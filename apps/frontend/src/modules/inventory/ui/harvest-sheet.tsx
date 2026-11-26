import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../application/inventoryStore";
import { GRADES, type Grade, type HarvestInput } from "../infrastructure/api";
import { todayISO } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import { FormField } from "@/shared/ui/form-field";
import { Input } from "@/shared/ui/input";
import { SegmentedControl } from "@/shared/ui/segmented-control";
import { Sheet } from "@/shared/ui/sheet";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: HarvestInput) => Promise<void>;
  plantingDate?: string | null;
}

export function HarvestSheet({ open, onClose, onSubmit, plantingDate }: Props) {
  const { t } = useTranslation();
  return (
    <Sheet open={open} onClose={onClose} title={t("inventory.harvest.new")}>
      <HarvestForm onClose={onClose} onSubmit={onSubmit} plantingDate={plantingDate} />
    </Sheet>
  );
}

function HarvestForm({ onClose, onSubmit, plantingDate }: Omit<Props, "open">) {
  const { t } = useTranslation();
  const [kg, setKg] = useState("");
  const [day, setDay] = useState(todayISO());
  const [grade, setGrade] = useState<Grade>("standard");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const quantity = Number(kg.replace(",", "."));
  const valid = quantity > 0 && !!day;

  const submit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ harvested_on: day, quantity_kg: quantity, grade, notes: notes.trim() || null });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-5 pt-2" noValidate>
      <FormField id="kg" label={t("inventory.harvest.quantity")}>
        <div className="relative">
          <Input
            id="kg"
            inputMode="decimal"
            autoComplete="off"
            placeholder="0"
            value={kg}
            onChange={(e) => setKg(e.target.value)}
            className="pr-12 text-lg"
            required
          />
          <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-dusty">kg</span>
        </div>
      </FormField>

      <FormField id="day" label={t("inventory.harvest.date")}>
        <Input
          id="day"
          type="date"
          value={day}
          min={plantingDate ?? undefined}
          max={todayISO()}
          onChange={(e) => setDay(e.target.value)}
          required
        />
      </FormField>

      <FormField id="grade" label={t("inventory.harvest.grade")} hint={t(`inventory.grade.${grade}.hint`)}>
        <SegmentedControl
          ariaLabel={t("inventory.harvest.grade")}
          value={grade}
          onChange={setGrade}
          options={GRADES.map((g) => ({ value: g, label: t(`inventory.grade.${g}`) }))}
          className="w-full"
        />
      </FormField>

      <FormField id="notes" label={t("inventory.notes")}>
        <Input id="notes" value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} />
      </FormField>

      <div aria-live="polite" className="-mt-2 min-h-5">
        {error && <p className="text-sm text-danger">{error}</p>}
      </div>

      <Button type="submit" size="lg" loading={saving} disabled={!valid}>
        {t("inventory.harvest.save")}
      </Button>
    </form>
  );
}
