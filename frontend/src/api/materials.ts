import client from './client'
import type { Material, PreviewTextResponse } from '@/types'

export const materialsApi = {
  submit: (formData: FormData) =>
    client.post<Material>('/materials/submit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  previewText: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post<PreviewTextResponse>('/materials/preview-text', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: () => client.get<Material[]>('/materials/list'),
  get: (id: string) => client.get<Material>(`/materials/${id}`),
  update: (id: string, data: Record<string, any>) =>
    client.put<Material>(`/materials/${id}`, data),
  versions: (id: string) =>
    client.get<{ versions: any[] }>(`/materials/${id}/versions`),
}
