import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../application/inventoryStore";
import type { Plot, PlotInput } from "../infrastructure/api";
import { todayISO } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import { FormField } from "@/shared/ui/form-field";
import { Input } from "@/shared/ui/input";
import { Sheet } from "@/shared/ui/sheet";

const VARIETIES = ["Biloxi", "Bluecrop", "Duke", "Emerald", "Jewel", "Legacy", "Misty", "O'Neal"];

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: PlotInput) => Promise<void>;
  plot?: Plot | null;
}

export function PlotSheet({ open, onClose, onSubmit, plot }: Props) {
  const { t } = useTranslation();
  return (
    <Sheet open={open} onClose={onClose} title={plot ? t("inventory.plot.edit") : t("inventory.plot.new")}>
      <PlotForm onClose={onClose} onSubmit={onSubmit} plot={plot} />
    </Sheet>
  );
}

function PlotForm({ onClose, onSubmit, plot }: Omit<Props, "open">) {
  const { t } = useTranslation();
  const [name, setName] = useState(plot?.name ?? "");
  const [variety, setVariety] = useState(plot?.variety ?? "");
  const [area, setArea] = useState(plot ? String(plot.area_ha) : "");
  const [planting, setPlanting] = useState(plot?.planting_date ?? "");
  const [plants, setPlants] = useState(plot?.plant_count != null ? String(plot.plant_count) : "");
  const [notes, setNotes] = useState(plot?.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const areaNum = Number(area.replace(",", "."));
  const valid = name.trim() !== "" && variety.trim() !== "" && areaNum > 0;

  const submit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        name: name.trim(),
        variety: variety.trim(),
        area_ha: areaNum,
        planting_date: planting || null,
        plant_count: plants ? Number(plants) : null,
        notes: notes.trim() || null,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-5 pt-2" noValidate>
      <FormField id="plot-name" label={t("inventory.plot.name")} hint={t("inventory.plot.name.hint")}>
        <Input id="plot-name" value={name} maxLength={100} onChange={(e) => setName(e.target.value)} required />
      </FormField>

      <FormField id="plot-variety" label={t("inventory.plot.variety")}>
        <Input
          id="plot-variety"
          list="varieties"
          value={variety}
          maxLength={100}
          onChange={(e) => setVariety(e.target.value)}
          required
        />
        <datalist id="varieties">
          {VARIETIES.map((v) => (
            <option key={v} value={v} />
          ))}
        </datalist>
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField id="plot-area" label={t("inventory.plot.area")}>
          <Input id="plot-area" inputMode="decimal" value={area} onChange={(e) => setArea(e.target.value)} required />
        </FormField>
        <FormField id="plot-plants" label={t("inventory.plot.plants")}>
          <Input
            id="plot-plants"
            inputMode="numeric"
            value={plants}
            onChange={(e) => setPlants(e.target.value.replace(/\D/g, ""))}
          />
        </FormField>
      </div>

      <FormField id="plot-planting" label={t("inventory.plot.planting")}>
        <Input id="plot-planting" type="date" value={planting} max={todayISO()} onChange={(e) => setPlanting(e.target.value)} />
      </FormField>

      <FormField id="plot-notes" label={t("inventory.notes")}>
        <Input id="plot-notes" value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} />
      </FormField>

      <div aria-live="polite" className="-mt-2 min-h-5">
        {error && <p className="text-sm text-danger">{error}</p>}
      </div>

      <Button type="submit" size="lg" loading={saving} disabled={!valid}>
        {t("inventory.save")}
      </Button>
    </form>
  );
}
