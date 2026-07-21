import { api } from './api'
import type { Query } from '@/types'

export const queryService = {
  async create(payload: {
    dataset_id: number
    question: string
    ai_model?: 'granite' | 'openai'
  }): Promise<{ id: number; status: string; message: string }> {
    const { data } = await api.post('/queries', payload)
    return data
  },

  async get(id: number): Promise<Query> {
    const { data } = await api.get<Query>(`/queries/${id}`)
    return data
  },

  async list(params?: { dataset_id?: number; page?: number; limit?: number }): Promise<Query[]> {
    const { data } = await api.get<Query[]>('/queries', { params })
    return data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/queries/${id}`)
  },

  /** Poll until query reaches terminal state (success or error) */
  async pollUntilDone(id: number, intervalMs = 1500, maxAttempts = 60): Promise<Query> {
    for (let i = 0; i < maxAttempts; i++) {
      const query = await queryService.get(id)
      if (query.status === 'success' || query.status === 'error') return query
      await new Promise((r) => setTimeout(r, intervalMs))
    }
    throw new Error('Query timed out.')
  },
}
