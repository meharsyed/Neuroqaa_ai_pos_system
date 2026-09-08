import axios, {
  type AxiosResponse,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "@/store/authStore";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  // The refresh-token cookie is httpOnly and scoped to /api/auth/ — this is
  // what lets the browser attach and accept it at all across an origin split
  // (e.g. the Vite dev server calling the Django API on another port).
  withCredentials: true,
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const { setAccessToken, logout } = useAuthStore.getState();

      try {
        // No body needed — the refresh token rides along as the httpOnly
        // cookie the login response set; `withCredentials` is what makes the
        // browser send it.
        const { data } = await axios.post<{ access: string }>(
          `${API_BASE}/auth/refresh/`,
          {},
          { withCredentials: true }
        );
        setAccessToken(data.access);
        original.headers.Authorization = `Bearer ${data.access}`;
        return apiClient(original);
      } catch {
        // Refresh failed (cookie missing, expired, or blacklisted) — sign out.
      }

      logout();
      window.location.replace("/login");
    }

    return Promise.reject(error);
  }
);
