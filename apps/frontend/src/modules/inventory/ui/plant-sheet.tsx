import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { inventoryAPI, type PlantBrief, type PlantDetail } from "../infrastructure/api";
import { formatDay } from "@/shared/lib/format";
import { Sheet } from "@/shared/ui/sheet";
import { Spinner } from "@/shared/ui/spinner";
import { ObservationForm } from "./observation-form";
import { STATUS_META } from "./plant-status";

interface Props {
  plant: PlantBrief | null;
  onClose: () => void;
  onObserve: (plantId: string, data: Parameters<typeof inventoryAPI.observePlant>[1]) => Promise<void>;
}

function StatusPill({ status }: { status: PlantBrief["status"] }) {
  const { t } = useTranslation();
  const { icon: Icon, color } = STATUS_META[status];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-midnight/[0.06] px-2.5 py-1 text-xs font-medium">
      <span className="grid size-4 place-items-center rounded-full" style={{ background: color }}>
        <Icon className="size-2.5 text-midnight/80" aria-hidden />
      </span>
      {t(`plants.status.${status}`)}
    </span>
  );
}

export function PlantSheet({ plant, onClose, onObserve }: Props) {
  const { t } = useTranslation();
  return (
    <Sheet
      open={plant !== null}
      onClose={onClose}
      title={plant ? t("plants.sheet.title", { row: plant.row, col: plant.col }) : ""}
    >
      {plant && <PlantBody plant={plant} onClose={onClose} onObserve={onObserve} />}
    </Sheet>
  );
}

function PlantBody({ plant, onClose, onObserve }: { plant: PlantBrief } & Pick<Props, "onClose" | "onObserve">) {
  const { t } = useTranslation();
  const [detail, setDetail] = useState<PlantDetail | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    inventoryAPI
      .getPlant(plant.id)
      .then((d) => alive && setDetail(d))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [plant.id]);

  return (
    <div className="flex flex-col gap-6 pt-1">
      <div className="flex items-center gap-2 text-sm text-dusty">
        {t("plants.sheet.current")} <StatusPill status={plant.status} />
      </div>

      <ObservationForm
        initialStatus={plant.status}
        submitLabel={t("plants.obs.save")}
        onSubmit={(data) => onObserve(plant.id, data)}
        onDone={onClose}
      />

      <section aria-labelledby="history-title">
        <h3 id="history-title" className="mb-3 text-lg font-semibold">
          {t("plants.history.title")}
        </h3>
        {!detail && !failed && (
          <div className="flex justify-center py-4 text-dusty">
            <Spinner />
          </div>
        )}
        {failed && <p className="text-sm text-danger">{t("inventory.error.generic")}</p>}
        {detail && detail.observations.length === 0 && (
          <p className="rounded-control border border-dashed border-hairline px-4 py-6 text-center text-sm text-dusty">
            {t("plants.history.empty")}
          </p>
        )}
        {detail && detail.observations.length > 0 && (
          <ol className="flex flex-col gap-3 border-l border-hairline pl-4">
            {detail.observations.map((o) => (
              <li key={o.id} className="relative">
                <span
                  className="absolute -left-[1.4rem] top-1.5 size-2.5 rounded-full ring-4 ring-cream"
                  style={{ background: STATUS_META[o.status].color }}
                  aria-hidden
                />
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill status={o.status} />
                  <span className="text-xs text-dusty">{formatDay(o.observed_on)}</span>
                </div>
                {o.notes && <p className="mt-1 text-sm">{o.notes}</p>}
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

export { StatusPill };
