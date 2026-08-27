import { useLanguageStore } from "@/store/languageStore";
import { translations, type TranslationKey } from "@/lib/translations";

export function useTranslation() {
  const language = useLanguageStore((state) => state.language);
  const isRTL = useLanguageStore((state) => state.isRTL);
  const setLanguage = useLanguageStore((state) => state.setLanguage);

  const t = (key: TranslationKey): string => {
    const translated = translations[language]?.[key];
    if (!translated) {
      // Fallback to English if translation missing
      return translations.en[key] || key;
    }
    return translated;
  };

  return { t, language, isRTL, setLanguage };
}