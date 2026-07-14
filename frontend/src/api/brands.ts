import client from './client'
import type { Brand, BrandProfile } from '@/types'

export const brandsApi = {
  search: (query = '') =>
    client.get<Brand[]>('/brands', { params: { search: query } }),

  create: (data: { name: string; industry?: string; industries?: string[] }) =>
    client.post<{ brand: Brand; created: boolean }>('/brands', data),

  profile: (brandId: string) =>
    client.get<BrandProfile>(`/brands/${brandId}/profile`),

  update: (brandId: string, data: Record<string, any>) =>
    client.patch<Brand>(`/brands/${brandId}`, data),

  setIndustries: (brandId: string, industries: string[]) =>
    client.put<Brand>(`/brands/${brandId}/industries`, { industries }),

  reviewIndustrySuggestion: (brandId: string, suggestionId: string, action: 'accept' | 'ignore' | 'restore') =>
    client.post<BrandProfile>(`/brands/${brandId}/industry-suggestions/${suggestionId}`, { action }),
}
