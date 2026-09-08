import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormHint, FormError } from "@/components/ui/form-field";

export interface FormNumberFieldProps {
  label: string;
  name: string;
  value: string | number;
  onChange: (value: string) => void;
  error?: string;
  hint?: string;
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  required?: boolean;
  disabled?: boolean;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
}

export function FormNumberField({
  label,
  name,
  value,
  onChange,
  error,
  hint,
  placeholder,
  min,
  max,
  step = 1,
  required = false,
  disabled = false,
  leadingIcon,
  trailingIcon,
}: FormNumberFieldProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    // Allow empty string or valid numbers
    if (val === "" || !isNaN(Number(val))) {
      onChange(val);
    }
  };

  return (
    <FormField>
      <FormLabel htmlFor={name}>
        {label}
        {required && <span className="text-destructive ms-1">*</span>}
      </FormLabel>
      <Input
        id={name}
        name={name}
        type="number"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        min={min}
        max={max}
        step={step}
        invalid={!!error}
        disabled={disabled}
        leadingIcon={leadingIcon}
        trailingIcon={trailingIcon}
      />
      {hint && !error && <FormHint>{hint}</FormHint>}
      {error && <FormError>{error}</FormError>}
    </FormField>
  );
}