<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { Material, ReviewQueueItem } from '@/types'

const store = useUserStore()
const router = useRouter()
const materials = ref<Material[]>([])
const queue = ref<ReviewQueueItem[]>([])
const loading = ref(true)
const navigationError = ref('')
const archiving = ref<Record<string, boolean>>({})

onMounted(async () => {
  try {
    const [mRes, qRes] = await Promise.all([materialsApi.list(), reviewsApi.queue()])
    materials.value = mRes.data
    queue.value = qRes.data
  } finally {
    loading.value = false
  }
})

const pendingCount = computed(() => materials.value.filter(m => !['approved', 'conditional_approved', 'draft', 'archived'].includes(m.status)).length)
const returnedCount = computed(() => materials.value.filter(m => m.status === 'returned').length)
const queueCount = computed(() => queue.value.length)

function statusVariant(status: string): 'success' | 'warning' | 'danger' | 'info' | 'gray' {
  if (status === 'approved' || status === 'conditional_approved') return 'success'
  if (status === 'returned') return 'danger'
  if (status === 'pending_legal' || status === 'ai_reviewing') return 'warning'
  return 'gray'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    approved: '已通过', conditional_approved: '有条件通过', pending_legal: '待法务审核',
    returned: '已退回', draft: '草稿', ai_reviewing: '审查中', archived: '已归档',
  }
  return map[status] || status
}

async function openMaterial(material: Material) {
  navigationError.value = ''
  try {
    const response = await reviewsApi.byMaterial(material.id)
    router.push(`/result/${response.data.id}`)
  } catch (error: any) {
    navigationError.value = error.response?.status === 404
      ? '该物料还没有审查记录'
      : (error.response?.data?.detail || '无法打开审查记录')
  }
}

function getQueueInfo(materialId: string): ReviewQueueItem | undefined {
  return queue.value.find(q => q.material_id === materialId)
}

async function handleArchive(material: Material) {
  if (!confirm('确认归档该物料？归档后不再参与待办。')) return
  archiving.value[material.id] = true
  try {
    await materialsApi.archive(material.id)
    materials.value = materials.value.filter(m => m.id !== material.id)
  } catch (e: any) {
    alert(e.response?.data?.detail || '归档失败')
  } finally {
    archiving.value[material.id] = false
  }
}
</script>

<template>
  <DefaultLayout>
    <div class="page-container max-w-4xl">
      <!-- Welcome Banner -->
      <div class="welcome-banner">
        <h2 class="text-white text-xl font-bold mb-1">
          你好，{{ store.user?.display_name }}
        </h2>
        <p class="text-white/80 text-sm">智能合规 · 广告无忧 — 让每一则广告都经得起法律检验</p>
      </div>

      <!-- Stat Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <div class="card text-center">
          <div class="stat-icon bg-sky-50 text-sky-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8v4l3 3M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <p class="text-3xl font-bold text-sky-600">{{ pendingCount }}</p>
          <p class="text-sm text-gray-500 mt-1">待处理</p>
        </div>
        <div class="card text-center">
          <div class="stat-icon bg-amber-50 text-amber-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <p class="text-3xl font-bold text-amber-600">{{ returnedCount }}</p>
          <p class="text-sm text-gray-500 mt-1">需修改</p>
        </div>
        <div class="card text-center" v-if="store.isLegal">
          <div class="stat-icon bg-red-50 text-red-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <p class="text-3xl font-bold text-red-600">{{ queueCount }}</p>
          <p class="text-sm text-gray-500 mt-1">待审核</p>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <router-link to="/submit" class="card quick-action-card">
          <div class="flex items-center gap-3">
            <div class="quick-action-icon bg-sky-50">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand)" stroke-width="2"><path d="M12 5v14M5 12h14" stroke-linecap="round"/></svg>
            </div>
            <div>
              <p class="text-[15px] font-semibold text-gray-800 dark:text-gray-200">提交物料</p>
              <p class="text-xs text-gray-400">上传广告内容开始审查</p>
            </div>
          </div>
        </router-link>
        <router-link to="/legal" class="card quick-action-card">
          <div class="flex items-center gap-3">
            <div class="quick-action-icon bg-green-50">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2"><path d="M9 12l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
            <div>
              <p class="text-[15px] font-semibold text-gray-800 dark:text-gray-200">查看审查结果</p>
              <p class="text-xs text-gray-400">查看风险评分和合规详情</p>
            </div>
          </div>
        </router-link>
        <router-link to="/legal" class="card quick-action-card">
          <div class="flex items-center gap-3">
            <div class="quick-action-icon bg-purple-50">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8B5CF6" stroke-width="2"><path d="M3 6l9-3 9 3M3 6v12l9 3 9-3V6M3 6l9 3 9-3M12 9v12" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
            <div>
              <p class="text-[15px] font-semibold text-gray-800 dark:text-gray-200">法务审核台</p>
              <p class="text-xs text-gray-400">查看待审核物料列表</p>
            </div>
          </div>
        </router-link>
      </div>

      <!-- Recent + Compliance Tip -->
      <div class="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4 min-w-0">
        <div class="card" v-if="materials.length">
          <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-4">最近提交</h3>
          <p v-if="navigationError" class="text-sm text-red-500 mb-2">{{ navigationError }}</p>
          <div v-for="m in materials.slice(0, 5)" :key="m.id"
               class="flex flex-col sm:flex-row sm:items-center sm:justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0 gap-2">
            <div class="min-w-0">
              <button class="text-sky-600 hover:underline text-left font-medium break-words" @click="openMaterial(m)">{{ m.name }}</button>
              <span class="text-xs text-gray-400 ml-2">{{ m.industry }}</span>
              <span v-if="m.current_version > 1" class="text-xs text-gray-400 ml-1">第{{ m.current_version }}次</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <StatusBadge :variant="statusVariant(m.status)">{{ statusLabel(m.status) }}</StatusBadge>
            </div>
            <div v-if="store.isMarketing && m.status === 'returned'" class="flex flex-wrap gap-2 items-center text-xs w-full sm:w-auto">
              <span class="text-orange-600 break-words">
                法务已退回
                <template v-if="getQueueInfo(m.id)?.return_reasons">：{{ getQueueInfo(m.id)?.return_reasons }}</template>
              </span>
              <router-link :to="`/submit?edit=${m.id}`" class="text-sky-600 hover:underline shrink-0">修改并重新提交</router-link>
              <button @click.stop="handleArchive(m)" :disabled="archiving[m.id]" class="text-gray-500 hover:text-gray-700 hover:underline shrink-0">归档</button>
            </div>
          </div>
        </div>
        <div v-else-if="!loading" class="card text-center text-gray-400">
          <p v-if="store.canSubmit">暂无提交记录，<router-link to="/submit" class="text-sky-600 hover:underline">去提交物料</router-link></p>
          <p v-else>暂无需要处理的审核物料</p>
        </div>

        <div class="card compliance-tip-card">
          <div class="flex items-center gap-2 mb-3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <h3 class="text-sm font-semibold text-amber-700">合规小贴士</h3>
          </div>
          <p class="text-sm text-amber-700 leading-relaxed">广告中使用「最」「第一」等绝对化用语违反《广告法》第九条。提交前请检查文案中是否含有禁用词汇。</p>
        </div>
      </div>
    </div>
  </DefaultLayout>
</template>
