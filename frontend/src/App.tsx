import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { router } from "@/router";
import { queryClient } from "@/lib/queryClient";
import { useLanguageStore, dirFor } from "@/store/languageStore";

export default function App() {
  const language = useLanguageStore((s) => s.language);

  useEffect(() => {
    document.documentElement.dir = dirFor(language);
    document.documentElement.lang = language;
  }, [language]);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
