import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { KeyRound, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiErrorMessage, usersApi } from "@/lib/users";
import { useToast } from "@/lib/use-toast";
import { useAuthStore } from "@/store/authStore";

/**
 * Shown when the owner issued this account's password.
 *
 * It has no close button on purpose: the point is that the owner stops knowing
 * a member of staff's password the moment they first sign in.
 */
export function ForcePasswordChange() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const { toast } = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: () => usersApi.changeOwnPassword(current, next),
    onSuccess: () => {
      if (user) setUser({ ...user, must_change_password: false });
      toast({ title: "Password changed", description: "That is the one to use from now on." });
    },
    onError: (err) => setError(apiErrorMessage(err, "Could not change the password.")),
  });

  if (!user?.must_change_password) return null;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (next !== confirm) {
      setError("The two new passwords do not match.");
      return;
    }
    mutate();
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-sm rounded-xl bg-background p-6 shadow-2xl">
        <div className="mb-4 flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
            <KeyRound className="h-4 w-4 text-primary" />
          </span>
          <div>
            <h2 className="font-semibold">Choose your own password</h2>
            <p className="text-xs text-muted-foreground">
              The one you were given was temporary.
            </p>
          </div>
        </div>

        <form className="space-y-3" onSubmit={submit}>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              The password you were given
            </label>
            <Input type="password" value={current} required autoFocus
                   onChange={(e) => setCurrent(e.target.value)} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              New password — at least 8 characters
            </label>
            <Input type="password" value={next} required minLength={8}
                   onChange={(e) => setNext(e.target.value)} />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Type it again
            </label>
            <Input type="password" value={confirm} required minLength={8}
                   onChange={(e) => setConfirm(e.target.value)} />
          </div>

          {error && (
            <p className="whitespace-pre-line rounded-lg border border-destructive/40 bg-destructive-bg px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={isPending}>
            {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Save and continue
          </Button>
        </form>
      </div>
    </div>
  );
}
