import { useMemo, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { FormPasswordField, FormTextField } from "@/components/forms";
import { useAuthStore } from "@/store/authStore";
import { apiClient } from "@/lib/axios";
import { useTranslation } from "@/lib/useTranslation";
import type { LoginResponse, LoginCredentials } from "@/types/auth";

type LoginForm = { email: string; password: string };

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [serverError, setServerError] = useState<string | null>(null);
  const from = (location.state as { from?: string })?.from ?? "/dashboard";
  const { t } = useTranslation();

  const FEATURES = [
    t("login.feature1"),
    t("login.feature2"),
    t("login.feature3"),
    t("login.feature4"),
  ];

  const loginSchema = useMemo(
    () =>
      z.object({
        email: z.string().email(t("login.emailInvalid")),
        password: z.string().min(1, t("login.passwordRequired")),
      }),
    [t]
  );

  const {
    control,
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
      setServerError(t("login.invalidCredentials"));
    },
  });

  return (
    <div className="min-h-screen flex">

      {/* ── Left decorative panel ─────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-5/12 xl:w-[46%] relative overflow-hidden bg-gradient-to-br from-green-900 via-green-800 to-green-950 flex-col justify-between p-12">

        {/* Dot grid overlay */}
        <div className="absolute inset-0 bg-dot-grid opacity-100 pointer-events-none" />

        {/* Animated blobs */}
        <div className="absolute top-16 -right-20 w-96 h-96 rounded-full bg-blue-600/25 blur-3xl animate-float pointer-events-none" />
        <div className="absolute bottom-24 -left-16 w-80 h-80 rounded-full bg-green-600/25 blur-3xl animate-float-slow pointer-events-none" />
        <div className="absolute top-1/2 right-1/3 w-52 h-52 rounded-full bg-teal-500/15 blur-2xl animate-float-reverse pointer-events-none" />

        {/* Top: logo mark */}
        <div className="relative z-10 animate-fade-up">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-xl glass flex items-center justify-center animate-glow-pulse">
              <img src="/brand/logo-mark-mono-light.svg" alt="" className="h-6 w-6" />
            </div>
            <div>
              <span className="text-white font-bold text-lg leading-tight block">
                Speed Tech Solutions
              </span>
              <span className="text-white/50 text-xs">{t("login.pointOfSaleSystem")}</span>
            </div>
          </div>
        </div>

        {/* Center: headline + features */}
        <div className="relative z-10 space-y-8">
          <div className="animate-fade-up-delay-1 space-y-3">
            <h2 className="text-4xl font-extrabold text-white leading-tight tracking-tight">
              {t("login.headline1")}<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-300 to-teal-300">
                {t("login.headline2")}
              </span>
            </h2>
            <p className="text-white/55 text-sm leading-relaxed max-w-xs">
              {t("login.subheadline")}
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
            {t("login.poweredBy")}{" "}
            <span className="text-white/55 font-semibold">Neuroqaa.ai</span>
          </p>
        </div>
      </div>

      {/* ── Right form panel ─────────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 bg-background">
        <div className="w-full max-w-[380px] animate-fade-in-scale">

          {/* Mobile-only logo */}
          <div className="lg:hidden flex items-center gap-2.5 justify-center mb-8">
            <div className="h-9 w-9 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/30">
              <img src="/brand/logo-mark-mono-light.svg" alt="" className="h-5 w-5" />
            </div>
            <span className="font-bold text-lg">Speed Tech Solutions</span>
          </div>

          {/* Heading */}
          <div className="mb-8 space-y-1.5 animate-fade-up">
            <h1 className="text-2xl font-bold tracking-tight">{t("login.welcomeBack")}</h1>
            <p className="text-sm text-muted-foreground">
              {t("login.signInSubtitle")}
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
            <Controller
              name="email"
              control={control}
              render={({ field }) => (
                <FormTextField
                  label={t("login.emailLabel")}
                  name="email"
                  type="email"
                  placeholder={t("login.emailPlaceholder")}
                  value={field.value}
                  onChange={field.onChange}
                  error={errors.email?.message}
                  autoComplete="email"
                  autoFocus
                />
              )}
            />

            <Controller
              name="password"
              control={control}
              render={({ field }) => (
                <FormPasswordField
                  label={t("login.passwordLabel")}
                  name="password"
                  placeholder="••••••••"
                  value={field.value}
                  onChange={field.onChange}
                  error={errors.password?.message}
                  autoComplete="current-password"
                />
              )}
            />

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
                className="w-full h-10 font-semibold btn-shimmer bg-gradient-to-r from-primary to-green-600 hover:from-primary/90 hover:to-green-700 transition-all duration-200 shadow-md shadow-primary/25 hover:shadow-lg hover:shadow-primary/30 hover:-translate-y-0.5"
                disabled={loginMutation.isPending}
                loading={loginMutation.isPending}
              >
                {loginMutation.isPending ? t("login.signingIn") : (
                  <>
                    {t("login.signIn")}
                    <ArrowRight className="h-4 w-4 ms-2" />
                  </>
                )}
              </Button>
            </div>
          </form>

          {/* Footer */}
          <p className="mt-8 text-center text-xs text-muted-foreground/50 animate-fade-up-delay-4">
            {t("login.poweredBy")}{" "}
            <span className="font-semibold text-muted-foreground/70">Neuroqaa.ai</span>
          </p>
        </div>
      </div>
    </div>
  );
}