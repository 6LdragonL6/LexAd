import client from './client'
import type { Material } from '@/types'

export const materialsApi = {
  submit: (data: {
    name: string; industry: string; platforms: string[]; material_type: string
    raw_text: string; priority: string; deadline?: string | null
  }) => client.post<Material>('/materials/submit', data),
  list: () => client.get<Material[]>('/materials/list'),
  get: (id: string) => client.get<Material>(`/materials/${id}`),
  update: (id: string, data: Record<string, any>) => client.put<Material>(`/materials/${id}`, data),
  versions: (id: string) => client.get<{ versions: any[] }>(`/materials/${id}/versions`),
}
