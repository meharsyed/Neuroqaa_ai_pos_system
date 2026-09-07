import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  KeyRound, Loader2, Plus, Search, ShieldCheck, UserPlus, Users as UsersIcon,
} from "lucide-react";

import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { DateTime } from "@/components/ui/date-display";
import { apiErrorMessage, usersApi } from "@/lib/users";
import { useToast } from "@/lib/use-toast";
import { useAuthStore } from "@/store/authStore";
import type { User, UserRole } from "@/types/auth";

const ROLES: { value: UserRole; label: string; blurb: string }[] = [
  { value: "owner", label: "Owner", blurb: "Everything, including staff accounts and the activity log." },
  { value: "manager", label: "Manager", blurb: "Prices, stock, reports and credit limits. No staff accounts." },
  { value: "cashier", label: "Cashier", blurb: "Sell, take payments, handle customers and the khata." },
  { value: "stock_clerk", label: "Stock Clerk", blurb: "The same as a cashier for now." },
];

// ── Add a member of staff ───────────────────────────────────────────────────

function AddUserDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "", phone: "",
    role: "cashier" as UserRole, password: "",
  });
  const [error, setError] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: () => usersApi.create(form),
    onSuccess: (user) => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast({
        title: `${user.full_name || user.email} can now sign in`,
        description: "Give them the password you set — they will be asked to choose their own.",
      });
      onOpenChange(false);
      setForm({ first_name: "", last_name: "", email: "", phone: "", role: "cashier", password: "" });
      setError("");
    },
    onError: (err) => setError(apiErrorMessage(err, "Could not create the account.")),
  });

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add a member of staff</DialogTitle>
        </DialogHeader>

        <form
          className="space-y-3"
          onSubmit={(e) => { e.preventDefault(); setError(""); mutate(); }}
        >
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">First name</label>
              <Input value={form.first_name} onChange={set("first_name")} required />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Last name</label>
              <Input value={form.last_name} onChange={set("last_name")} />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Email — this is how they sign in</label>
            <Input type="email" value={form.email} onChange={set("email")} required />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Phone</label>
            <Input value={form.phone} onChange={set("phone")} placeholder="03XX XXXXXXX" />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Role</label>
            <div className="space-y-1.5">
              {ROLES.map((r) => (
                <label
                  key={r.value}
                  className={`flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 transition-colors ${
                    form.role === r.value ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    className="mt-0.5 accent-primary"
                    checked={form.role === r.value}
                    onChange={() => setForm({ ...form, role: r.value })}
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{r.label}</span>
                    <span className="block text-xs text-muted-foreground">{r.blurb}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Temporary password — at least 8 characters
            </label>
            <Input
              type="text"
              value={form.password}
              onChange={set("password")}
              required
              minLength={8}
              placeholder="Tell them this, they will change it"
            />
            <p className="text-xs text-muted-foreground">
              They are asked to choose their own the first time they sign in, so you
              will not keep knowing it.
            </p>
          </div>

          {error && (
            <p className="whitespace-pre-line rounded-lg border border-destructive/40 bg-destructive-bg px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <Button type="button" variant="outline" className="flex-1"
                    onClick={() => onOpenChange(false)} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" className="flex-1" disabled={isPending}>
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              Create account
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Reset somebody's password ───────────────────────────────────────────────

function ResetPasswordDialog({
  user, onClose,
}: { user: User | null; onClose: () => void }) {
  const { toast } = useToast();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: () => usersApi.setPassword(user!.id, password),
    onSuccess: () => {
      toast({
        title: `New password set for ${user!.full_name || user!.email}`,
        description: "They will be asked to choose their own when they next sign in.",
      });
      setPassword(""); setError(""); onClose();
    },
    onError: (err) => setError(apiErrorMessage(err, "Could not set the password.")),
  });

  return (
    <Dialog open={!!user} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Reset password</DialogTitle>
        </DialogHeader>
        {user && (
          <form className="space-y-3"
                onSubmit={(e) => { e.preventDefault(); setError(""); mutate(); }}>
            <p className="text-sm text-muted-foreground">
              A new temporary password for <span className="font-medium text-foreground">
              {user.full_name || user.email}</span>.
            </p>
            <Input
              type="text" value={password} minLength={8} required
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              autoFocus
            />
            {error && (
              <p className="whitespace-pre-line rounded-lg border border-destructive/40 bg-destructive-bg px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            )}
            <div className="flex gap-2">
              <Button type="button" variant="outline" className="flex-1" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" className="flex-1" disabled={isPending}>
                {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                Set password
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── The page ────────────────────────────────────────────────────────────────

export default function UsersPage() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const me = useAuthStore((s) => s.user);
  const [search, setSearch] = useState("");
  const [adding, setAdding] = useState(false);
  const [resetting, setResetting] = useState<User | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["users", search],
    queryFn: () => usersApi.list({ search: search || undefined }),
  });

  const { mutate: update, isPending: updating } = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: Parameters<typeof usersApi.update>[1] }) =>
      usersApi.update(id, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (err) =>
      toast({ title: apiErrorMessage(err, "Could not save the change."), variant: "error" }),
  });

  const users = data?.results ?? [];

  return (
    <PageContainer>
      <PageHeader
        title="Staff"
        subtitle="Who can sign in, and what they are allowed to do"
        actions={
          <Button onClick={() => setAdding(true)}>
            <Plus className="h-4 w-4" /> Add staff
          </Button>
        }
      />

      <div className="relative max-w-sm">
        <Search className="absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, email or phone"
          className="ps-9"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
        </div>
      ) : users.length === 0 ? (
        <EmptyState icon={UsersIcon} title="Nobody found" />
      ) : (
        <div className="divide-y rounded-lg border">
          {users.map((u) => {
            const isMe = u.id === me?.id;
            return (
              <div key={u.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 truncate font-medium">
                    {u.full_name || u.email}
                    {isMe && <span className="text-xs text-muted-foreground">(you)</span>}
                    {!u.is_active && <Badge variant="danger">Deactivated</Badge>}
                    {u.must_change_password && (
                      <Badge variant="warning">Must set a password</Badge>
                    )}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {u.email}
                    {u.phone ? ` · ${u.phone}` : ""}
                    {" · "}
                    {u.last_login
                      ? <>last signed in <DateTime value={u.last_login} format="short" /></>
                      : "never signed in"}
                  </p>
                </div>

                <select
                  value={u.role}
                  disabled={isMe || updating}
                  onChange={(e) => update({ id: u.id, patch: { role: e.target.value as UserRole } })}
                  className="h-9 rounded-md border border-input bg-background px-2 text-sm disabled:opacity-50"
                  aria-label={`Role for ${u.email}`}
                  title={isMe ? "You cannot change your own role" : undefined}
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>

                <Button
                  variant="outline" size="sm"
                  onClick={() => setResetting(u)}
                  disabled={!u.is_active}
                >
                  <KeyRound className="h-4 w-4" /> Reset password
                </Button>

                <Button
                  variant={u.is_active ? "ghost" : "outline"}
                  size="sm"
                  disabled={isMe || updating}
                  title={isMe ? "You cannot deactivate your own account" : undefined}
                  onClick={() => update({ id: u.id, patch: { is_active: !u.is_active } })}
                >
                  {u.is_active ? "Deactivate" : "Reactivate"}
                </Button>
              </div>
            );
          })}
        </div>
      )}

      <p className="flex items-start gap-2 rounded-lg border bg-muted/40 px-3 py-2.5 text-xs text-muted-foreground">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          Accounts are deactivated, never deleted — every bill points at the person
          who rang it up, and that record has to survive them leaving. A deactivated
          account cannot sign in and keeps its history.
        </span>
      </p>

      <AddUserDialog open={adding} onOpenChange={setAdding} />
      <ResetPasswordDialog user={resetting} onClose={() => setResetting(null)} />
    </PageContainer>
  );
}
