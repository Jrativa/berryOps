import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { AnimatePresence, motion } from "motion/react";
import { CheckSquare, Grid3x3, MousePointerClick, Plus, Search } from "lucide-react";

import { formatNumber } from "@/shared/lib/format";
import { spring } from "@/shared/lib/motion";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Sheet } from "@/shared/ui/sheet";
import { Spinner } from "@/shared/ui/spinner";
import { useInventoryStore } from "../application/inventoryStore";
import { computeStats, usePlantsStore } from "../application/plantsStore";
import { PLANT_STATUSES, type Plot, type PlantBrief } from "../infrastructure/api";
import { GridSheet } from "./grid-sheet";
import { ObservationForm } from "./observation-form";
import { PlantGrid } from "./plant-grid";
import { PlantSheet, StatusPill } from "./plant-sheet";
import { SEVERITY, STATUS_META } from "./plant-status";

const LIST_LIMIT = 50;

function Stat({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded-card border border-hairline bg-surface p-5">
      <p className="text-sm font-medium text-dusty">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-tight [font-variant-numeric:tabular-nums]">
        {value}
        {unit && <span className="ml-1 text-base font-medium text-dusty">{unit}</span>}
      </p>
    </div>
  );
}

export function PlantsPanel({ plot }: { plot: Plot }) {
  const { t } = useTranslation();
  const {
    plants, loading, error, selecting, selected, filter,
    load, generate, observeOne, observeSelected, setSelecting, toggle, clearSelection, setFilter,
  } = usePlantsStore();

  const [gridOpen, setGridOpen] = useState(false);
  const [open, setOpen] = useState<PlantBrief | null>(null);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [search, setSearch] = useState({ row: "", col: "" });
  const [searchError, setSearchError] = useState(false);

  useEffect(() => {
    void load(plot.id);
  }, [plot.id, load]);

  const stats = useMemo(() => computeStats(plants), [plants]);
  const issues = useMemo(
    () =>
      plants
        .filter((p) => p.status !== "healthy")
        .sort((a, b) => SEVERITY[a.status] - SEVERITY[b.status] || a.row - b.row || a.col - b.col),
    [plants],
  );
  const needAttention = stats.total - stats.counts.healthy;

  const findPlant = (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    const plant = plants.find((p) => p.row === Number(search.row) && p.col === Number(search.col));
    setSearchError(!plant);
    if (plant) setOpen(plant);
  };

  if (loading && plants.length === 0) {
    return (
      <div className="mt-16 flex justify-center text-dusty" aria-live="polite">
        <Spinner className="size-6" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-8 rounded-card border border-hairline bg-surface p-8 text-center">
        <p className="text-danger">{t("inventory.error.generic")}</p>
        <Button variant="secondary" className="mt-4" onClick={() => void load(plot.id)}>
          {t("inventory.retry")}
        </Button>
      </div>
    );
  }

  const gridSheet = (
    <GridSheet
      open={gridOpen}
      onClose={() => setGridOpen(false)}
      current={{ rows: stats.rows, columns: stats.columns, total: stats.total }}
      onSubmit={async (rows, columns) => {
        await generate(plot.id, rows, columns);
        // Mantiene al día el contador del encabezado del lote
        const total = usePlantsStore.getState().plants.length;
        useInventoryStore.setState((s) => (s.plot ? { plot: { ...s.plot, plant_count: total } } : s));
      }}
    />
  );

  if (stats.total === 0) {
    return (
      <>
        <div className="mt-8 flex flex-col items-center rounded-card border border-hairline bg-surface px-6 py-14 text-center">
          <div className="grid size-14 place-items-center rounded-2xl bg-purple/10 text-purple">
            <Grid3x3 className="size-7" strokeWidth={1.75} aria-hidden />
          </div>
          <h2 className="mt-5 text-2xl font-semibold">{t("plants.empty.title")}</h2>
          <p className="mt-2 max-w-md text-dusty">{t("plants.empty.desc")}</p>
          <Button className="mt-6" onClick={() => setGridOpen(true)}>
            <Plus />
            {t("plants.grid.generate")}
          </Button>
        </div>
        {gridSheet}
      </>
    );
  }

  return (
    <div className="mt-8">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label={t("plants.stats.total")} value={formatNumber(stats.total, 0)} />
        <Stat label={t("plants.stats.attention")} value={formatNumber(needAttention, 0)} />
        <Stat label={t("plants.stats.mortality")} value={formatNumber(stats.mortality)} unit="%" />
      </div>

      {/* Leyenda = filtro: resalta un estado y atenúa el resto del mapa */}
      <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label={t("plants.legend")}>
        {PLANT_STATUSES.map((s) => {
          const { icon: Icon, color } = STATUS_META[s];
          const active = filter === s;
          return (
            <button
              key={s}
              type="button"
              aria-pressed={active}
              onClick={() => setFilter(active ? null : s)}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                active ? "border-midnight bg-midnight text-cream" : "border-hairline bg-surface hover:bg-midnight/[0.04]",
              )}
            >
              <span className="grid size-4 place-items-center rounded-full" style={{ background: color }}>
                <Icon className="size-2.5 text-midnight/80" aria-hidden />
              </span>
              {t(`plants.status.${s}`)}
              <span className={active ? "text-cream/70" : "text-dusty"}>{formatNumber(stats.counts[s], 0)}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <form onSubmit={findPlant} className="flex items-center gap-2" role="search">
          <Input
            aria-label={t("plants.search.row")}
            placeholder={t("plants.search.row")}
            inputMode="numeric"
            value={search.row}
            onChange={(e) => setSearch({ ...search, row: e.target.value.replace(/\D/g, "") })}
            className="h-10 w-24"
          />
          <Input
            aria-label={t("plants.search.col")}
            placeholder={t("plants.search.col")}
            inputMode="numeric"
            value={search.col}
            onChange={(e) => setSearch({ ...search, col: e.target.value.replace(/\D/g, "") })}
            className="h-10 w-28"
          />
          <Button type="submit" variant="secondary" size="sm" disabled={!search.row || !search.col} className="h-10">
            <Search />
            {t("plants.search.go")}
          </Button>
        </form>

        <div className="ml-auto flex gap-2">
          <Button
            variant={selecting ? "primary" : "secondary"}
            size="sm"
            className="h-10"
            aria-pressed={selecting}
            onClick={() => setSelecting(!selecting)}
          >
            {selecting ? <CheckSquare /> : <MousePointerClick />}
            {selecting ? t("plants.select.done") : t("plants.select.start")}
          </Button>
          <Button variant="secondary" size="sm" className="h-10" onClick={() => setGridOpen(true)}>
            <Plus />
            {t("plants.grid.extend")}
          </Button>
        </div>
      </div>
      <p aria-live="polite" className="min-h-5 pt-1 text-sm text-danger">
        {searchError ? t("plants.search.notFound") : ""}
      </p>
      {selecting && <p className="pb-2 text-sm text-dusty">{t("plants.select.hint")}</p>}

      <div className="mt-1 max-h-[70vh] overflow-auto rounded-card border border-hairline bg-surface p-4">
        <PlantGrid
          plants={plants}
          rows={stats.rows}
          columns={stats.columns}
          selected={selected}
          filter={filter}
          selecting={selecting}
          onOpen={setOpen}
          onToggle={toggle}
        />
      </div>

      {/* Lista equivalente al mapa: no depende del color y se lee con lector de pantalla */}
      <section className="mt-10" aria-labelledby="issues-title">
        <h2 id="issues-title" className="mb-3 text-xl font-semibold">
          {t("plants.issues.title")}
        </h2>
        {issues.length === 0 ? (
          <p className="rounded-card border border-dashed border-hairline px-6 py-10 text-center text-dusty">
            {t("plants.issues.empty")}
          </p>
        ) : (
          <>
            <ul className="overflow-hidden rounded-card border border-hairline bg-surface">
              {issues.slice(0, LIST_LIMIT).map((p) => (
                <li key={p.id} className="border-b border-hairline last:border-b-0">
                  <button
                    type="button"
                    onClick={() => setOpen(p)}
                    className="flex w-full items-center justify-between gap-4 px-5 py-3.5 text-left transition-colors hover:bg-midnight/[0.02]"
                  >
                    <span className="font-medium [font-variant-numeric:tabular-nums]">
                      {t("plants.position", { row: p.row, col: p.col })}
                    </span>
                    <StatusPill status={p.status} />
                  </button>
                </li>
              ))}
            </ul>
            {issues.length > LIST_LIMIT && (
              <p className="mt-2 px-1 text-sm text-dusty">
                {t("plants.issues.more", { count: issues.length - LIST_LIMIT })}
              </p>
            )}
          </>
        )}
      </section>

      {/* Barra de selección flotante */}
      <AnimatePresence>
        {selected.size > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={spring}
            className="glass fixed inset-x-0 bottom-6 z-40 mx-auto flex w-[calc(100%-3rem)] max-w-md items-center justify-between gap-3 rounded-full border border-hairline px-5 py-2.5 shadow-xl"
          >
            <p className="text-sm font-medium [font-variant-numeric:tabular-nums]">
              {t("plants.select.count", { count: selected.size })}
            </p>
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" onClick={clearSelection}>
                {t("plants.select.clear")}
              </Button>
              <Button size="sm" onClick={() => setBulkOpen(true)}>
                {t("plants.select.record")}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <PlantSheet plant={open} onClose={() => setOpen(null)} onObserve={observeOne} />

      <Sheet
        open={bulkOpen}
        onClose={() => setBulkOpen(false)}
        title={t("plants.bulk.title", { count: selected.size })}
      >
        <div className="pt-2">
          <ObservationForm
            submitLabel={t("plants.bulk.save", { count: selected.size })}
            onSubmit={async (data) => {
              await observeSelected(plot.id, data);
            }}
            onDone={() => setBulkOpen(false)}
          />
        </div>
      </Sheet>

      {gridSheet}
    </div>
  );
}
