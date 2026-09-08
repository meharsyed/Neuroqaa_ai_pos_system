#!/usr/bin/env python
"""
Generate secure Django SECRET_KEY and other security settings.
Run this once and add the output to your .env file.

Usage:
    python scripts/generate_django_keys.py
"""

import secrets
import string
from pathlib import Path


def generate_secret_key(length=50):
    """
    Generate a cryptographically secure Django SECRET_KEY.

    Django recommends:
    - At least 50 characters
    - Mix of letters, digits, symbols
    - Cryptographically random (not predictable)

    Args:
        length: Length of the key (default 50, recommended minimum)

    Returns:
        A secure random string suitable for Django SECRET_KEY
    """
    # Characters Django recognizes as "safe" in SECRET_KEY
    chars = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"

    # Use secrets module for cryptographic randomness (not random module)
    key = "".join(secrets.choice(chars) for _ in range(length))
    return key


def generate_jwt_secret(length=64):
    """
    Generate a secure JWT signing key.
    Longer than SECRET_KEY because JWT tokens rely heavily on this.
    """
    chars = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_encryption_key():
    """
    Generate a base64-encoded encryption key for sensitive data.
    Uses Fernet (symmetric encryption) from cryptography library.
    """
    import base64
    random_bytes = secrets.token_bytes(32)  # 256 bits
    return base64.urlsafe_b64encode(random_bytes).decode()


def main():
    """Generate all security keys and display them."""

    print("=" * 80)
    print("DJANGO SECURITY KEY GENERATOR")
    print("=" * 80)
    print()

    # Generate Django SECRET_KEY
    secret_key = generate_secret_key(50)
    print("1. DJANGO SECRET_KEY (for session encryption, CSRF tokens, password reset links)")
    print("-" * 80)
    print(f"SECRET_KEY={secret_key}")
    print()
    print("   ✓ Length: 50+ characters")
    print("   ✓ Cryptographically random")
    print("   ✓ Mix of letters, digits, symbols")
    print()

    # Generate JWT secret
    jwt_secret = generate_secret_key(64)
    print("2. JWT_SECRET (for token signing - can be same as SECRET_KEY or different)")
    print("-" * 80)
    print(f"JWT_SECRET={jwt_secret}")
    print()
    print("   Note: simplejwt will use Django's SECRET_KEY by default.")
    print("   Only set this if you want a separate key for JWT signing.")
    print()

    # Generate CSRF key
    csrf_key = generate_secret_key(32)
    print("3. CSRF_TRUSTED_ORIGINS (for production - configure in settings)")
    print("-" * 80)
    print("   CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com")
    print()

    # Generate database password
    db_password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))
    print("4. SECURE DATABASE PASSWORD (for production PostgreSQL)")
    print("-" * 80)
    print(f"POSTGRES_PASSWORD={db_password}")
    print()
    print("   ✓ 20 random alphanumeric characters")
    print("   ✓ Should be 20+ chars in production")
    print()

    # Display full .env template
    print("=" * 80)
    print("COMPLETE .env TEMPLATE (Copy and paste into your .env file)")
    print("=" * 80)
    print()

    env_template = f"""# ────────────────────────────────────────────────────────────────────────────────
# SECURITY SETTINGS
# ────────────────────────────────────────────────────────────────────────────────
SECRET_KEY={secret_key}
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# ────────────────────────────────────────────────────────────────────────────────
# CORS CONFIGURATION (set to your exact frontend domain for production)
# ────────────────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://yourdomain.com

# ────────────────────────────────────────────────────────────────────────────────
# DATABASE CONFIGURATION (for PostgreSQL cloud deployment)
# ────────────────────────────────────────────────────────────────────────────────
POSTGRES_DB=pos_production
POSTGRES_USER=pos_user
POSTGRES_PASSWORD={db_password}
POSTGRES_HOST=your-db-host.rds.amazonaws.com
POSTGRES_PORT=5432

# ────────────────────────────────────────────────────────────────────────────────
# OPTIONAL: JWT CONFIGURATION (only if using custom JWT settings)
# Leave commented if using defaults (simplejwt will use SECRET_KEY)
# ────────────────────────────────────────────────────────────────────────────────
# JWT_SECRET={jwt_secret}
# JWT_ACCESS_TOKEN_LIFETIME_MINUTES=30
# JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# ────────────────────────────────────────────────────────────────────────────────
# LOGGING (optional, for debugging)
# ────────────────────────────────────────────────────────────────────────────────
# LOG_LEVEL=INFO
"""

    print(env_template)
    print()
    print("=" * 80)
    print("SECURITY BEST PRACTICES")
    print("=" * 80)
    print("""
✓ NEVER commit .env to git — add to .gitignore (already done)
✓ Generate NEW keys for production (don't copy dev keys)
✓ SECRET_KEY should be 50+ characters, random, stored securely
✓ DEBUG=False in production (prevents sensitive info leaks)
✓ ALLOWED_HOSTS must be exact list (prevents Host header attacks)
✓ CORS_ALLOWED_ORIGINS must be exact origin (prevents XSS attacks)
✓ Database password should be 20+ random characters
✓ Never use default passwords
✓ Rotate keys if compromised
✓ Store .env in secure location (AWS Secrets Manager, HashiCorp Vault, etc.)

FOR PRODUCTION:
1. Generate new SECRET_KEY (done ✓)
2. Set DEBUG=False (prevents info leaks)
3. Set ALLOWED_HOSTS to exact domain
4. Set CORS_ALLOWED_ORIGINS to frontend domain
5. Create strong database password
6. Store .env in secrets manager, not in repo
7. Run: python manage.py check --deploy

FOR LOCAL DEVELOPMENT:
1. Use weaker passwords (fine for dev)
2. DEBUG=True is OK (you need error details)
3. ALLOWED_HOSTS can include localhost
4. CORS_ALLOWED_ORIGINS=http://localhost:5173
""")


if __name__ == "__main__":
    main()
