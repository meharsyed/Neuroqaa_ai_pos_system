import { useEffect, useState } from "react";
import { AlertTriangle, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/axios";

export function OfflineBanner() {
  const [offline, setOffline] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  // Disable offline banner in development mode
  const isDev = import.meta.env.DEV;

  useEffect(() => {
    // Don't show banner in development
    if (isDev) return;

    let timeoutId: NodeJS.Timeout;

    const checkConnection = async () => {
      try {
        // Try a simple health check
        await apiClient.get("/health/", { timeout: 3000 });
        setOffline(false);
      } catch {
        setOffline(true);
        // Auto-retry every 5 seconds
        timeoutId = setTimeout(checkConnection, 5000);
      }
    };

    // Check on mount
    checkConnection();

    // Setup axios interceptor for errors
    const errorInterceptor = apiClient.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === undefined || error.code === "ECONNABORTED") {
          setOffline(true);
        }
        return Promise.reject(error);
      }
    );

    return () => {
      clearTimeout(timeoutId);
      apiClient.interceptors.response.eject(errorInterceptor);
    };
  }, []);

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await apiClient.get("/health/", { timeout: 3000 });
      setOffline(false);
    } catch {
      setOffline(true);
    } finally {
      setIsRetrying(false);
    }
  };

  if (!offline) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-40 bg-warning/90 text-warning-foreground border-b border-warning/50 px-4 py-2.5">
      <div className="flex items-center justify-between gap-3 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span className="text-sm font-medium">
            Unable to connect to server. Working in offline mode.
          </span>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={handleRetry}
          disabled={isRetrying}
          className="gap-1.5 text-xs"
        >
          <RotateCw className="h-3 w-3" />
          {isRetrying ? "Retrying..." : "Retry"}
        </Button>
      </div>
    </div>
  );
}