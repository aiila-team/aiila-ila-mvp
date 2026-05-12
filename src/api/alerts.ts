import client from './client';
import { Alert, AlertStatus, PaginatedResponse } from '../types';

export const alertsApi = {
  getAll: async (params?: {
    page?: number;
    page_size?: number;
    severity?: string;
    status?: string;
  }): Promise<PaginatedResponse<Alert>> => {
    const { data } = await client.get('/alerts', { params });
    return data;
  },

  getById: async (id: string): Promise<Alert> => {
    const { data } = await client.get(`/alerts/${id}`);
    return data;
  },

  updateStatus: async (id: string, status: AlertStatus): Promise<Alert> => {
    const { data } = await client.patch(`/alerts/${id}`, { status });
    return data;
  },

  dismiss: async (id: string): Promise<void> => {
    await client.delete(`/alerts/${id}`);
  },
};
