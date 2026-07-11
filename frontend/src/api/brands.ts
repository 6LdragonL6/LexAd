import client from './client'
import type { Brand, BrandProfile } from '@/types'

export const brandsApi = {
  search: (query = '') =>
    client.get<Brand[]>('/brands', { params: { search: query } }),

  create: (data: { name: string; industry?: string }) =>
    client.post<{ brand: Brand; created: boolean }>('/brands', data),

  profile: (brandId: string) =>
    client.get<BrandProfile>(`/brands/${brandId}/profile`),

  update: (brandId: string, data: Record<string, any>) =>
    client.patch<Brand>(`/brands/${brandId}`, data),
}
