<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { reviewsApi } from '@/api/reviews'
import { useUserStore } from '@/stores/user'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import type { ReviewQueueItem } from '@/types'

const store = useUserStore()
const queue = ref<ReviewQueueItem[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await reviewsApi.queue()
    queue.value = res.data
  } finally {
    loading.value = false
  }
})

function priorityColor(p: string) {
  return p === 'extreme' ? 'text-red-600 bg-red-50' : p === 'urgent' ? 'text-orange-600 bg-orange-50' : 'text-gray-600 bg-gray-100'
}
</script>

<template>
  <DefaultLayout>
    <div class="max-w-5xl mx-auto p-8">
      <h2 class="text-xl font-bold mb-6">{{ store.isMarketing ? '我的提交' : '法务审核台' }}</h2>
      <div v-if="loading" class="text-gray-400 py-8 text-center">加载中...</div>
      <div v-else-if="!queue.length" class="text-gray-400 py-8 text-center">暂无待审核物料</div>
      <div v-else class="card overflow-hidden !p-0">
        <div class="grid grid-cols-7 gap-4 px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-500 border-b">
          <span>物料名称</span>
          <span>提交人</span>
          <span>行业</span>
          <span>风险分</span>
          <span>优先级</span>
          <span>等待时间</span>
          <span>状态</span>
        </div>
        <router-link v-for="item in queue" :key="item.id" :to="`/legal/${item.id}`"
          class="grid grid-cols-7 gap-4 px-4 py-3 text-sm hover:bg-gray-50 border-b last:border-0 items-center">
          <span class="text-sky-600 truncate">{{ item.material_name }}</span>
          <span class="text-gray-600">{{ item.submitter_name }}</span>
          <span class="text-gray-500">{{ item.industry }}</span>
          <span :class="{ 'text-red-500 font-bold': item.ai_risk_score < 60, 'text-yellow-500': item.ai_risk_score >= 60 && item.ai_risk_score < 80, 'text-green-500': item.ai_risk_score >= 80 }">{{ item.ai_risk_score }}</span>
          <span :class="priorityColor(item.priority)" class="text-xs px-1.5 py-0.5 rounded-full inline-block w-fit">{{ item.priority === 'extreme' ? '极速' : item.priority === 'urgent' ? '加急' : '普通' }}</span>
          <span class="text-gray-400">{{ item.waiting_hours ?? 0 }}h</span>
          <span class="text-xs px-1.5 py-0.5 rounded-full w-fit"
            :class="{ 'bg-green-100 text-green-700': item.status === 'approved', 'bg-yellow-100 text-yellow-700': item.status === 'pending_legal', 'bg-red-100 text-red-700': item.status === 'returned' }">
            {{ item.status === 'pending_legal' ? '待审核' : item.status === 'approved' ? '已通过' : item.status === 'returned' ? '已退回' : item.status }}
          </span>
        </router-link>
      </div>
    </div>
  </DefaultLayout>
</template>
