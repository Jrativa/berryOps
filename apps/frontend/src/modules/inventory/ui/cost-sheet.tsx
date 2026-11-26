import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../application/inventoryStore";
import { COST_CATEGORIES, type CostCategory, type CostInput } from "../infrastructure/api";
import { todayISO } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import { FormField } from "@/shared/ui/form-field";
import { Input } from "@/shared/ui/input";
import { Sheet } from "@/shared/ui/sheet";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: CostInput) => Promise<void>;
}

export function CostSheet({ open, onClose, onSubmit }: Props) {
  const { t } = useTranslation();
  return (
    <Sheet open={open} onClose={onClose} title={t("inventory.cost.new")}>
      <CostForm onClose={onClose} onSubmit={onSubmit} />
    </Sheet>
  );
}

function CostForm({ onClose, onSubmit }: Omit<Props, "open">) {
  const { t } = useTranslation();
  const [amount, setAmount] = useState("");
  const [day, setDay] = useState(todayISO());
  const [category, setCategory] = useState<CostCategory>("labor");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const value = Number(amount.replace(",", "."));
  const valid = value > 0 && !!day;

  const submit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ incurred_on: day, category, amount: value, notes: notes.trim() || null });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-5 pt-2" noValidate>
      <FormField id="amount" label={t("inventory.cost.amount")} hint={t("inventory.cost.amount.hint")}>
        <Input
          id="amount"
          inputMode="decimal"
          autoComplete="off"
          placeholder="0"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="text-lg"
          required
        />
      </FormField>

      <FormField id="cost-category" label={t("inventory.cost.category")}>
        <select
          id="cost-category"
          value={category}
          onChange={(e) => setCategory(e.target.value as CostCategory)}
          className="h-11 w-full rounded-control border border-hairline bg-surface px-4 text-[0.9375rem] outline-none focus-visible:ring-2 focus-visible:ring-purple/40"
        >
          {COST_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {t(`inventory.cost.${c}`)}
            </option>
          ))}
        </select>
      </FormField>

      <FormField id="cost-day" label={t("inventory.cost.date")}>
        <Input id="cost-day" type="date" value={day} max={todayISO()} onChange={(e) => setDay(e.target.value)} required />
      </FormField>

      <FormField id="cost-notes" label={t("inventory.notes")}>
        <Input id="cost-notes" value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} />
      </FormField>

      <div aria-live="polite" className="-mt-2 min-h-5">
        {error && <p className="text-sm text-danger">{error}</p>}
      </div>

      <Button type="submit" size="lg" loading={saving} disabled={!valid}>
        {t("inventory.cost.save")}
      </Button>
    </form>
  );
}
