import { useState } from "react";
import { useLanguageStore } from "@/store/languageStore";
import { Globe, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface LanguageToggleProps {
  variant?: "sidebar" | "header";
}

export function LanguageToggle({ variant = "sidebar" }: LanguageToggleProps) {
  const language = useLanguageStore((state) => state.language);
  const setLanguage = useLanguageStore((state) => state.setLanguage);
  const [isOpen, setIsOpen] = useState(false);

  const handleLanguageChange = (lang: "en" | "ur") => {
    setLanguage(lang);
    // Update HTML lang attribute (for accessibility)
    const htmlElement = document.documentElement;
    htmlElement.lang = lang;
    // DON'T flip layout direction - only text direction
    // Use CSS classes instead (applied in ProtectedLayout)
    setIsOpen(false);
  };

  const buttonClasses = cn(
    "flex items-center gap-1.5 rounded-md font-medium transition-all duration-200",
    variant === "sidebar" ? (
      "px-2.5 py-2 text-xs text-white/80 hover:text-white hover:bg-white/15 bg-white/5"
    ) : (
      "px-3 py-2 text-sm text-slate-700 hover:text-slate-900 hover:bg-slate-100 bg-slate-50 border border-slate-200"
    )
  );

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={buttonClasses}
        title="Change language"
      >
        <Globe className="h-4 w-4" />
        <span className="font-semibold">{language === "en" ? "EN" : "اردو"}</span>
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <div className={cn(
          "absolute mt-1 bg-white rounded-lg border shadow-lg z-50 min-w-[140px]",
          variant === "sidebar" ? "right-0 border-white/20 bg-slate-800 shadow-2xl" : "right-0 border-slate-200"
        )}>
          <button
            onClick={() => handleLanguageChange("en")}
            className={cn(
              "w-full px-3 py-2.5 text-sm text-left font-medium hover:bg-opacity-80 transition-colors first:rounded-t-lg",
              language === "en"
                ? variant === "sidebar"
                  ? "text-primary bg-white/10"
                  : "text-primary bg-primary/10"
                : variant === "sidebar"
                  ? "text-white/80 hover:text-white hover:bg-white/5"
                  : "text-slate-700 hover:text-slate-900 hover:bg-slate-100"
            )}
          >
            🇺🇸 English
          </button>
          <button
            onClick={() => handleLanguageChange("ur")}
            className={cn(
              "w-full px-3 py-2.5 text-sm text-left font-medium hover:bg-opacity-80 transition-colors last:rounded-b-lg",
              language === "ur"
                ? variant === "sidebar"
                  ? "text-primary bg-white/10"
                  : "text-primary bg-primary/10"
                : variant === "sidebar"
                  ? "text-white/80 hover:text-white hover:bg-white/5"
                  : "text-slate-700 hover:text-slate-900 hover:bg-slate-100"
            )}
          >
            🇵🇰 اردو
          </button>
        </div>
      )}
    </div>
  );
}