import apiClient from './client'
import type { CaseItem, ReviewResult, TemplateItem } from '@/types'

export function submitReview(rawText: string, imageFile?: File): Promise<ReviewResult> {
  const formData = new FormData()
  formData.append('raw_text', rawText)
  if (imageFile) {
    formData.append('image_file', imageFile)
  }
  return apiClient
    .post('/review/submit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((res) => res.data)
}

export function getReviewResult(requestId: string): Promise<ReviewResult> {
  return apiClient.get(`/review/result/${requestId}`).then((res) => res.data)
}

export function listCases(): Promise<{ items: CaseItem[]; total: number }> {
  return apiClient.get('/review/cases').then((res) => res.data)
}

export function listTemplates(): Promise<{ items: TemplateItem[]; total: number }> {
  return apiClient.get('/review/templates').then((res) => res.data)
}
