import client from './client'
import type { KnowledgeCatalog, KnowledgeContent } from '@/types'

export const knowledgeApi = {
  catalog: (layer: string) =>
    client.get<KnowledgeCatalog>(`/knowledge/catalog/${layer}`),
  content: (item_id: string) =>
    client.get<KnowledgeContent>('/knowledge/content', { params: { item_id } }),
}
