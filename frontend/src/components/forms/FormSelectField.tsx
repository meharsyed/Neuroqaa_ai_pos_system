import { Select } from "@/components/ui/select";
import { FormField, FormLabel, FormHint, FormError } from "@/components/ui/form-field";

interface SelectOption {
  value: string | number;
  label: string;
}

export interface FormSelectFieldProps {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  options?: SelectOption[];
  error?: string;
  hint?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function FormSelectField({
  label,
  name,
  value,
  onChange,
  options = [],
  error,
  hint,
  required = false,
  disabled = false,
  placeholder,
}: FormSelectFieldProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange(e.target.value);
  };

  return (
    <FormField>
      <FormLabel htmlFor={name}>
        {label}
        {required && <span className="text-destructive ms-1">*</span>}
      </FormLabel>
      <Select
        id={name}
        name={name}
        value={value}
        onChange={handleChange}
        options={options}
        placeholder={placeholder}
        disabled={disabled}
      />
      {hint && !error && <FormHint>{hint}</FormHint>}
      {error && <FormError>{error}</FormError>}
    </FormField>
  );
}