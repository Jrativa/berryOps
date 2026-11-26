import { memo, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { PlantBrief, PlantStatus } from "../infrastructure/api";
import { STATUS_META } from "./plant-status";

interface Props {
  plants: PlantBrief[];
  rows: number;
  columns: number;
  selected: Set<string>;
  filter: PlantStatus | null;
  selecting: boolean;
  onOpen: (plant: PlantBrief) => void;
  onToggle: (ids: string[], force?: boolean) => void;
}

function cellSize(columns: number) {
  return columns <= 24 ? 28 : columns <= 48 ? 20 : 14;
}

interface CellProps {
  plant: PlantBrief;
  label: string;
  selected: boolean;
  dimmed: boolean;
  cursor: boolean;
}

const Cell = memo(function Cell({ plant, label, selected, dimmed, cursor }: CellProps) {
  return (
    <div
      id={`cell-${plant.row}-${plant.col}`}
      role="gridcell"
      aria-selected={selected}
      aria-label={label}
      data-id={plant.id}
      data-r={plant.row}
      data-c={plant.col}
      className="cursor-pointer rounded-[4px] transition-opacity duration-150"
      style={{
        background: STATUS_META[plant.status].color,
        opacity: dimmed ? 0.18 : 1,
        outline: selected
          ? "2px solid var(--purple)"
          : cursor
            ? "2px solid color-mix(in oklch, var(--midnight) 60%, transparent)"
            : undefined,
        outlineOffset: selected || cursor ? -2 : undefined,
        boxShadow: selected ? "inset 0 0 0 4px var(--surface)" : undefined,
      }}
    />
  );
});

/**
 * Mapa del lote: una celda por planta, fila × columna. Pensado para miles de plantas:
 * los eventos se delegan en el contenedor (no hay un manejador por celda) y las celdas están memorizadas.
 * Teclado: flechas para moverse, Enter/Espacio para abrir o seleccionar.
 */
export function PlantGrid({ plants, rows, columns, selected, filter, selecting, onOpen, onToggle }: Props) {
  const { t } = useTranslation();
  const size = cellSize(columns);
  const [cursor, setCursor] = useState<{ r: number; c: number } | null>(null);
  const drag = useRef<{ force: boolean } | null>(null);

  const cells = useMemo(() => {
    const grid: (PlantBrief | null)[] = new Array(rows * columns).fill(null);
    for (const p of plants) grid[(p.row - 1) * columns + (p.col - 1)] = p;
    return grid;
  }, [plants, rows, columns]);

  const byId = useMemo(() => new Map(plants.map((p) => [p.id, p])), [plants]);
  const showEvery = size >= 20 ? 1 : 5;

  const label = (p: PlantBrief) =>
    t("plants.cell.label", { row: p.row, col: p.col, status: t(`plants.status.${p.status}`) });

  const plantFrom = (target: EventTarget | null): PlantBrief | undefined => {
    const el = (target as HTMLElement | null)?.closest?.("[data-id]") as HTMLElement | null;
    return el ? byId.get(el.dataset.id!) : undefined;
  };

  const activate = (plant: PlantBrief) => {
    if (selecting) onToggle([plant.id]);
    else onOpen(plant);
  };

  const rowIds = (r: number) => cells.slice((r - 1) * columns, r * columns).filter(Boolean).map((p) => p!.id);
  const colIds = (c: number) => plants.filter((p) => p.col === c).map((p) => p.id);

  const onKeyDown = (e: React.KeyboardEvent) => {
    const cur = cursor ?? { r: 1, c: 1 };
    const move = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[e.key];
    if (move) {
      e.preventDefault();
      const next = {
        r: Math.min(rows, Math.max(1, cur.r + move[0])),
        c: Math.min(columns, Math.max(1, cur.c + move[1])),
      };
      setCursor(next);
      document.getElementById(`cell-${next.r}-${next.c}`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      const plant = cells[(cur.r - 1) * columns + (cur.c - 1)];
      if (plant) activate(plant);
    }
  };

  const header = "grid place-items-center text-[10px] font-medium text-dusty";

  return (
    <div
      role="grid"
      aria-label={t("plants.grid.label")}
      aria-rowcount={rows}
      aria-colcount={columns}
      aria-activedescendant={cursor ? `cell-${cursor.r}-${cursor.c}` : undefined}
      tabIndex={0}
      onKeyDown={onKeyDown}
      onFocus={() => setCursor((c) => c ?? { r: 1, c: 1 })}
      onBlur={() => setCursor(null)}
      onPointerDown={(e) => {
        const plant = plantFrom(e.target);
        if (!plant) return;
        if (selecting && e.pointerType === "mouse") {
          // Arrastrar para seleccionar varias: el primer gesto decide si se añade o se quita
          drag.current = { force: !selected.has(plant.id) };
          onToggle([plant.id], drag.current.force);
        }
      }}
      onPointerOver={(e) => {
        if (!drag.current) return;
        const plant = plantFrom(e.target);
        if (plant) onToggle([plant.id], drag.current.force);
      }}
      onPointerUp={() => {
        drag.current = null;
      }}
      onPointerLeave={() => {
        drag.current = null;
      }}
      onClick={(e) => {
        const plant = plantFrom(e.target);
        // En modo selección el clic con ratón ya se resolvió en pointerdown (soporta arrastre)
        if (plant && !(selecting && (e.nativeEvent as PointerEvent).pointerType === "mouse")) activate(plant);
      }}
      className="inline-grid select-none gap-[2px] outline-none"
      style={{ gridTemplateColumns: `${size}px repeat(${columns}, ${size}px)` }}
    >
      <div />
      {Array.from({ length: columns }, (_, i) => i + 1).map((c) => (
        <button
          key={`h${c}`}
          type="button"
          tabIndex={-1}
          aria-label={t("plants.grid.selectCol", { col: c })}
          onClick={() => onToggle(colIds(c))}
          className={`${header} h-5 rounded hover:bg-midnight/[0.06] hover:text-midnight`}
        >
          {c === 1 || c % showEvery === 0 ? c : ""}
        </button>
      ))}

      {Array.from({ length: rows }, (_, i) => i + 1).map((r) => (
        <RowFragment
          key={r}
          r={r}
          columns={columns}
          size={size}
          cells={cells}
          showEvery={showEvery}
          headerClass={header}
          rowLabel={t("plants.grid.selectRow", { row: r })}
          onRow={() => onToggle(rowIds(r))}
          selected={selected}
          filter={filter}
          cursor={cursor}
          label={label}
        />
      ))}
    </div>
  );
}

interface RowProps {
  r: number;
  columns: number;
  size: number;
  cells: (PlantBrief | null)[];
  showEvery: number;
  headerClass: string;
  rowLabel: string;
  onRow: () => void;
  selected: Set<string>;
  filter: PlantStatus | null;
  cursor: { r: number; c: number } | null;
  label: (p: PlantBrief) => string;
}

function RowFragment({ r, columns, size, cells, showEvery, headerClass, rowLabel, onRow, selected, filter, cursor, label }: RowProps) {
  return (
    <div role="row" className="contents">
      <button
        type="button"
        tabIndex={-1}
        aria-label={rowLabel}
        onClick={onRow}
        className={`${headerClass} rounded hover:bg-midnight/[0.06] hover:text-midnight`}
        style={{ height: size }}
      >
        {r === 1 || r % showEvery === 0 ? r : ""}
      </button>
      {Array.from({ length: columns }, (_, i) => {
        const plant = cells[(r - 1) * columns + i];
        if (!plant) return <div key={i} style={{ height: size }} />;
        return (
          <Cell
            key={plant.id}
            plant={plant}
            label={label(plant)}
            selected={selected.has(plant.id)}
            dimmed={filter !== null && plant.status !== filter}
            cursor={cursor?.r === plant.row && cursor?.c === plant.col}
          />
        );
      })}
    </div>
  );
}
