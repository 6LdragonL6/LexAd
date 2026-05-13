// 审查相关 API 调用函数
import apiClient from './client'
import type { CaseItem, ReviewResult, TemplateItem } from '@/types'

/** 提交广告文案进行合规审查，支持附带图片文件 */
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

/** 根据请求 ID 获取审查结果 */
export function getReviewResult(requestId: string): Promise<ReviewResult> {
  return apiClient.get(`/review/result/${requestId}`).then((res) => res.data)
}

/** 获取案例库列表 */
export function listCases(): Promise<{ items: CaseItem[]; total: number }> {
  return apiClient.get('/review/cases').then((res) => res.data)
}

/** 获取改写模板库列表 */
export function listTemplates(): Promise<{ items: TemplateItem[]; total: number }> {
  return apiClient.get('/review/templates').then((res) => res.data)
}
