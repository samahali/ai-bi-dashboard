import type { Insight } from '@/types'

import { api } from './api'

export const insightService = {
  async list(
    datasetId: number,
    params?: { insight_type?: string; severity?: string; limit?: number }
  ): Promise<Insight[]> {
    const { data } = await api.get<Insight[]>(`/insights/${datasetId}`, { params })
    return data
  },

  async dismiss(id: number): Promise<Insight> {
    const { data } = await api.post<Insight>(`/insights/${id}/dismiss`)
    return data
  },
}
