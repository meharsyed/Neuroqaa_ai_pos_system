import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Zap,
  Mail,
  Lock,
  ArrowRight,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/store/authStore";
import { apiClient } from "@/lib/axios";
import type { LoginResponse, LoginCredentials } from "@/types/auth";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type LoginForm = z.infer<typeof loginSchema>;

const FEATURES = [
  "Keyboard-first checkout — built for speed",
  "Real-time sales & inventory reports",
  "Cash drawer reconciliation & shift management",
  "ESC/POS thermal receipt printing",
];

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [serverError, setServerError] = useState<string | null>(null);
  const from = (location.state as { from?: string })?.from ?? "/dashboard";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const loginMutation = useMutation({
    mutationFn: (creds: LoginCredentials) =>
      apiClient.post<LoginResponse>("/auth/login/", creds).then((r) => r.data),
    onSuccess: (data) => {
      setAuth(data);
      navigate(from, { replace: true });
    },
    onError: () => {
      setServerError("Invalid email or password. Please try again.");
    },
  });

  return (
    <div className="min-h-screen flex">

      {/* ── Left decorative panel ─────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-5/12 xl:w-[46%] relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 flex-col justify-between p-12">

        {/* Dot grid overlay */}
        <div className="absolute inset-0 bg-dot-grid opacity-100 pointer-events-none" />

        {/* Animated blobs */}
        <div className="absolute top-16 -right-20 w-96 h-96 rounded-full bg-blue-600/25 blur-3xl animate-float pointer-events-none" />
        <div className="absolute bottom-24 -left-16 w-80 h-80 rounded-full bg-indigo-600/25 blur-3xl animate-float-slow pointer-events-none" />
        <div className="absolute top-1/2 right-1/3 w-52 h-52 rounded-full bg-cyan-500/15 blur-2xl animate-float-reverse pointer-events-none" />

        {/* Top: logo mark */}
        <div className="relative z-10 animate-fade-up">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl glass flex items-center justify-center animate-glow-pulse">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="text-white font-bold text-lg leading-tight block">
                Neuroqaa POS
              </span>
              <span className="text-white/50 text-xs">Point of Sale System</span>
            </div>
          </div>
        </div>

        {/* Center: headline + features */}
        <div className="relative z-10 space-y-8">
          <div className="animate-fade-up-delay-1 space-y-3">
            <h2 className="text-4xl font-extrabold text-white leading-tight tracking-tight">
              Modern POS for<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-cyan-300">
                Modern Businesses
              </span>
            </h2>
            <p className="text-white/55 text-sm leading-relaxed max-w-xs">
              Fast, reliable, and built for Quetta's growing retail market.
            </p>
          </div>

          <ul className="space-y-3 animate-fade-up-delay-2">
            {FEATURES.map((f, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-white/75">
                <CheckCircle2 className="h-4 w-4 text-blue-300 shrink-0 mt-0.5" />
                {f}
              </li>
            ))}
          </ul>
        </div>

        {/* Bottom: brand tag */}
        <div className="relative z-10 animate-fade-up-delay-3">
          <p className="text-white/30 text-xs">
            Powered by{" "}
            <span className="text-white/55 font-semibold">Neuroqaa.ai</span>
          </p>
        </div>
      </div>

      {/* ── Right form panel ─────────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 bg-background">
        <div className="w-full max-w-[380px] animate-fade-in-scale">

          {/* Mobile-only logo */}
          <div className="lg:hidden flex items-center gap-2.5 justify-center mb-8">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/30">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-lg">Neuroqaa POS</span>
          </div>

          {/* Heading */}
          <div className="mb-8 space-y-1.5 animate-fade-up">
            <h1 className="text-2xl font-bold tracking-tight">Welcome back</h1>
            <p className="text-sm text-muted-foreground">
              Sign in to access the POS system
            </p>
          </div>

          {/* Form */}
          <form
            onSubmit={handleSubmit((data) => {
              setServerError(null);
              loginMutation.mutate(data);
            })}
            className="space-y-5"
          >
            {/* Email */}
            <div className="space-y-1.5 animate-fade-up-delay-1">
              <Label htmlFor="email" className="text-sm font-medium">
                Email address
              </Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  className="pl-9 transition-all duration-200 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  {...register("email")}
                />
              </div>
              {errors.email && (
                <p className="text-xs text-destructive flex items-center gap-1">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1.5 animate-fade-up-delay-2">
              <Label htmlFor="password" className="text-sm font-medium">
                Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="pl-9 transition-all duration-200 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  {...register("password")}
                />
              </div>
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            {/* Server error */}
            {serverError && (
              <div className="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2.5 text-sm text-destructive animate-fade-up">
                {serverError}
              </div>
            )}

            {/* Submit */}
            <div className="animate-fade-up-delay-3 pt-1">
              <Button
                type="submit"
                className="w-full h-10 font-semibold btn-shimmer bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/90 hover:to-indigo-700 transition-all duration-200 shadow-md shadow-primary/25 hover:shadow-lg hover:shadow-primary/30 hover:-translate-y-0.5"
                disabled={loginMutation.isPending}
              >
                {loginMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </div>
          </form>

          {/* Footer */}
          <p className="mt-8 text-center text-xs text-muted-foreground/50 animate-fade-up-delay-4">
            Powered by{" "}
            <span className="font-semibold text-muted-foreground/70">Neuroqaa.ai</span>
          </p>
        </div>
      </div>
    </div>
  );
}