import type { ReactNode } from "react";

interface FormFieldProps {
  id: string;
  label: string;
  hint?: string;
  children: ReactNode;
}

export function FormField({ id, label, hint, children }: FormFieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium text-midnight">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-dusty">{hint}</p>}
    </div>
  );
}
