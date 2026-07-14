<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { reviewsApi } from '@/api/reviews'
import { materialsApi } from '@/api/materials'
import { adminSettingsApi } from '@/api/adminSettings'
import { useUserStore } from '@/stores/user'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { ReviewQueueItem } from '@/types'

const store = useUserStore()
const router = useRouter()
const queue = ref<ReviewQueueItem[]>([])
const loading = ref(true)
const archiving = ref<Record<string, boolean>>({})
const deleting = ref<Record<string, boolean>>({})

onMounted(async () => {
  await loadQueue()
})

async function loadQueue() {
  loading.value = true
  try {
    const res = await reviewsApi.queue()
    queue.value = res.data
  } finally {
    loading.value = false
  }
}

function priorityColor(p: string) {
  return p === 'extreme' ? 'text-red-600 bg-red-50' : p === 'urgent' ? 'text-orange-600 bg-orange-50' : 'text-gray-600 bg-gray-100'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    pending_legal: '待审核',
    approved: '已通过',
    conditional_approved: '有条件通过',
    returned: '已退回',
    draft: '草稿',
    ai_reviewing: '审查中',
    archived: '已归档',
  }
  return map[status] || status
}

function statusClass(status: string) {
  if (status === 'approved') return 'bg-green-100 text-green-700'
  if (status === 'conditional_approved') return 'bg-blue-100 text-blue-700'
  if (status === 'pending_legal' || status === 'ai_reviewing') return 'bg-yellow-100 text-yellow-700'
  if (status === 'returned') return 'bg-red-100 text-red-700'
  if (status === 'archived') return 'bg-gray-100 text-gray-500'
  return 'bg-gray-100 text-gray-600'
}

function statusVariant(status: string): 'success' | 'warning' | 'danger' | 'info' | 'gray' {
  if (status === 'approved' || status === 'conditional_approved') return 'success'
  if (status === 'pending_legal' || status === 'ai_reviewing') return 'warning'
  if (status === 'returned') return 'danger'
  return 'gray'
}

function goResubmit(item: ReviewQueueItem) {
  router.push({ path: '/submit', query: { edit: item.material_id } })
}

function detailLink(item: ReviewQueueItem): string {
  return store.isMarketing ? `/result/${item.id}` : `/legal/${item.id}`
}

async function handleArchive(item: ReviewQueueItem) {
  if (!confirm('确认归档该物料？归档后不再参与待办。')) return
  archiving.value[item.material_id] = true
  try {
    await materialsApi.archive(item.material_id)
    await loadQueue()
  } finally {
    archiving.value[item.material_id] = false
  }
}

async function handleAdminDelete(item: ReviewQueueItem) {
  if (!confirm(`将物料「${item.material_name}」及其审核记录移入回收站？15 天内可恢复。`)) return
  deleting.value[item.material_id] = true
  try {
    await adminSettingsApi.moveToRecycleBin('material', item.material_id)
    queue.value = queue.value.filter(queueItem => queueItem.material_id !== item.material_id)
  } catch (error: any) {
    alert(error.response?.data?.detail || '删除失败')
  } finally {
    deleting.value[item.material_id] = false
  }
}

</script>

