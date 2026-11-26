import { api } from '@/core/api/axios.instance';
import { downloadFile } from '@/shared/lib/download';

export type Grade = 'premium' | 'standard' | 'processing';
export const GRADES: Grade[] = ['premium', 'standard', 'processing'];

export interface Plot {
  id: string;
  owner_id: string;
  name: string;
  variety: string;
  area_ha: number;
  planting_date: string | null;
  plant_count: number | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PlotInput {
  name: string;
  variety: string;
  area_ha: number;
  planting_date?: string | null;
  plant_count?: number | null;
  notes?: string | null;
}

export interface Harvest {
  id: string;
  plot_id: string;
  harvested_on: string; // YYYY-MM-DD
  quantity_kg: number;
  grade: Grade;
  notes: string | null;
  created_at: string;
}

export interface HarvestInput {
  harvested_on: string;
  quantity_kg: number;
  grade: Grade;
  notes?: string | null;
}

export type CostCategory = 'fertilizer' | 'pesticide' | 'irrigation' | 'labor' | 'other';
export const COST_CATEGORIES: CostCategory[] = ['fertilizer', 'pesticide', 'irrigation', 'labor', 'other'];

export interface Cost {
  id: string;
  plot_id: string;
  incurred_on: string; // YYYY-MM-DD
  category: CostCategory;
  amount: number;
  notes: string | null;
  created_at: string;
}

export interface CostInput {
  incurred_on: string;
  category: CostCategory;
  amount: number;
  notes?: string | null;
}

export interface Summary {
  total_kg: number;
  harvest_count: number;
  yield_kg_per_ha: number;
  last_harvest_on: string | null;
  by_plot: {
    plot_id: string;
    plot_name: string;
    total_kg: number;
    yield_kg_per_ha: number;
    total_cost: number;
    cost_per_kg: number | null;
  }[];
  by_month: { month: string; total_kg: number }[];
  by_grade: { grade: Grade; total_kg: number }[];
  total_cost: number;
  cost_per_kg: number | null;
  by_category: { category: CostCategory; total: number }[];
}

export type PlantStatus = 'healthy' | 'attention' | 'sick' | 'dead';
export const PLANT_STATUSES: PlantStatus[] = ['healthy', 'attention', 'sick', 'dead'];

/** Versión ligera de una planta: lo justo para dibujar el mapa del lote. */
export interface PlantBrief {
  id: string;
  row: number;
  col: number;
  status: PlantStatus;
}

export interface Observation {
  id: string;
  plant_id: string;
  status: PlantStatus;
  notes: string | null;
  observed_on: string; // YYYY-MM-DD
  recorded_by: string;
  created_at: string;
}

export interface PlantDetail extends PlantBrief {
  plot_id: string;
  created_at: string;
  observations: Observation[];
}

export interface ObservationInput {
  status: PlantStatus;
  notes?: string | null;
  observed_on?: string;
}

export const inventoryAPI = {
  listPlots: async (): Promise<Plot[]> => (await api.get('/inventory/plots')).data,
  getPlot: async (id: string): Promise<Plot> => (await api.get(`/inventory/plots/${id}`)).data,
  createPlot: async (data: PlotInput): Promise<Plot> => (await api.post('/inventory/plots', data)).data,
  updatePlot: async (id: string, data: Partial<PlotInput>): Promise<Plot> =>
    (await api.patch(`/inventory/plots/${id}`, data)).data,
  deletePlot: async (id: string) => {
    await api.delete(`/inventory/plots/${id}`);
  },

  listHarvests: async (plotId: string): Promise<Harvest[]> =>
    (await api.get(`/inventory/plots/${plotId}/harvests`)).data,
  addHarvest: async (plotId: string, data: HarvestInput): Promise<Harvest> =>
    (await api.post(`/inventory/plots/${plotId}/harvests`, data)).data,
  deleteHarvest: async (id: string) => {
    await api.delete(`/inventory/harvests/${id}`);
  },

  listCosts: async (plotId: string): Promise<Cost[]> =>
    (await api.get(`/inventory/plots/${plotId}/costs`)).data,
  addCost: async (plotId: string, data: CostInput): Promise<Cost> =>
    (await api.post(`/inventory/plots/${plotId}/costs`, data)).data,
  deleteCost: async (id: string) => {
    await api.delete(`/inventory/costs/${id}`);
  },

  /** Descarga un CSV: cosechas o costos (de un lote o de todos) y las plantas de un lote. */
  exportCsv: (kind: 'harvests' | 'costs', opts: { from?: string; plotId?: string } = {}) =>
    downloadFile(`/inventory/export/${kind}`, { from: opts.from, plot: opts.plotId }),
  exportPlants: (plotId: string) => downloadFile(`/inventory/plots/${plotId}/plants/export`),

  listPlants: async (plotId: string): Promise<PlantBrief[]> =>
    (await api.get(`/inventory/plots/${plotId}/plants`)).data,
  generateGrid: async (plotId: string, rows: number, columns: number): Promise<{ created: number; total: number }> =>
    (await api.post(`/inventory/plots/${plotId}/plants/generate`, { rows, columns })).data,
  getPlant: async (id: string): Promise<PlantDetail> => (await api.get(`/inventory/plants/${id}`)).data,
  observePlant: async (id: string, data: ObservationInput): Promise<Observation> =>
    (await api.post(`/inventory/plants/${id}/observations`, data)).data,
  observePlants: async (plotId: string, plantIds: string[], data: ObservationInput): Promise<{ updated: number }> =>
    (await api.post(`/inventory/plots/${plotId}/plants/observations`, { plant_ids: plantIds, ...data })).data,

  summary: async (from?: string): Promise<Summary> =>
    (await api.get('/inventory/summary', { params: from ? { from } : undefined })).data,
};
