import { FormHint } from "@/components/ui/form-field";

export interface FormCheckboxFieldProps {
  label: string;
  name: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  hint?: string;
  disabled?: boolean;
  required?: boolean;
}

export function FormCheckboxField({
  label,
  name,
  checked,
  onChange,
  hint,
  disabled = false,
  required = false,
}: FormCheckboxFieldProps) {
  return (
    <div className="flex items-start gap-3">
      <input
        id={name}
        name={name}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        required={required}
        className="h-4 w-4 rounded border border-border bg-background text-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 mt-1"
      />
      <div className="flex-1 space-y-1">
        <label
          htmlFor={name}
          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
        >
          {label}
          {required && <span className="text-destructive ms-1">*</span>}
        </label>
        {hint && <FormHint>{hint}</FormHint>}
      </div>
    </div>
  );
}