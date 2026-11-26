import type { ReactNode } from "react";
import { motion, type HTMLMotionProps } from "motion/react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";
import { springSnappy } from "@/shared/lib/motion";
import { Spinner } from "@/shared/ui/spinner";

const buttonVariants = cva(
  "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap font-medium outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        primary: "bg-purple text-cream hover:bg-purple-dark",
        secondary: "bg-midnight/[0.06] text-midnight hover:bg-midnight/10",
        ghost: "text-midnight/70 hover:bg-midnight/[0.06] hover:text-midnight",
      },
      size: {
        sm: "h-9 rounded-full px-4 text-sm",
        md: "h-11 rounded-control px-5 text-[0.9375rem]",
        lg: "h-12 rounded-control px-6 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

type ButtonProps = Omit<HTMLMotionProps<"button">, "children"> &
  VariantProps<typeof buttonVariants> & { loading?: boolean; children?: ReactNode };

/**
 * La retroalimentación ocurre al presionar (pointer-down), no al soltar:
 * `whileTap` escala el botón de inmediato y vuelve con un spring sin rebote.
 */
function Button({ className, variant, size, loading, disabled, children, ...props }: ButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      transition={springSnappy}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </motion.button>
  );
}

export { Button };
