import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react";

import { Navbar } from "@/modules/home/ui/navbar";
import { formatDay, formatKg, formatNumber } from "@/shared/lib/format";
import { inventoryAPI } from "../infrastructure/api";
import { spring } from "@/shared/lib/motion";
import { Button } from "@/shared/ui/button";
import { SegmentedControl } from "@/shared/ui/segmented-control";
import { Spinner } from "@/shared/ui/spinner";
import { errorMessage, useInventoryStore } from "../application/inventoryStore";
import { CostSheet } from "./cost-sheet";
import { ExportButton } from "./export-button";
import { HarvestSheet } from "./harvest-sheet";
import { PlantsPanel } from "./plants-panel";
import { PlotSheet } from "./plot-sheet";

type Tab = "harvests" | "plants" | "costs";

export function PlotDetailPage() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  // La pestaña vive en la URL: se conserva al recargar y se puede compartir el enlace
  const [params, setParams] = useSearchParams();
  const requested = params.get("tab");
  const tab: Tab = requested === "plants" || requested === "costs" ? requested : "harvests";
  const setTab = (next: Tab) => setParams(next === "harvests" ? {} : { tab: next }, { replace: true });
  const {
    plot, harvests, costs, detailLoading, error,
    loadPlot, updatePlot, deletePlot, addHarvest, deleteHarvest, addCost, deleteCost,
  } = useInventoryStore();

  const [harvesting, setHarvesting] = useState(false);
  const [addingCost, setAddingCost] = useState(false);
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    void loadPlot(id);
  }, [id, loadPlot]);

  const total = harvests.reduce((sum, h) => sum + h.quantity_kg, 0);
  const hasHarvests = harvests.length > 0;
  const totalCost = costs.reduce((sum, c) => sum + c.amount, 0);

  const run = async (fn: () => Promise<void>) => {
    setActionError(null);
    try {
      await fn();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  };

  return (
    <div className="min-h-dvh">
      <Navbar />
      <main className="mx-auto max-w-3xl px-6 pb-24 pt-24">
        <Link to="/inventory" className="inline-flex items-center gap-1.5 text-sm font-medium text-dusty hover:text-midnight">
          <ArrowLeft className="size-4" aria-hidden />
          {t("inventory.title")}
        </Link>

        {detailLoading && (
          <div className="mt-24 flex justify-center text-dusty" aria-live="polite">
            <Spinner className="size-6" />
          </div>
        )}

        {error && !plot && !detailLoading && (
          <div className="mt-12 rounded-card border border-hairline bg-surface p-8 text-center">
            <p className="text-danger">{error}</p>
            <Button variant="secondary" className="mt-4" onClick={() => navigate("/inventory")}>
              {t("inventory.back")}
            </Button>
          </div>
        )}

        {plot && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={spring}>
            <div className="mt-6 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="text-4xl font-semibold sm:text-5xl">{plot.name}</h1>
                <p className="mt-2 text-base text-dusty">
                  {plot.variety} · {formatNumber(plot.area_ha, 2)} ha
                  {plot.planting_date && ` · ${t("inventory.plot.planted")} ${formatDay(plot.planting_date)}`}
                  {plot.plant_count != null && ` · ${formatNumber(plot.plant_count, 0)} ${t("inventory.plot.plants.unit")}`}
                </p>
                {plot.notes && <p className="mt-1 text-sm text-dusty">{plot.notes}</p>}
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
                  <Pencil />
                  {t("inventory.edit")}
                </Button>
              </div>
            </div>

            <SegmentedControl
              ariaLabel={t("plants.tabs.label")}
              value={tab}
              onChange={setTab}
              className="mt-8"
              options={[
                { value: "harvests", label: t("plants.tabs.harvests") },
                { value: "plants", label: t("plants.tabs.plants") },
                { value: "costs", label: t("plants.tabs.costs") },
              ]}
            />

            {tab === "plants" ? (
              <>
                <div className="mt-6 flex justify-end">
                  <ExportButton onExport={() => inventoryAPI.exportPlants(plot.id)} />
                </div>
                <PlantsPanel plot={plot} />
              </>
            ) : tab === "costs" ? (
              <>
                <div className="mt-6 flex items-center justify-between rounded-card border border-hairline bg-surface p-6">
                  <div>
                    <p className="text-sm font-medium text-dusty">{t("inventory.cost.total")}</p>
                    <p className="mt-1 text-4xl font-semibold tracking-tight [font-variant-numeric:tabular-nums]">
                      {formatNumber(totalCost, 2)}
                    </p>
                    <p className="mt-1 text-sm text-dusty">
                      {t("inventory.cost.count", { count: costs.length })}
                      {total > 0 && ` · ${t("inventory.cost.perKg", { value: formatNumber(totalCost / total, 2) })}`}
                    </p>
                  </div>
                  <Button size="lg" onClick={() => setAddingCost(true)}>
                    <Plus />
                    {t("inventory.cost.new")}
                  </Button>
                </div>

                <div aria-live="polite" className="min-h-6 px-1 pt-3">
                  {actionError && <p className="text-sm text-danger">{actionError}</p>}
                </div>

                {costs.length === 0 ? (
                  <p className="rounded-card border border-dashed border-hairline px-6 py-12 text-center text-dusty">
                    {t("inventory.cost.empty")}
                  </p>
                ) : (
                  <>
                    <ul className="overflow-hidden rounded-card border border-hairline bg-surface">
                      <AnimatePresence initial={false}>
                        {costs.map((c) => (
                          <motion.li
                            key={c.id}
                            layout
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={spring}
                            className="border-b border-hairline last:border-b-0"
                          >
                            <div className="flex items-center gap-4 px-5 py-4">
                              <div className="min-w-0 flex-1">
                                <p className="font-medium [font-variant-numeric:tabular-nums]">{formatDay(c.incurred_on)}</p>
                                {c.notes && <p className="truncate text-sm text-dusty">{c.notes}</p>}
                              </div>
                              <span className="rounded-full bg-midnight/[0.06] px-2.5 py-1 text-xs font-medium text-dusty">
                                {t(`inventory.cost.${c.category}`)}
                              </span>
                              <p className="w-24 text-right font-semibold [font-variant-numeric:tabular-nums]">
                                {formatNumber(c.amount, 2)}
                              </p>
                              <button
                                type="button"
                                aria-label={t("inventory.cost.delete")}
                                disabled={c.id.startsWith("temp-")}
                                onClick={() => run(() => deleteCost(c.id))}
                                className="grid size-9 place-items-center rounded-full text-dusty transition-colors hover:bg-danger/10 hover:text-danger disabled:opacity-40"
                              >
                                <Trash2 className="size-4" />
                              </button>
                            </div>
                          </motion.li>
                        ))}
                      </AnimatePresence>
                    </ul>
                    <div className="mt-4 flex justify-end">
                      <ExportButton onExport={() => inventoryAPI.exportCsv("costs", { plotId: plot.id })} />
                    </div>
                  </>
                )}
              </>
            ) : (
              <>
            <div className="mt-6 flex items-center justify-between rounded-card border border-hairline bg-surface p-6">
              <div>
                <p className="text-sm font-medium text-dusty">{t("inventory.harvest.total")}</p>
                <p className="mt-1 text-4xl font-semibold tracking-tight [font-variant-numeric:tabular-nums]">
                  {formatNumber(total)} <span className="text-lg font-medium text-dusty">kg</span>
                </p>
                <p className="mt-1 text-sm text-dusty">{t("inventory.harvest.count", { count: harvests.length })}</p>
              </div>
              <Button size="lg" onClick={() => setHarvesting(true)}>
                <Plus />
                {t("inventory.harvest.new")}
              </Button>
            </div>

            <div aria-live="polite" className="min-h-6 px-1 pt-3">
              {actionError && <p className="text-sm text-danger">{actionError}</p>}
            </div>

            {!hasHarvests ? (
              <p className="rounded-card border border-dashed border-hairline px-6 py-12 text-center text-dusty">
                {t("inventory.harvest.empty")}
              </p>
            ) : (
              <ul className="overflow-hidden rounded-card border border-hairline bg-surface">
                <AnimatePresence initial={false}>
                  {harvests.map((h) => (
                    <motion.li
                      key={h.id}
                      layout
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={spring}
                      className="border-b border-hairline last:border-b-0"
                    >
                      <div className="flex items-center gap-4 px-5 py-4">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium [font-variant-numeric:tabular-nums]">{formatDay(h.harvested_on)}</p>
                          {h.notes && <p className="truncate text-sm text-dusty">{h.notes}</p>}
                        </div>
                        <span className="rounded-full bg-midnight/[0.06] px-2.5 py-1 text-xs font-medium text-dusty">
                          {t(`inventory.grade.${h.grade}`)}
                        </span>
                        <p className="w-24 text-right font-semibold [font-variant-numeric:tabular-nums]">
                          {formatKg(h.quantity_kg)}
                        </p>
                        <button
                          type="button"
                          aria-label={t("inventory.harvest.delete")}
                          disabled={h.id.startsWith("temp-")}
                          onClick={() => run(() => deleteHarvest(h.id))}
                          className="grid size-9 place-items-center rounded-full text-dusty transition-colors hover:bg-danger/10 hover:text-danger disabled:opacity-40"
                        >
                          <Trash2 className="size-4" />
                        </button>
                      </div>
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ul>
            )}

            {hasHarvests && (
              <div className="mt-4 flex justify-end">
                <ExportButton onExport={() => inventoryAPI.exportCsv("harvests", { plotId: plot.id })} />
              </div>
            )}
              </>
            )}

            <div className="mt-10 border-t border-hairline pt-6">
              {!confirming ? (
                <Button variant="ghost" size="sm" onClick={() => setConfirming(true)} className="text-danger hover:bg-danger/10 hover:text-danger">
                  <Trash2 />
                  {hasHarvests ? t("inventory.plot.archive") : t("inventory.plot.delete")}
                </Button>
              ) : (
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-sm text-dusty">
                    {hasHarvests ? t("inventory.plot.archive.confirm") : t("inventory.plot.delete.confirm")}
                  </p>
                  <Button
                    size="sm"
                    className="bg-danger hover:bg-danger/90"
                    onClick={() =>
                      run(async () => {
                        await deletePlot(plot.id);
                        navigate("/inventory", { replace: true });
                      })
                    }
                  >
                    {t("inventory.confirm")}
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => setConfirming(false)}>
                    {t("inventory.cancel")}
                  </Button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </main>

      {plot && (
        <>
          <HarvestSheet
            open={harvesting}
            onClose={() => setHarvesting(false)}
            plantingDate={plot.planting_date}
            onSubmit={(data) => addHarvest(plot.id, data)}
          />
          <CostSheet open={addingCost} onClose={() => setAddingCost(false)} onSubmit={(data) => addCost(plot.id, data)} />
          <PlotSheet open={editing} onClose={() => setEditing(false)} plot={plot} onSubmit={(data) => updatePlot(plot.id, data)} />
        </>
      )}
    </div>
  );
}
