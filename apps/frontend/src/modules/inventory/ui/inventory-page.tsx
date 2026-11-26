import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "motion/react";
import { ChevronRight, Plus, Sprout } from "lucide-react";

import { Navbar } from "@/modules/home/ui/navbar";
import { formatDay, formatKg, formatNumber } from "@/shared/lib/format";
import { riseIn, stagger } from "@/shared/lib/motion";
import { Button } from "@/shared/ui/button";
import { SegmentedControl } from "@/shared/ui/segmented-control";
import { Spinner } from "@/shared/ui/spinner";
import { periodStart, useInventoryStore, type Period } from "../application/inventoryStore";
import { inventoryAPI } from "../infrastructure/api";
import { ExportButton } from "./export-button";
import { GradeBars } from "./grade-bars";
import { MonthChart } from "./month-chart";
import { PlotSheet } from "./plot-sheet";

const PERIODS: Period[] = ["30d", "12m", "all"];

function Kpi({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded-card border border-hairline bg-surface p-6">
      <p className="text-sm font-medium text-dusty">{label}</p>
      <p className="mt-2 text-4xl font-semibold tracking-tight [font-variant-numeric:tabular-nums]">
        {value}
        {unit && <span className="ml-1 text-lg font-medium text-dusty">{unit}</span>}
      </p>
    </div>
  );
}

