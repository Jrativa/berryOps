import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { AnimatePresence, motion, useDragControls } from "motion/react";
import { X } from "lucide-react";

import { spring } from "@/shared/lib/motion";

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

interface SheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

/**
 * Hoja modal. Entra y sale por el mismo camino (desde abajo) y se puede arrastrar hacia abajo
 * desde el asa: se cierra según la velocidad del gesto, no solo por la distancia recorrida.
 * El arrastre solo se activa en el asa para no secuestrar los campos del formulario.
 */
export function Sheet({ open, onClose, title, children }: SheetProps) {
  const { t } = useTranslation();
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const controls = useDragControls();

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Foco al primer campo; Esc cierra; Tab queda atrapado dentro de la hoja
    const raf = requestAnimationFrame(() => {
      const first = panelRef.current?.querySelector<HTMLElement>("input,select,textarea");
      (first ?? panelRef.current)?.focus();
    });
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") return onClose();
      if (e.key !== "Tab" || !panelRef.current) return;
      const items = [...panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus();
    };
  }, [open, onClose]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] flex items-end justify-center sm:items-center sm:p-6">
          {/* Atenuar para enfocar: el fondo se aleja bajo un velo */}
          <motion.div
            className="absolute inset-0 bg-midnight/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            aria-hidden
          />
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            initial={{ opacity: 0, y: 48 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 48 }}
            transition={spring}
            drag="y"
            dragControls={controls}
            dragListener={false}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_, info) => {
              if (info.offset.y > 120 || info.velocity.y > 600) onClose();
            }}
            className="relative flex max-h-[92dvh] w-full max-w-lg flex-col overflow-hidden rounded-t-card bg-cream shadow-2xl outline-none sm:rounded-card"
          >
            <div
              className="flex cursor-grab touch-none justify-center pb-1 pt-2.5 active:cursor-grabbing sm:hidden"
              onPointerDown={(e) => controls.start(e)}
              aria-hidden
            >
              <div className="h-1.5 w-10 rounded-full bg-midnight/20" />
            </div>
            <div className="flex items-center justify-between px-6 pb-2 pt-3 sm:pt-6">
              <h2 id={titleId} className="text-2xl font-semibold">
                {title}
              </h2>
              <button
                type="button"
                onClick={onClose}
                aria-label={t("common.close")}
                className="grid size-9 place-items-center rounded-full text-dusty transition-colors hover:bg-midnight/[0.06] hover:text-midnight"
              >
                <X className="size-5" />
              </button>
            </div>
            <div className="overflow-y-auto px-6 pb-6">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
