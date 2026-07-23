import type { Report } from '@/types'

import { api } from './api'

export const reportService = {
  async create(payload: {
    dataset_id: number
    title: string
    description?: string
    query_ids: number[]
    visualization_ids?: number[]
    include_insights?: boolean
  }): Promise<{ id: number; status: string; message: string }> {
    const { data } = await api.post('/reports', payload)
    return data
  },

  async get(id: number): Promise<Report> {
    const { data } = await api.get<Report>(`/reports/${id}`)
    return data
  },

  async list(): Promise<Report[]> {
    const { data } = await api.get<Report[]>('/reports')
    return data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/reports/${id}`)
  },

  /** Fetch the PDF through the authenticated axios instance and trigger a browser download. */
  async download(id: number, filename = `report_${id}.pdf`): Promise<void> {
    const { data } = await api.get(`/reports/${id}/download`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}
