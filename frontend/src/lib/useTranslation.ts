import { useLanguageStore } from "@/store/languageStore";
import { translations } from "@/lib/translations";

type Vars = Record<string, string | number>;

function resolve(dict: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, dict);
}

export function useTranslation() {
  const language = useLanguageStore((s) => s.language);
  const dict = translations[language];

  function t(key: string, vars?: Vars): string {
    const val = resolve(dict, key);
    if (typeof val !== "string") {
      // Falling back to the raw key means the user reads "bills.title" on a
      // screen. Silent in production — a missing word is better than a broken
      // page — but never silent while someone is working on it.
      if (import.meta.env.DEV) {
        console.warn(`[i18n] no "${language}" translation for "${key}"`);
      }
      return key;
    }
    if (!vars) return val;
    return Object.entries(vars).reduce(
      (acc, [k, v]) => acc.split(`{${k}}`).join(String(v)),
      val
    );
  }

  return { t, language };
}
