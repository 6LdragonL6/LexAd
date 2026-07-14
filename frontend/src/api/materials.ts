import client from './client'
import type { Material, MaterialVersion, PreviewTextResponse, Review } from '@/types'

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
  resubmit: (id: string, data: Record<string, any>) =>
    client.post<Review>(`/materials/${id}/resubmit`, data),
  versions: (id: string) =>
    client.get<{ versions: MaterialVersion[] }>(`/materials/${id}/versions`),
  archive: (id: string) =>
    client.post<Material>(`/materials/${id}/archive`),
  delete: (id: string) =>
    client.delete(`/materials/${id}`),
}
