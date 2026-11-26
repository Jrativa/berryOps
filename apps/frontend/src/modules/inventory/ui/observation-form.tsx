import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../application/inventoryStore";
import { PLANT_STATUSES, type ObservationInput, type PlantStatus } from "../infrastructure/api";
import { todayISO } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import { FormField } from "@/shared/ui/form-field";
import { Input } from "@/shared/ui/input";
import { SegmentedControl } from "@/shared/ui/segmented-control";

interface Props {
  initialStatus?: PlantStatus;
  submitLabel: string;
  onSubmit: (data: ObservationInput) => Promise<void>;
  onDone: () => void;
}

/** Formulario común para registrar el estado de una planta o de varias a la vez. */
export function ObservationForm({ initialStatus = "healthy", submitLabel, onSubmit, onDone }: Props) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<PlantStatus>(initialStatus);
  const [notes, setNotes] = useState("");
  const [day, setDay] = useState(todayISO());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ status, notes: notes.trim() || null, observed_on: day });
      onDone();
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-5" noValidate>
      <FormField id="obs-status" label={t("plants.obs.status")} hint={t(`plants.status.${status}.hint`)}>
        <SegmentedControl
          ariaLabel={t("plants.obs.status")}
          value={status}
          onChange={setStatus}
          options={PLANT_STATUSES.map((s) => ({ value: s, label: t(`plants.status.${s}`) }))}
          className="w-full"
        />
      </FormField>

      <FormField id="obs-notes" label={t("inventory.notes")}>
        <Input
          id="obs-notes"
          value={notes}
          maxLength={500}
          placeholder={t("plants.obs.notes.placeholder")}
          onChange={(e) => setNotes(e.target.value)}
        />
      </FormField>

      <FormField id="obs-day" label={t("plants.obs.date")}>
        <Input id="obs-day" type="date" value={day} max={todayISO()} onChange={(e) => setDay(e.target.value)} required />
      </FormField>

      <div aria-live="polite" className="-mt-2 min-h-5">
        {error && <p className="text-sm text-danger">{error}</p>}
      </div>

      <Button type="submit" size="lg" loading={saving} disabled={!day}>
        {submitLabel}
      </Button>
    </form>
  );
}
