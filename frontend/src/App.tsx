import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { router } from "@/router";
import { queryClient } from "@/lib/queryClient";
import { useLanguageStore, dirFor } from "@/store/languageStore";
import { useDarkModeStore } from "@/store/darkModeStore";
import { Toaster } from "@/components/ui/toaster";
import { OfflineBanner } from "@/components/offline-banner";

export default function App() {
  const language = useLanguageStore((s) => s.language);
  const darkMode = useDarkModeStore((s) => s.darkMode);

  useEffect(() => {
    document.documentElement.dir = dirFor(language);
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);

  return (
    <QueryClientProvider client={queryClient}>
      <OfflineBanner />
      <Toaster />
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
