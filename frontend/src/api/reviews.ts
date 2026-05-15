import client from './client'
import type { Review, ReviewQueueItem } from '@/types'

export const reviewsApi = {
  aiReview: (material_id: string) =>
    client.post<Review>('/reviews/ai-review', { material_id }),
  get: (id: string) => client.get<Review>(`/reviews/${id}`),
  byMaterial: (material_id: string) => client.get<Review>(`/reviews/by-material/${material_id}`),
  submitDecision: (id: string, data: { decision: string; notes: string; return_reasons: string }) =>
    client.post<Review>(`/reviews/${id}/decision`, data),
  queue: () => client.get<ReviewQueueItem[]>('/reviews/queue'),
}
