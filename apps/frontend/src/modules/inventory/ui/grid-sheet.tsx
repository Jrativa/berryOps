import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../application/inventoryStore";
import { formatNumber } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import { FormField } from "@/shared/ui/form-field";
import { Input } from "@/shared/ui/input";
import { Sheet } from "@/shared/ui/sheet";

const MAX_SIDE = 500;
const MAX_TOTAL = 50000;

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (rows: number, columns: number) => Promise<void>;
  /** Dimensiones actuales (0 si el lote aún no tiene plantas) */
  current: { rows: number; columns: number; total: number };
}

export function GridSheet({ open, onClose, onSubmit, current }: Props) {
  const { t } = useTranslation();
  const extending = current.total > 0;
  return (
    <Sheet open={open} onClose={onClose} title={extending ? t("plants.grid.extend") : t("plants.grid.generate")}>
      <GridForm onClose={onClose} onSubmit={onSubmit} current={current} />
    </Sheet>
  );
}

function GridForm({ onClose, onSubmit, current }: Omit<Props, "open">) {
  const { t } = useTranslation();
  const [rows, setRows] = useState(current.rows ? String(current.rows) : "");
  const [columns, setColumns] = useState(current.columns ? String(current.columns) : "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const r = Number(rows);
  const c = Number(columns);
  const total = r * c;
  const inRange = r >= 1 && c >= 1 && r <= MAX_SIDE && c <= MAX_SIDE && total <= MAX_TOTAL;
  // Las plantas existentes se conservan: solo se crean las posiciones que faltan
  const newPlants = inRange ? Math.max(total - current.total, 0) : 0;

  const submit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!inRange) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit(r, c);
      onClose();
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  };

  const digits = (v: string) => v.replace(/\D/g, "").slice(0, 3);

  return (
    <form onSubmit={submit} className="flex flex-col gap-5 pt-2" noValidate>
      <p className="text-sm text-dusty">{t("plants.grid.explain")}</p>

      <div className="grid grid-cols-2 gap-4">
        <FormField id="grid-rows" label={t("plants.grid.rows")}>
          <Input id="grid-rows" inputMode="numeric" value={rows} onChange={(e) => setRows(digits(e.target.value))} required />
        </FormField>
        <FormField id="grid-cols" label={t("plants.grid.columns")}>
          <Input id="grid-cols" inputMode="numeric" value={columns} onChange={(e) => setColumns(digits(e.target.value))} required />
        </FormField>
      </div>

      <p className="rounded-control bg-midnight/[0.05] px-4 py-3 text-sm" aria-live="polite">
        {inRange
          ? t("plants.grid.preview", { total: formatNumber(total, 0), created: formatNumber(newPlants, 0) })
          : t("plants.grid.limits", { side: MAX_SIDE, total: formatNumber(MAX_TOTAL, 0) })}
      </p>

      <div aria-live="polite" className="-mt-2 min-h-5">
        {error && <p className="text-sm text-danger">{error}</p>}
      </div>

      <Button type="submit" size="lg" loading={saving} disabled={!inRange || newPlants === 0}>
        {current.total > 0 ? t("plants.grid.extend") : t("plants.grid.generate")}
      </Button>
    </form>
  );
}
