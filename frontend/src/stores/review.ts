import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ReviewResult } from '@/types'
import { getReviewResult, submitReview } from '@/api/review'

export const useReviewStore = defineStore('review', () => {
  const currentResult = ref<ReviewResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

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

  function clearResult() {
    currentResult.value = null
    error.value = null
  }

  return { currentResult, loading, error, submit, fetchResult, clearResult }
})
