import { api } from './api'
import type { Dataset, DatasetPreview, PaginatedDatasets } from '@/types'

export const datasetService = {
  async list(params?: { page?: number; limit?: number; search?: string }): Promise<PaginatedDatasets> {
    const { data } = await api.get<PaginatedDatasets>('/datasets', { params })
    return data
  },

  async get(id: number): Promise<Dataset> {
    const { data } = await api.get<Dataset>(`/datasets/${id}`)
    return data
  },

  async preview(id: number, rows = 50, offset = 0, table?: string): Promise<DatasetPreview> {
    const { data } = await api.get<DatasetPreview>(`/datasets/${id}/preview`, {
      params: { rows, offset, table },
    })
    return data
  },

  async upload(
    file: File,
    meta: { name: string; description?: string; is_public?: boolean }
  ): Promise<Dataset> {
    const form = new FormData()
    form.append('file', file)
    form.append('name', meta.name)
    if (meta.description) form.append('description', meta.description)
    form.append('is_public', String(meta.is_public ?? false))

    const { data } = await api.post<Dataset>('/files/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async update(id: number, payload: { name?: string; description?: string; is_public?: boolean }): Promise<Dataset> {
    const { data } = await api.put<Dataset>(`/datasets/${id}`, payload)
    return data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/datasets/${id}`)
  },
}
