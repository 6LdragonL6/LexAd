import client from './client'
import type { KnowledgeCatalog, KnowledgeContent, PlatformOption } from '@/types'

export const knowledgeApi = {
  platforms: () =>
    client.get<{ items: PlatformOption[]; total: number }>('/knowledge/platforms'),
  catalog: (layer: string) =>
    client.get<KnowledgeCatalog>(`/knowledge/catalog/${layer}`),
  content: (item_id: string) =>
    client.get<KnowledgeContent>('/knowledge/content', { params: { item_id } }),
}
