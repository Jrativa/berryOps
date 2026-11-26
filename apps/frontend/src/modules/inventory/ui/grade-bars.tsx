import { useTranslation } from "react-i18next";

import type { Summary } from "../infrastructure/api";
import { formatKg } from "@/shared/lib/format";

/**
 * Reparto por calidad. Tres categorías ordenadas por volumen y con etiqueta directa:
 * la identidad la da el texto, no el color, así que un único tono basta.
 */
export function GradeBars({ data }: { data: Summary["by_grade"] }) {
  const { t } = useTranslation();
  const total = data.reduce((sum, g) => sum + g.total_kg, 0);
  if (total === 0) return null;

  return (
    <ul className="flex flex-col gap-4">
      {data.map((g) => (
        <li key={g.grade}>
          <div className="mb-1.5 flex items-baseline justify-between text-sm">
            <span className="font-medium">{t(`inventory.grade.${g.grade}`)}</span>
            <span className="text-dusty">
              {formatKg(g.total_kg)} · {Math.round((g.total_kg / total) * 100)}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-midnight/[0.06]">
            <div
              className="h-full rounded-full bg-purple"
              style={{ width: `${(g.total_kg / total) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