export function InventoryPage() {
  const { t } = useTranslation();
  const { plots, summary, period, loading, error, setPeriod, loadOverview, createPlot } = useInventoryStore();
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  const byPlot = new Map(summary?.by_plot.map((p) => [p.plot_id, p]));
  const firstLoad = loading && !summary;

  return (
    <div className="min-h-dvh">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 pb-24 pt-24">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl font-semibold sm:text-5xl">{t("inventory.title")}</h1>
            <p className="mt-2 text-base text-dusty">{t("inventory.subtitle")}</p>
          </div>
          <Button onClick={() => setCreating(true)}>
            <Plus />
            {t("inventory.plot.new")}
          </Button>
        </div>

        {firstLoad && (
          <div className="mt-24 flex justify-center text-dusty" aria-live="polite">
            <Spinner className="size-6" />
          </div>
        )}

        {error && !summary && (
          <div className="mt-12 rounded-card border border-hairline bg-surface p-8 text-center">
            <p className="text-danger">{error}</p>
            <Button variant="secondary" className="mt-4" onClick={() => void loadOverview()}>
              {t("inventory.retry")}
            </Button>
          </div>
        )}

        {summary && plots.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-12 flex flex-col items-center rounded-card border border-hairline bg-surface px-6 py-16 text-center"
          >
            <div className="grid size-14 place-items-center rounded-2xl bg-purple/10 text-purple">
              <Sprout className="size-7" strokeWidth={1.75} aria-hidden />
            </div>
            <h2 className="mt-5 text-2xl font-semibold">{t("inventory.empty.title")}</h2>
            <p className="mt-2 max-w-sm text-dusty">{t("inventory.empty.desc")}</p>
            <Button className="mt-6" onClick={() => setCreating(true)}>
              <Plus />
              {t("inventory.empty.cta")}
            </Button>
          </motion.div>
        )}

        {summary && plots.length > 0 && (
          <motion.div variants={stagger} initial="hidden" animate="show" className="mt-8">
            <motion.div variants={riseIn} className="mb-6 flex flex-wrap items-center justify-between gap-3">
              <SegmentedControl
                ariaLabel={t("inventory.period.label")}
                value={period}
                onChange={setPeriod}
                options={PERIODS.map((p) => ({ value: p, label: t(`inventory.period.${p}`) }))}
              />
              <div className="flex flex-wrap items-center gap-2">
                <ExportButton
                  label={t("inventory.export.harvests")}
                  onExport={() => inventoryAPI.exportCsv("harvests", { from: periodStart(period) })}
                />
                <ExportButton
                  label={t("inventory.export.costs")}
                  onExport={() => inventoryAPI.exportCsv("costs", { from: periodStart(period) })}
                />
              </div>
            </motion.div>

            <motion.div
              variants={riseIn}
              className={`grid gap-4 sm:grid-cols-3 transition-opacity ${loading ? "opacity-60" : ""}`}
            >
              <Kpi label={t("inventory.kpi.total")} value={formatNumber(summary.total_kg)} unit="kg" />
              <Kpi label={t("inventory.kpi.yield")} value={formatNumber(summary.yield_kg_per_ha)} unit="kg/ha" />
              <Kpi
                label={t("inventory.kpi.last")}
                value={summary.last_harvest_on ? formatDay(summary.last_harvest_on, { day: "numeric", month: "short" }) : "—"}
              />
            </motion.div>

            {summary.total_cost > 0 && (
              <motion.div
                variants={riseIn}
                className={`mt-4 grid gap-4 sm:grid-cols-3 transition-opacity ${loading ? "opacity-60" : ""}`}
              >
                <Kpi label={t("inventory.kpi.cost")} value={formatNumber(summary.total_cost, 2)} />
                <Kpi
                  label={t("inventory.kpi.costPerKg")}
                  value={summary.cost_per_kg != null ? formatNumber(summary.cost_per_kg, 2) : "—"}
                />
                <div className="rounded-card border border-hairline bg-surface p-6">
                  <p className="text-sm font-medium text-dusty">{t("inventory.cost.byCategory")}</p>
                  <ul className="mt-2 flex flex-col gap-1 text-sm">
                    {summary.by_category.map((c) => (
                      <li key={c.category} className="flex justify-between gap-3">
                        <span className="text-dusty">{t(`inventory.cost.${c.category}`)}</span>
                        <span className="font-medium [font-variant-numeric:tabular-nums]">{formatNumber(c.total, 2)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </motion.div>
            )}

            <motion.section variants={riseIn} className="mt-4 rounded-card border border-hairline bg-surface p-6">
              <h2 className="mb-4 text-xl font-semibold">{t("inventory.chart.title")}</h2>
              {summary.by_month.length > 0 ? (
                <MonthChart data={summary.by_month} />
              ) : (
                <p className="py-10 text-center text-dusty">{t("inventory.chart.empty")}</p>
              )}
            </motion.section>

            <div className="mt-4 grid gap-4 lg:grid-cols-5">
              <motion.section variants={riseIn} className="rounded-card border border-hairline bg-surface p-6 lg:col-span-2">
                <h2 className="mb-5 text-xl font-semibold">{t("inventory.grade.title")}</h2>
                {summary.by_grade.length > 0 ? (
                  <GradeBars data={summary.by_grade} />
                ) : (
                  <p className="text-dusty">{t("inventory.chart.empty")}</p>
                )}
              </motion.section>

              <motion.section variants={riseIn} className="lg:col-span-3">
                <h2 className="mb-3 px-1 text-xl font-semibold">{t("inventory.plots.title")}</h2>
                <ul className="flex flex-col gap-3">
                  {plots.map((plot) => {
                    const stats = byPlot.get(plot.id);
                    return (
                      <li key={plot.id}>
                        <motion.div whileTap={{ scale: 0.985 }} transition={{ type: "spring", bounce: 0, duration: 0.25 }}>
                          <Link
                            to={`/inventory/plots/${plot.id}`}
                            className="flex items-center gap-4 rounded-card border border-hairline bg-surface p-5 transition-colors hover:bg-midnight/[0.02]"
                          >
                            <div className="grid size-11 shrink-0 place-items-center rounded-control bg-purple/10 text-purple">
                              <Sprout className="size-5" strokeWidth={1.75} aria-hidden />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="truncate font-semibold">{plot.name}</p>
                              <p className="truncate text-sm text-dusty">
                                {plot.variety} · {formatNumber(plot.area_ha, 2)} ha
                              </p>
                            </div>
                            <div className="text-right text-sm">
                              <p className="font-semibold [font-variant-numeric:tabular-nums]">
                                {formatKg(stats?.total_kg ?? 0)}
                              </p>
                              {stats && <p className="text-dusty">{formatNumber(stats.yield_kg_per_ha)} kg/ha</p>}
                              {stats?.cost_per_kg != null && (
                                <p className="text-dusty">{t("inventory.cost.perKg", { value: formatNumber(stats.cost_per_kg, 2) })}</p>
                              )}
                            </div>
                            <ChevronRight className="size-5 shrink-0 text-dusty" aria-hidden />
                          </Link>
                        </motion.div>
                      </li>
                    );
                  })}
                </ul>
              </motion.section>
            </div>
          </motion.div>
        )}
      </main>

      <PlotSheet open={creating} onClose={() => setCreating(false)} onSubmit={async (data) => {
        await createPlot(data);
        void loadOverview();
      }} />
    </div>
  );
}
