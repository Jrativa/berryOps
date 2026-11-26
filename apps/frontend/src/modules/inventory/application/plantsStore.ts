import { create } from 'zustand';
import {
  inventoryAPI,
  PLANT_STATUSES,
  type ObservationInput,
  type PlantBrief,
  type PlantStatus,
} from '../infrastructure/api';

export interface PlantStats {
  rows: number;
  columns: number;
  total: number;
  counts: Record<PlantStatus, number>;
  /** % de plantas muertas sobre el total */
  mortality: number;
}

/** Las cifras se derivan de la lista cargada: siempre coinciden con lo que muestra el mapa. */
export function computeStats(plants: PlantBrief[]): PlantStats {
  const counts = Object.fromEntries(PLANT_STATUSES.map((s) => [s, 0])) as Record<PlantStatus, number>;
  let rows = 0;
  let columns = 0;
  for (const p of plants) {
    counts[p.status] += 1;
    if (p.row > rows) rows = p.row;
    if (p.col > columns) columns = p.col;
  }
  const total = plants.length;
  return { rows, columns, total, counts, mortality: total ? (counts.dead / total) * 100 : 0 };
}

interface PlantsState {
  plotId: string | null;
  plants: PlantBrief[];
  loading: boolean;
  error: boolean;

  /** Modo selección: tocar celdas las agrupa para registrar un estado a todas a la vez */
  selecting: boolean;
  selected: Set<string>;
  /** Estado resaltado desde la leyenda (el resto del mapa se atenúa) */
  filter: PlantStatus | null;

  load: (plotId: string) => Promise<void>;
  generate: (plotId: string, rows: number, columns: number) => Promise<void>;
  observeOne: (plantId: string, data: ObservationInput) => Promise<void>;
  observeSelected: (plotId: string, data: ObservationInput) => Promise<number>;

  setSelecting: (on: boolean) => void;
  toggle: (ids: string[], force?: boolean) => void;
  clearSelection: () => void;
  setFilter: (status: PlantStatus | null) => void;
}

export const usePlantsStore = create<PlantsState>((set, get) => ({
  plotId: null,
  plants: [],
  loading: false,
  error: false,
  selecting: false,
  selected: new Set(),
  filter: null,

  load: async (plotId) => {
    set({ plotId, plants: [], loading: true, error: false, selected: new Set(), selecting: false, filter: null });
    try {
      const plants = await inventoryAPI.listPlants(plotId);
      if (get().plotId === plotId) set({ plants, loading: false });
    } catch {
      if (get().plotId === plotId) set({ loading: false, error: true });
    }
  },

  generate: async (plotId, rows, columns) => {
    await inventoryAPI.generateGrid(plotId, rows, columns);
    await get().load(plotId);
  },

  // Optimista: el mapa cambia al instante y se revierte si el servidor rechaza el cambio.
  observeOne: async (plantId, data) => {
    const previous = get().plants;
    set({ plants: previous.map((p) => (p.id === plantId ? { ...p, status: data.status } : p)) });
    try {
      await inventoryAPI.observePlant(plantId, data);
    } catch (err) {
      set({ plants: previous });
      throw err;
    }
  },

  observeSelected: async (plotId, data) => {
    const ids = [...get().selected];
    const previous = get().plants;
    const target = new Set(ids);
    set({ plants: previous.map((p) => (target.has(p.id) ? { ...p, status: data.status } : p)) });
    try {
      const result = await inventoryAPI.observePlants(plotId, ids, data);
      set({ selected: new Set(), selecting: false });
      return result.updated;
    } catch (err) {
      set({ plants: previous });
      throw err;
    }
  },

  setSelecting: (selecting) => set({ selecting, selected: selecting ? get().selected : new Set() }),

  toggle: (ids, force) =>
    set((s) => {
      const next = new Set(s.selected);
      // Sin `force`, si todas ya estaban seleccionadas se deseleccionan; si no, se seleccionan todas
      const add = force ?? !ids.every((id) => next.has(id));
      ids.forEach((id) => (add ? next.add(id) : next.delete(id)));
      return { selected: next, selecting: true };
    }),

  clearSelection: () => set({ selected: new Set() }),
  setFilter: (filter) => set({ filter }),
}));
