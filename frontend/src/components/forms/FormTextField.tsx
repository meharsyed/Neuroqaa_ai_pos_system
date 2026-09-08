import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormHint, FormError } from "@/components/ui/form-field";

export interface FormTextFieldProps {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  hint?: string;
  placeholder?: string;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
  required?: boolean;
  type?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  autoComplete?: string;
}

export function FormTextField({
  label,
  name,
  value,
  onChange,
  error,
  hint,
  placeholder,
  leadingIcon,
  trailingIcon,
  required = false,
  type = "text",
  disabled = false,
  autoFocus = false,
  autoComplete,
}: FormTextFieldProps) {
  return (
    <FormField>
      <FormLabel htmlFor={name}>
        {label}
        {required && <span className="text-destructive ms-1">*</span>}
      </FormLabel>
      <Input
        id={name}
        name={name}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        leadingIcon={leadingIcon}
        trailingIcon={trailingIcon}
        invalid={!!error}
        disabled={disabled}
        autoFocus={autoFocus}
        autoComplete={autoComplete}
      />
      {hint && !error && <FormHint>{hint}</FormHint>}
      {error && <FormError>{error}</FormError>}
    </FormField>
  );
}