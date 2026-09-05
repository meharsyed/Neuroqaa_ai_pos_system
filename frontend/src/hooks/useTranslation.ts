import { useLanguageStore, dirFor } from "@/store/languageStore";
import { translations } from "@/lib/translations";

export function useTranslation() {
  const language = useLanguageStore((state) => state.language);
  const setLanguage = useLanguageStore((state) => state.setLanguage);

  const t = (key: string): string => {
    const parts = key.split(".");
    const langTranslations = translations[language as keyof typeof translations] as Record<string, any>;
    let current: unknown = langTranslations;
    for (const part of parts) {
      if (typeof current === "object" && current !== null) {
        current = (current as Record<string, unknown>)[part];
      } else {
        return key;
      }
    }
    return (current as string) || key;
  };

  return { t, language, setLanguage, dirFor };
}