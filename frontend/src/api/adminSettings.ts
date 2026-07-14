import client from './client'
import type { AiConfigStatus, RecycleBinEntry, RecycleBinList, RecycleTargetType } from '@/types'

export const adminSettingsApi = {
  getAiConfig: () => client.get<AiConfigStatus>('/admin/settings/ai'),
  saveAiConfig: (apiKey: string) => client.put<AiConfigStatus>('/admin/settings/ai', { api_key: apiKey }),
  testAiConfig: (apiKey?: string) => client.post<{ ok: boolean; message: string; tested_at: string }>(
    '/admin/settings/ai/test',
    apiKey ? { api_key: apiKey } : undefined,
  ),
  clearAiConfig: () => client.delete('/admin/settings/ai'),
  listRecycleBin: (targetType?: RecycleTargetType, page = 1, pageSize = 20) =>
    client.get<RecycleBinList>('/admin/settings/recycle-bin', {
      params: { target_type: targetType || undefined, page, page_size: pageSize },
    }),
  moveToRecycleBin: (targetType: RecycleTargetType, targetId: string) =>
    client.post<RecycleBinEntry>('/admin/settings/recycle-bin', { target_type: targetType, target_id: targetId }),
  restore: (entryId: string) => client.post(`/admin/settings/recycle-bin/${entryId}/restore`),
  purge: (entryId: string) => client.delete(`/admin/settings/recycle-bin/${entryId}`),
}
