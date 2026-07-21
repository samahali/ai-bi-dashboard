import { api } from './api'
import type { Visualization } from '@/types'

export const visualizationService = {
  async create(payload: {
    query_id: number
    chart_type: string
    title?: string
    x_axis?: string
    y_axis?: string
    config?: Record<string, unknown>
  }): Promise<Visualization> {
    const { data } = await api.post<Visualization>('/visualizations', payload)
    return data
  },

  async update(
    id: number,
    payload: { title?: string; config?: Record<string, unknown>; is_saved?: boolean }
  ): Promise<Visualization> {
    const { data } = await api.put<Visualization>(`/visualizations/${id}`, payload)
    return data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/visualizations/${id}`)
  },
}
