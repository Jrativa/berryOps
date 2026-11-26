import { Bug, Eye, Leaf, Skull, type LucideIcon } from "lucide-react";

import type { PlantStatus } from "../infrastructure/api";

/**
 * "Sana" es el estado normal, así que su color retrocede (un tinte suave de la paleta) y las
 * excepciones destacan. Los colores no son la única señal: cada estado tiene icono y nombre en la
 * leyenda, en la lista de plantas con novedad y en el texto accesible de cada celda.
 */
export const STATUS_META: Record<PlantStatus, { icon: LucideIcon; color: string }> = {
  healthy: { icon: Leaf, color: "var(--st-healthy)" },
  attention: { icon: Eye, color: "var(--st-attention)" },
  sick: { icon: Bug, color: "var(--st-sick)" },
  dead: { icon: Skull, color: "var(--st-dead)" },
};

/** Orden de gravedad para listar primero lo más urgente. */
export const SEVERITY: Record<PlantStatus, number> = { dead: 0, sick: 1, attention: 2, healthy: 3 };
