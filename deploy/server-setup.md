# One-time server setup — run these yourself, in order

Read every command before running it — nothing here is meant to be piped
blindly into a shell. Each step says what it does and why, and everything
is additive: nothing here modifies the website's nginx site, its Postgres
database, or its systemd service.

## 0. Before you start

Confirm the website is still fine after *every* step below, not just at the
end — it costs one command and catches a mistake immediately instead of an
hour later:

```bash
curl -sSI https://neuroqaa-ai.tech | head -1     # expect: HTTP/2 200 (or 301/302)
```

## 1. Add a 2GB swapfile

The box currently has 0B swap (`free -h` showed `Swap: 0B`). Cheap insurance
against an OOM crash taking down both apps if something briefly spikes:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
free -h   # should now show Swap: 2.0Gi
```

Make it permanent across reboots:

```bash
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. Create the POS's own database and role on the existing Postgres

This is the ONE thing that touches a shared service — but it only *adds* a
database and a role with no access to anything else; the website's own
database and role are completely untouched and cannot be reached by the new
one:

```bash
sudo -u postgres psql
```

Then, inside the `psql` prompt (replace the password with a real generated
one — save it, you'll need it for `.env.prod` in step 4):

```sql
CREATE ROLE pos_app WITH LOGIN PASSWORD 'REPLACE_WITH_A_REAL_PASSWORD';
CREATE DATABASE pos_db OWNER pos_app;
\q
```

Confirm isolation — connecting as `pos_app` should work for `pos_db` and
fail for anything else:

```bash
PGPASSWORD='REPLACE_WITH_A_REAL_PASSWORD' psql -h 127.0.0.1 -U pos_app -d pos_db -c '\conninfo'
```

## 3. Create the directory the POS lives in, and a dedicated deploy user

Keeping this in its own directory, owned by its own user, means the
GitHub Actions deploy key never needs root or touches anything under the
website's own directory:

```bash
sudo mkdir -p /opt/pos-system
sudo useradd -r -m -d /home/posdeploy -s /bin/bash posdeploy
sudo usermod -aG docker posdeploy      # lets it run `docker compose` without sudo
sudo chown -R posdeploy:posdeploy /opt/pos-system
```

Generate a dedicated SSH keypair for GitHub Actions to use (on your own
machine, not the server):

```bash
ssh-keygen -t ed25519 -f pos_deploy_key -C "github-actions-pos-deploy" -N ""
```

Then add the **public** key to the server for the `posdeploy` user:

```bash
sudo mkdir -p /home/posdeploy/.ssh
sudo tee -a /home/posdeploy/.ssh/authorized_keys < pos_deploy_key.pub
sudo chown -R posdeploy:posdeploy /home/posdeploy/.ssh
sudo chmod 700 /home/posdeploy/.ssh
sudo chmod 600 /home/posdeploy/.ssh/authorized_keys
```

The **private** key (`pos_deploy_key`, no extension) is what goes into the
GitHub repo secret `SSH_PRIVATE_KEY` — see the CI/CD section of
`docs/PHASE_16_DEPLOYMENT_PLAN.md`. Never paste the private key anywhere
else, and delete your local copy of it once it's in GitHub's secret store.

## 4. Clone the repo and create the production env file

As the `posdeploy` user (`sudo -u posdeploy -i` to switch to it):

```bash
git clone https://github.com/meharsyed/Neuroqaa_ai_pos_system.git /opt/pos-system
cd /opt/pos-system
nano backend/.env.prod
```

`.env.prod` needs (fill in real values — this file never goes in git):

```
SECRET_KEY=<a long random string, e.g. from `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`>
DEBUG=False
ALLOWED_HOSTS=POS_DOMAIN
DATABASE_URL=postgres://pos_app:REPLACE_WITH_A_REAL_PASSWORD@127.0.0.1:5432/pos_db
CORS_ALLOWED_ORIGINS=https://POS_DOMAIN
```

(`SENTRY_DSN` and `AWS_STORAGE_BUCKET_NAME` are both optional — leave them
unset for now; see `docs/PHASE_16_DEPLOYMENT_PLAN.md` on storage.)

## 5. First manual deploy (before CI/CD is wired up)

This proves the whole stack works before any automation touches it:

```bash
cd /opt/pos-system
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend   # watch it come up, Ctrl+C when settled
curl -sS http://127.0.0.1:8001/admin/login/ | head -5        # should return HTML, not a connection error
```

## 6. nginx + SSL

```bash
sudo cp /opt/pos-system/deploy/nginx-pos.conf.template /etc/nginx/sites-available/pos
sudo sed -i 's/POS_DOMAIN/your.actual.domain/g' /etc/nginx/sites-available/pos
sudo ln -s /etc/nginx/sites-available/pos /etc/nginx/sites-enabled/pos
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d your.actual.domain
```

Certbot edits only the `pos` site file it's pointed at — it does not touch
`/etc/nginx/sites-available/neuroqaa`.

## 7. Confirm, from outside the server

```bash
curl -sSI https://your.actual.domain           # the POS frontend
curl -sSI https://your.actual.domain/api/      # the API, through nginx
curl -sSI https://neuroqaa-ai.tech             # the website — still fine
```

Once all three come back clean, the manual deploy is proven and Phase 16's
CI/CD section takes over future deploys.
