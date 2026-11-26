import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { formatKg, formatMonth, formatNumber } from "@/shared/lib/format";

interface Point {
  month: string; // YYYY-MM
  total_kg: number;
}

const W = 640;
const H = 240;
const PAD = { top: 16, right: 8, bottom: 28, left: 44 };
const MAX_MONTHS = 12;

/** Rellena los meses sin cosecha para que el eje de tiempo sea continuo. */
function continuous(points: Point[]): Point[] {
  if (points.length === 0) return [];
  const byMonth = new Map(points.map((p) => [p.month, p.total_kg]));
  const [fy, fm] = points[0].month.split("-").map(Number);
  const [ly, lm] = points[points.length - 1].month.split("-").map(Number);
  const out: Point[] = [];
  for (let y = fy, m = fm; y < ly || (y === ly && m <= lm); m === 12 ? (y++, (m = 1)) : m++) {
    const key = `${y}-${String(m).padStart(2, "0")}`;
    out.push({ month: key, total_kg: byMonth.get(key) ?? 0 });
  }
  return out.slice(-MAX_MONTHS);
}

function niceMax(value: number): number {
  if (value <= 0) return 1;
  const pow = 10 ** Math.floor(Math.log10(value));
  const n = value / pow;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow;
}

/** Barra con extremo superior redondeado (4 px) y base recta anclada al eje. */
function barPath(x: number, y: number, w: number, h: number, r = 4): string {
  const rr = Math.min(r, w / 2, h);
  return `M${x},${y + h} V${y + rr} Q${x},${y} ${x + rr},${y} H${x + w - rr} Q${x + w},${y} ${x + w},${y + rr} V${y + h} Z`;
}

export function MonthChart({ data }: { data: Point[] }) {
  const { t } = useTranslation();
  const [active, setActive] = useState<number | null>(null);
  const points = useMemo(() => continuous(data), [data]);

  const max = niceMax(Math.max(...points.map((p) => p.total_kg), 0));
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const slot = innerW / Math.max(points.length, 1);
  const barW = Math.min(36, slot - 2 * 2); // 2 px de aire entre barras a cada lado
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH;
  const peak = points.reduce((best, p, i) => (p.total_kg > points[best].total_kg ? i : best), 0);
  const ticks = [0, max / 2, max];

  if (points.length === 0) return null;

  return (
    <figure className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label={t("inventory.chart.label")}
        onMouseLeave={() => setActive(null)}
      >
        {/* Cuadrícula recesiva: líneas finas y etiquetas en tinta suave */}
        {ticks.map((tick) => (
          <g key={tick}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={y(tick)}
              y2={y(tick)}
              stroke="var(--hairline)"
              strokeWidth={1}
            />
            <text x={PAD.left - 8} y={y(tick) + 4} textAnchor="end" fontSize={11} fill="var(--dusty)">
              {formatNumber(tick, 0)}
            </text>
          </g>
        ))}

        {points.map((p, i) => {
          const cx = PAD.left + slot * i + slot / 2;
          const h = Math.max((p.total_kg / max) * innerH, p.total_kg > 0 ? 2 : 0);
          const isActive = active === i;
          return (
            <g
              key={p.month}
              tabIndex={0}
              role="img"
              aria-label={`${formatMonth(p.month, "long")}: ${formatKg(p.total_kg)}`}
              onMouseEnter={() => setActive(i)}
              onFocus={() => setActive(i)}
              onBlur={() => setActive(null)}
              className="outline-none"
            >
              {/* Zona de impacto más grande que la barra */}
              <rect x={cx - slot / 2} y={PAD.top} width={slot} height={innerH + PAD.bottom} fill="transparent" />
              {h > 0 && (
                <path
                  d={barPath(cx - barW / 2, y(p.total_kg), barW, h)}
                  fill="var(--purple)"
                  opacity={active === null || isActive ? 1 : 0.45}
                />
              )}
              <text x={cx} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--dusty)">
                {formatMonth(p.month)}
              </text>
              {/* Etiqueta directa solo en el máximo: nunca un número en cada barra */}
              {i === peak && p.total_kg > 0 && active === null && (
                <text x={cx} y={y(p.total_kg) - 6} textAnchor="middle" fontSize={12} fontWeight={600} fill="var(--midnight)">
                  {formatNumber(p.total_kg, 0)}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {active !== null && (
        <div
          className="pointer-events-none absolute -translate-x-1/2 -translate-y-full rounded-control bg-midnight px-3 py-2 text-xs text-cream shadow-lg"
          style={{
            left: `${((PAD.left + slot * active + slot / 2) / W) * 100}%`,
            top: `${(y(points[active].total_kg) / H) * 100}%`,
          }}
        >
          <p className="text-cream/70">{formatMonth(points[active].month, "long")}</p>
          <p className="font-semibold">{formatKg(points[active].total_kg)}</p>
        </div>
      )}

      {/* Equivalente tabular para lectores de pantalla */}
      <table className="sr-only">
        <caption>{t("inventory.chart.label")}</caption>
        <tbody>
          {points.map((p) => (
            <tr key={p.month}>
              <th scope="row">{formatMonth(p.month, "long")}</th>
              <td>{formatKg(p.total_kg)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
