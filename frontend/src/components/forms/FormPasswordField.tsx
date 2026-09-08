import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormHint, FormError } from "@/components/ui/form-field";

export interface FormPasswordFieldProps {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  hint?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  autoComplete?: string;
  autoFocus?: boolean;
  showToggle?: boolean;
}

export function FormPasswordField({
  label,
  name,
  value,
  onChange,
  error,
  hint,
  placeholder,
  required = false,
  disabled = false,
  autoComplete = "current-password",
  autoFocus = false,
  showToggle = true,
}: FormPasswordFieldProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <FormField>
      <FormLabel htmlFor={name}>
        {label}
        {required && <span className="text-destructive ms-1">*</span>}
      </FormLabel>
      <div className="relative">
        <Input
          id={name}
          name={name}
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          invalid={!!error}
          disabled={disabled}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          trailingIcon={
            showToggle && (
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-muted-foreground hover:text-foreground transition-colors"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            )
          }
        />
      </div>
      {hint && !error && <FormHint>{hint}</FormHint>}
      {error && <FormError>{error}</FormError>}
    </FormField>
  );
}