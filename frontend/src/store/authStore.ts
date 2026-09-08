import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, LoginResponse } from "@/types/auth";

interface AuthState {
  user: User | null;
  /**
   * In memory only — never persisted (see `partialize` below). The refresh
   * token that used to sit alongside it in localStorage is gone entirely:
   * the backend now sets it as an httpOnly cookie the browser holds and this
   * app never touches. A page reload starts with accessToken back at null;
   * the axios interceptor's 401-triggered refresh (lib/axios.ts) picks it
   * back up from the cookie within the first request.
   */
  accessToken: string | null;
  isAuthenticated: boolean;
  setAuth: (response: LoginResponse) => void;
  /** Patch the cached user — e.g. after they choose their own password. */
  setUser: (user: User) => void;
  setAccessToken: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,

      setAuth: (response: LoginResponse) =>
        set({
          user: response.user,
          accessToken: response.access,
          isAuthenticated: true,
        }),

      setUser: (user: User) => set({ user }),

      // Called by the axios interceptor after a silent token refresh
      setAccessToken: (token: string) => set({ accessToken: token }),

      logout: () =>
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: "pos-auth",
      // `user`/`isAuthenticated` are persisted so a reload doesn't flash a
      // logged-out UI while the silent refresh (cookie-based) completes.
      // accessToken is deliberately excluded — it never touches localStorage.
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
