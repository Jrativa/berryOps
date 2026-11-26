import { useId } from "react";
import { motion } from "motion/react";

import { cn } from "@/shared/lib/utils";
import { springSnappy } from "@/shared/lib/motion";

interface Option<T extends string> {
  value: T;
  label: string;
}

interface SegmentedControlProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: Option<T>[];
  ariaLabel: string;
  className?: string;
}

/** Selector segmentado: la píldora activa se desliza con un spring (y se puede redirigir a mitad). */
export function SegmentedControl<T extends string>({
  value,
  onChange,
  options,
  ariaLabel,
  className,
}: SegmentedControlProps<T>) {
  const id = useId();

  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn("inline-flex rounded-control bg-midnight/[0.06] p-1", className)}
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.value)}
            className={cn(
              "relative min-h-9 flex-1 whitespace-nowrap rounded-[10px] px-3.5 text-sm font-medium transition-colors",
              active ? "text-midnight" : "text-dusty hover:text-midnight",
            )}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                transition={springSnappy}
                className="absolute inset-0 rounded-[10px] bg-surface shadow-sm"
              />
            )}
            <span className="relative">{o.label}</span>
          </button>
        );
      })}
    </div>
  );
}
