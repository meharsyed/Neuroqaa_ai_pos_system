import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DatePickerProps {
  value: string; // YYYY-MM-DD format
  onChange: (date: string) => void;
  placeholder?: string;
  className?: string;
}

function formatDateDisplay(dateStr: string): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-PK", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function DatePicker({ value, onChange, placeholder = "DD/MMM/YYYY", className }: DatePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState<Date>(
    value ? new Date(value) : new Date()
  );

  const handleDateClick = (day: number) => {
    const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, "0");
    const dd = String(date.getDate()).padStart(2, "0");
    onChange(`${yyyy}-${mm}-${dd}`);
    setIsOpen(false);
  };

  const getDaysInMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  };

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  };

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  };

  const days: (number | null)[] = [];
  const firstDay = getFirstDayOfMonth(currentMonth);
  for (let i = 0; i < firstDay; i++) {
    days.push(null);
  }
  const daysInMonth = getDaysInMonth(currentMonth);
  for (let i = 1; i <= daysInMonth; i++) {
    days.push(i);
  }

  const monthYear = currentMonth.toLocaleDateString("en-PK", {
    month: "long",
    year: "numeric",
  });

  const isToday = (day: number) => {
    if (!value) return false;
    const date = new Date(value);
    return (
      day === date.getDate() &&
      currentMonth.getMonth() === date.getMonth() &&
      currentMonth.getFullYear() === date.getFullYear()
    );
  };

  return (
    <div className="relative w-full">
      <div className="flex gap-2">
        <Input
          type="text"
          value={value ? formatDateDisplay(value) : ""}
          placeholder={placeholder}
          readOnly
          onClick={() => setIsOpen(!isOpen)}
          className={cn("cursor-pointer", className)}
        />
      </div>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 z-50 bg-background border rounded-lg shadow-xl p-4 w-72">
          {/* Month/Year Header */}
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={prevMonth}
              className="p-1 hover:bg-muted rounded"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <div className="font-semibold text-sm">{monthYear}</div>
            <button
              onClick={nextMonth}
              className="p-1 hover:bg-muted rounded"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Weekday Headers */}
          <div className="grid grid-cols-7 gap-1 mb-2">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
              <div key={day} className="text-xs font-semibold text-muted-foreground text-center py-1">
                {day}
              </div>
            ))}
          </div>

          {/* Calendar Days */}
          <div className="grid grid-cols-7 gap-1">
            {days.map((day, idx) => (
              <button
                key={idx}
                onClick={() => day && handleDateClick(day)}
                disabled={!day}
                className={cn(
                  "h-8 text-xs rounded hover:bg-muted disabled:opacity-0",
                  day && isToday(day) && "bg-primary text-primary-foreground font-semibold"
                )}
              >
                {day}
              </button>
            ))}
          </div>

          {/* Footer */}
          <div className="mt-4 pt-3 border-t flex gap-2 justify-end">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsOpen(false)}
            >
              Close
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}