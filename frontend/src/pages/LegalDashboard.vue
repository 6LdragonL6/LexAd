<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { reviewsApi } from '@/api/reviews'
import { materialsApi } from '@/api/materials'
import { useUserStore } from '@/stores/user'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import type { ReviewQueueItem } from '@/types'

const store = useUserStore()
const router = useRouter()
const queue = ref<ReviewQueueItem[]>([])
const loading = ref(true)
const archiving = ref<Record<string, boolean>>({})

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
    returned: '已退回',
    draft: '草稿',
    ai_reviewing: '审查中',
    archived: '已归档',
  }
  return map[status] || status
}

function statusClass(status: string) {
  if (status === 'approved') return 'bg-green-100 text-green-700'
  if (status === 'pending_legal' || status === 'ai_reviewing') return 'bg-yellow-100 text-yellow-700'
  if (status === 'returned') return 'bg-red-100 text-red-700'
  if (status === 'archived') return 'bg-gray-100 text-gray-500'
  return 'bg-gray-100 text-gray-600'
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

</script>

<template>
  <DefaultLayout>
    <div class="max-w-5xl mx-auto p-4 lg:p-8">
      <h2 class="page-heading">{{ store.isMarketing ? '我的提交' : '法务审核台' }}</h2>
      <div v-if="loading" class="text-gray-400 py-8 text-center">加载中...</div>
      <div v-else-if="!queue.length" class="text-gray-400 py-8 text-center">
        {{ store.isMarketing ? '暂无提交记录，去提交物料开始审查' : '暂无待审核物料' }}
      </div>
      <div v-else class="card overflow-hidden !p-0">
        <!-- Desktop table header -->
        <div class="hidden sm:grid grid-cols-7 gap-4 px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-500 border-b">
          <span>物料名称</span>
          <span>提交人</span>
          <span>行业</span>
          <span>风险分</span>
          <span>优先级</span>
          <span>等待时间</span>
          <span>状态</span>
        </div>
        <!-- Desktop table rows -->
        <div v-for="item in queue" :key="item.id">
          <router-link :to="detailLink(item)"
            class="hidden sm:grid grid-cols-7 gap-4 px-4 py-3 text-sm hover:bg-gray-50 border-b last:border-0 items-center">
            <span class="text-sky-700 truncate">{{ item.material_name }}</span>
            <span class="text-gray-600">{{ item.submitter_name }}</span>
            <span class="text-gray-500">{{ item.industry }}</span>
            <span :class="{ 'text-red-500 font-bold': item.ai_risk_score < 60, 'text-yellow-500': item.ai_risk_score >= 60 && item.ai_risk_score < 80, 'text-green-500': item.ai_risk_score >= 80 }">{{ item.ai_risk_score }}</span>
            <span :class="priorityColor(item.priority)" class="text-xs px-1.5 py-0.5 rounded-full inline-block w-fit">{{ item.priority === 'extreme' ? '极速' : item.priority === 'urgent' ? '加急' : '普通' }}</span>
            <span class="text-gray-400">{{ item.waiting_hours ?? 0 }}h</span>
            <span class="text-xs px-1.5 py-0.5 rounded-full w-fit" :class="statusClass(item.status)">
              {{ statusLabel(item.status) }}
            </span>
          </router-link>
          <!-- Return info banner for marketing returned items -->
          <div v-if="store.isMarketing && item.status === 'returned'"
            class="hidden sm:block px-4 py-2 bg-orange-50 border-b border-orange-100 text-sm">
            <div class="flex flex-wrap gap-4 items-start">
              <div class="flex-1">
                <span class="text-orange-700 font-medium">法务退回 · 第{{ item.version }}次提交</span>
                <span v-if="item.return_reasons" class="text-orange-600 ml-2">原因：{{ item.return_reasons }}</span>
                <span v-if="item.legal_notes" class="text-gray-500 ml-2">备注：{{ item.legal_notes }}</span>
              </div>
              <div class="flex gap-2 shrink-0">
                <button @click.prevent="goResubmit(item)" class="px-3 py-1 text-xs bg-sky-600 text-white rounded hover:bg-sky-700">修改并重新提交</button>
                <button @click.prevent="handleArchive(item)" :disabled="archiving[item.material_id]" class="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300">归档</button>
              </div>
            </div>
          </div>
        </div>
        <!-- Mobile cards -->
        <div v-for="item in queue" :key="'m-' + item.id">
          <router-link :to="detailLink(item)"
            class="block sm:hidden p-4 border-b last:border-0 hover:bg-gray-50">
            <div class="flex items-center justify-between mb-1">
              <span class="font-medium text-sky-700 truncate">{{ item.material_name }}</span>
              <span class="text-xs px-1.5 py-0.5 rounded-full shrink-0 ml-2" :class="statusClass(item.status)">
                {{ statusLabel(item.status) }}
              </span>
            </div>
            <div class="flex gap-3 text-xs text-gray-500">
              <span>{{ item.submitter_name }}</span>
              <span>{{ item.industry }}</span>
              <span>风险: {{ item.ai_risk_score }}</span>
              <span :class="priorityColor(item.priority)">{{ item.priority === 'extreme' ? '极速' : item.priority === 'urgent' ? '加急' : '普通' }}</span>
              <span>{{ item.waiting_hours ?? 0 }}h</span>
            </div>
          </router-link>
          <!-- Return info for mobile marketing returned items -->
          <div v-if="store.isMarketing && item.status === 'returned'"
            class="sm:hidden px-4 py-2 bg-orange-50 border-b border-orange-100 text-xs">
            <p class="text-orange-700 font-medium mb-1">法务退回 · 第{{ item.version }}次提交</p>
            <p v-if="item.return_reasons" class="text-orange-600">原因：{{ item.return_reasons }}</p>
            <p v-if="item.legal_notes" class="text-gray-500">备注：{{ item.legal_notes }}</p>
            <div class="flex gap-2 mt-2">
              <button @click="goResubmit(item)" class="px-2 py-1 text-xs bg-sky-600 text-white rounded">修改并重新提交</button>
              <button @click="handleArchive(item)" :disabled="archiving[item.material_id]" class="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded">归档</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </DefaultLayout>
</template>
