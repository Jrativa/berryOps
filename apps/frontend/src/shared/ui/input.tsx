import * as React from "react";

import { cn } from "@/shared/lib/utils";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      className={cn(
        "h-12 w-full min-w-0 rounded-control border border-hairline bg-surface px-4 text-base text-midnight",
        "placeholder:text-dusty/60 outline-none transition-[border-color,box-shadow] duration-150",
        "focus-visible:border-purple/60 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-purple/15",
        "aria-invalid:border-danger/60 aria-invalid:ring-danger/10",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
