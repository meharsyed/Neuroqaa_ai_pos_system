import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDarkModeStore } from "@/store/darkModeStore";

export function DarkModeToggle() {
  const { darkMode, toggleDarkMode } = useDarkModeStore();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleDarkMode}
      title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
      className="rounded-full"
    >
      {darkMode ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
    </Button>
  );
}