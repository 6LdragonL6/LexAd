// 审查状态管理 —— Pinia Store，管理审查提交、结果获取和加载/错误状态
import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ReviewResult } from '@/types'
import { getReviewResult, submitReview } from '@/api/review'

export const useReviewStore = defineStore('review', () => {
  const currentResult = ref<ReviewResult | null>(null)  // 当前审查结果
  const loading = ref(false)                             // 加载状态
  const error = ref<string | null>(null)                 // 错误信息

  /** 提交审查：将广告文本和可选图片发送到后端，存储结果 */
  async function submit(rawText: string, imageFile?: File) {
    loading.value = true
    error.value = null
    try {
      currentResult.value = await submitReview(rawText, imageFile)
    } catch (e: any) {
      error.value = e.response?.data?.detail || '审查提交失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /** 根据请求 ID 获取已有的审查结果 */
  async function fetchResult(requestId: string) {
    loading.value = true
    error.value = null
    try {
      currentResult.value = await getReviewResult(requestId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取结果失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /** 清空当前存储的审查结果和错误 */
  function clearResult() {
    currentResult.value = null
    error.value = null
  }

  return { currentResult, loading, error, submit, fetchResult, clearResult }
})
