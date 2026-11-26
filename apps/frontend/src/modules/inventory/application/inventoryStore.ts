import { create } from 'zustand';
import { isAxiosError } from 'axios';
import i18n from '@/i18n/config';
import {
  inventoryAPI,
  type Cost,
  type CostInput,
  type Harvest,
  type HarvestInput,
  type Plot,
  type PlotInput,
  type Summary,
} from '../infrastructure/api';

export type Period = '30d' | '12m' | 'all';

export function periodStart(period: Period): string | undefined {
  if (period === 'all') return undefined;
  const d = new Date();
  if (period === '30d') d.setDate(d.getDate() - 30);
  else d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().slice(0, 10);
}

/** Mensaje legible: el backend manda el detalle de reglas de negocio (400), el resto es genérico. */
export function errorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (err.response?.status === 400 && typeof detail === 'string') return detail;
    if (err.response?.status === 404) return i18n.t('inventory.error.notFound');
  }
  return i18n.t('inventory.error.generic');
}

interface InventoryState {
  plots: Plot[];
  summary: Summary | null;
  period: Period;
  loading: boolean;
  error: string | null;

  // detalle de un lote
  plot: Plot | null;
  harvests: Harvest[];
  costs: Cost[];
  detailLoading: boolean;

  setPeriod: (p: Period) => void;
  loadOverview: () => Promise<void>;
  createPlot: (data: PlotInput) => Promise<Plot>;
  loadPlot: (id: string) => Promise<void>;
  updatePlot: (id: string, data: Partial<PlotInput>) => Promise<void>;
  deletePlot: (id: string) => Promise<void>;
  addHarvest: (plotId: string, data: HarvestInput) => Promise<void>;
  deleteHarvest: (id: string) => Promise<void>;
  addCost: (plotId: string, data: CostInput) => Promise<void>;
  deleteCost: (id: string) => Promise<void>;
}

export const useInventoryStore = create<InventoryState>((set, get) => ({
  plots: [],
  summary: null,
  period: '12m',
  loading: false,
  error: null,
  plot: null,
  harvests: [],
  costs: [],
  detailLoading: false,

  setPeriod: (period) => {
    set({ period });
    void get().loadOverview();
  },

  loadOverview: async () => {
    set({ loading: true, error: null });
    try {
      const [plots, summary] = await Promise.all([
        inventoryAPI.listPlots(),
        inventoryAPI.summary(periodStart(get().period)),
      ]);
      set({ plots, summary, loading: false });
    } catch (err) {
      set({ error: errorMessage(err), loading: false });
    }
  },

  createPlot: async (data) => {
    const plot = await inventoryAPI.createPlot(data);
    set((s) => ({ plots: [...s.plots, plot].sort((a, b) => a.name.localeCompare(b.name)) }));
    return plot;
  },

  loadPlot: async (id) => {
    set({ detailLoading: true, error: null, plot: null, harvests: [], costs: [] });
    try {
      const [plot, harvests, costs] = await Promise.all([
        inventoryAPI.getPlot(id),
        inventoryAPI.listHarvests(id),
        inventoryAPI.listCosts(id),
      ]);
      set({ plot, harvests, costs, detailLoading: false });
    } catch (err) {
      set({ error: errorMessage(err), detailLoading: false });
    }
  },

  updatePlot: async (id, data) => {
    const plot = await inventoryAPI.updatePlot(id, data);
    set((s) => ({ plot, plots: s.plots.map((p) => (p.id === id ? plot : p)) }));
  },

  deletePlot: async (id) => {
    await inventoryAPI.deletePlot(id);
    set((s) => ({ plots: s.plots.filter((p) => p.id !== id) }));
  },

  // Actualización optimista: la cosecha aparece al instante y se reemplaza por la del servidor.
  addHarvest: async (plotId, data) => {
    const temp: Harvest = {
      id: `temp-${Date.now()}`,
      plot_id: plotId,
      harvested_on: data.harvested_on,
      quantity_kg: data.quantity_kg,
      grade: data.grade,
      notes: data.notes ?? null,
      created_at: new Date().toISOString(),
    };
    const sortDesc = (list: Harvest[]) =>
      [...list].sort((a, b) => b.harvested_on.localeCompare(a.harvested_on));
    set((s) => ({ harvests: sortDesc([temp, ...s.harvests]) }));
    try {
      const saved = await inventoryAPI.addHarvest(plotId, data);
      set((s) => ({ harvests: sortDesc(s.harvests.map((h) => (h.id === temp.id ? saved : h))) }));
    } catch (err) {
      set((s) => ({ harvests: s.harvests.filter((h) => h.id !== temp.id) }));
      throw err;
    }
  },

  deleteHarvest: async (id) => {
    const previous = get().harvests;
    set({ harvests: previous.filter((h) => h.id !== id) });
    try {
      await inventoryAPI.deleteHarvest(id);
    } catch (err) {
      set({ harvests: previous });
      throw err;
    }
  },

  // Mismo patrón optimista que las cosechas
  addCost: async (plotId, data) => {
    const temp: Cost = {
      id: `temp-${Date.now()}`,
      plot_id: plotId,
      incurred_on: data.incurred_on,
      category: data.category,
      amount: data.amount,
      notes: data.notes ?? null,
      created_at: new Date().toISOString(),
    };
    const sortDesc = (list: Cost[]) => [...list].sort((a, b) => b.incurred_on.localeCompare(a.incurred_on));
    set((s) => ({ costs: sortDesc([temp, ...s.costs]) }));
    try {
      const saved = await inventoryAPI.addCost(plotId, data);
      set((s) => ({ costs: sortDesc(s.costs.map((c) => (c.id === temp.id ? saved : c))) }));
    } catch (err) {
      set((s) => ({ costs: s.costs.filter((c) => c.id !== temp.id) }));
      throw err;
    }
  },

  deleteCost: async (id) => {
    const previous = get().costs;
    set({ costs: previous.filter((c) => c.id !== id) });
    try {
      await inventoryAPI.deleteCost(id);
    } catch (err) {
      set({ costs: previous });
      throw err;
    }
  },
}));