<template>
  <DefaultLayout>
    <div class="page-container max-w-6xl">
      <div class="responsive-toolbar mb-6">
        <div>
          <h2 class="page-heading">{{ store.isMarketing ? '我的提交' : '法务审核台' }}</h2>
          <p class="text-sm text-gray-400 mt-1">智能合规 · 广告无忧</p>
        </div>
        <span class="text-sm text-gray-400">{{ queue.length }} 条记录</span>
      </div>

      <!-- Stat cards -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div class="card text-center">
          <div class="stat-icon bg-amber-50 text-amber-600 mx-auto">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8v4l3 3M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <p class="text-2xl font-bold">{{ queue.filter(q => q.status === 'pending_legal').length }}</p>
          <p class="text-xs text-gray-400 mt-1">待审核</p>
        </div>
        <div class="card text-center">
          <div class="stat-icon bg-blue-50 text-blue-600 mx-auto">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0zM12 8v4" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <p class="text-2xl font-bold">{{ queue.filter(q => q.status === 'ai_reviewing').length }}</p>
          <p class="text-xs text-gray-400 mt-1">审查中</p>
        </div>
        <div class="card text-center">
          <div class="stat-icon bg-green-50 text-green-600 mx-auto">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <p class="text-2xl font-bold">{{ queue.filter(q => q.status === 'approved' || q.status === 'conditional_approved').length }}</p>
          <p class="text-xs text-gray-400 mt-1">已通过</p>
        </div>
        <div class="card text-center">
          <div class="stat-icon bg-red-50 text-red-600 mx-auto">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <p class="text-2xl font-bold">{{ queue.filter(q => q.status === 'returned').length }}</p>
          <p class="text-xs text-gray-400 mt-1">已退回</p>
        </div>
      </div>

      <!-- Loading / Empty -->
      <div v-if="loading" class="text-gray-400 py-12 text-center">加载中...</div>
      <div v-else-if="!queue.length" class="card text-center text-gray-400 py-12">
        {{ store.isMarketing ? '暂无提交记录，去提交物料开始审查' : '暂无待审核物料' }}
      </div>

      <!-- Table -->
      <div v-else class="card !p-0 overflow-hidden">
        <!-- Desktop table header -->
        <div class="hidden sm:grid gap-4 px-5 py-3 bg-gray-50 dark:bg-gray-800 text-xs font-semibold text-gray-500 border-b border-gray-200 dark:border-gray-700" :class="store.isAdmin ? 'grid-cols-8' : 'grid-cols-7'">
          <span>物料名称</span>
          <span>提交人</span>
          <span>行业</span>
          <span>风险分</span>
          <span>优先级</span>
          <span>等待时间</span>
          <span>状态</span>
          <span v-if="store.isAdmin" class="text-right">操作</span>
        </div>

        <div v-for="item in queue" :key="item.id">
          <!-- Desktop row -->
          <div class="hidden sm:grid gap-4 px-5 py-3 text-sm hover:bg-gray-50 dark:hover:bg-gray-800/50 border-b border-gray-100 dark:border-gray-700 last:border-0 items-center" :class="store.isAdmin ? 'grid-cols-8' : 'grid-cols-7'">
            <router-link :to="detailLink(item)" class="contents">
              <span class="text-sky-600 truncate">{{ item.material_name }}</span>
              <span class="text-gray-600 dark:text-gray-300">{{ item.submitter_name }}</span>
              <span class="text-gray-500">{{ item.industry }}</span>
              <span class="font-bold" :class="{ 'text-red-500': item.ai_risk_score < 60, 'text-yellow-500': item.ai_risk_score >= 60 && item.ai_risk_score < 80, 'text-green-500': item.ai_risk_score >= 80 }">{{ item.ai_risk_score }}</span>
              <span><StatusBadge :variant="item.priority === 'extreme' ? 'danger' : item.priority === 'urgent' ? 'warning' : 'gray'">{{ item.priority === 'extreme' ? '极速' : item.priority === 'urgent' ? '加急' : '普通' }}</StatusBadge></span>
              <span class="text-gray-400">{{ item.waiting_hours ?? 0 }}h</span>
              <span><StatusBadge :variant="statusVariant(item.status)">{{ statusLabel(item.status) }}</StatusBadge></span>
            </router-link>
            <span v-if="store.isAdmin" class="text-right">
              <button class="text-xs text-red-600 hover:underline disabled:opacity-50" :disabled="deleting[item.material_id]" @click="handleAdminDelete(item)">
                {{ deleting[item.material_id] ? '删除中…' : '删除' }}
              </button>
            </span>
          </div>

          <!-- Return info for desktop -->
          <div v-if="store.isMarketing && item.status === 'returned'" class="hidden sm:block px-5 py-2 bg-orange-50 dark:bg-orange-900/20 border-b border-orange-100 dark:border-orange-800 text-sm">
            <div class="flex flex-wrap gap-4 items-start">
              <div class="flex-1">
                <span class="text-orange-700 dark:text-orange-300 font-medium">法务退回 · 第{{ item.version }}次提交</span>
                <span v-if="item.return_reasons" class="text-orange-600 dark:text-orange-400 ml-2">原因：{{ item.return_reasons }}</span>
                <span v-if="item.legal_notes" class="text-gray-500 ml-2">备注：{{ item.legal_notes }}</span>
              </div>
              <div class="flex gap-2 shrink-0">
                <button @click.prevent="goResubmit(item)" class="btn-primary text-xs min-h-[32px] px-3 py-1">修改并重新提交</button>
                <button @click.prevent="handleArchive(item)" :disabled="archiving[item.material_id]" class="btn-ghost text-xs">归档</button>
              </div>
            </div>
          </div>

          <!-- Mobile card -->
          <div class="block sm:hidden p-4 border-b last:border-0 hover:bg-gray-50 dark:hover:bg-gray-800/50">
            <router-link :to="detailLink(item)" class="block">
              <div class="flex items-center justify-between mb-1">
                <span class="font-medium text-sky-600 truncate">{{ item.material_name }}</span>
                <StatusBadge :variant="statusVariant(item.status)">{{ statusLabel(item.status) }}</StatusBadge>
              </div>
              <div class="flex gap-3 text-xs text-gray-500">
                <span>{{ item.submitter_name }}</span>
                <span>{{ item.industry }}</span>
                <span>风险: {{ item.ai_risk_score }}</span>
                <span>{{ item.waiting_hours ?? 0 }}h</span>
              </div>
            </router-link>
            <div v-if="store.isAdmin" class="flex justify-end mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
              <button class="text-xs text-red-600 hover:underline disabled:opacity-50" :disabled="deleting[item.material_id]" @click="handleAdminDelete(item)">
                {{ deleting[item.material_id] ? '删除中…' : '删除' }}
              </button>
            </div>
          </div>

          <!-- Return info for mobile -->
          <div v-if="store.isMarketing && item.status === 'returned'" class="sm:hidden px-4 py-2 bg-orange-50 dark:bg-orange-900/20 border-b border-orange-100 dark:border-orange-800 text-xs">
            <p class="text-orange-700 dark:text-orange-300 font-medium mb-1">法务退回 · 第{{ item.version }}次提交</p>
            <p v-if="item.return_reasons" class="text-orange-600 dark:text-orange-400">原因：{{ item.return_reasons }}</p>
            <p v-if="item.legal_notes" class="text-gray-500">备注：{{ item.legal_notes }}</p>
            <div class="flex gap-2 mt-2">
              <button @click="goResubmit(item)" class="btn-primary text-xs min-h-[32px]">修改并重新提交</button>
              <button @click="handleArchive(item)" :disabled="archiving[item.material_id]" class="btn-ghost text-xs">归档</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </DefaultLayout>
</template>
