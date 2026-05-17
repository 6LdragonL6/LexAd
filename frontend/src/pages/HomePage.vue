<!-- frontend/src/pages/HomePage.vue -->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import type { Material, ReviewQueueItem } from '@/types'

const store = useUserStore()
const materials = ref<Material[]>([])
const queue = ref<ReviewQueueItem[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [mRes, qRes] = await Promise.all([materialsApi.list(), reviewsApi.queue()])
    materials.value = mRes.data
    queue.value = qRes.data
  } finally {
    loading.value = false
  }
})

const pendingCount = computed(() => materials.value.filter(m => m.status !== 'approved' && m.status !== 'draft').length)
const returnedCount = computed(() => materials.value.filter(m => m.status === 'returned').length)
const queueCount = computed(() => queue.value.length)
</script>

<template>
  <DefaultLayout>
    <div class="max-w-4xl mx-auto p-8">
      <h2 class="text-xl font-bold mb-6">
        {{ store.isMarketing ? '我的工作台' : store.isLegal ? '法务工作台' : '管理面板' }}
      </h2>
      <div class="grid grid-cols-3 gap-4 mb-8">
        <div class="card text-center">
          <p class="text-3xl font-bold text-sky-600">{{ pendingCount }}</p>
          <p class="text-sm text-gray-500 mt-1">待处理</p>
        </div>
        <div class="card text-center">
          <p class="text-3xl font-bold text-orange-500">{{ returnedCount }}</p>
          <p class="text-sm text-gray-500 mt-1">需修改</p>
        </div>
        <div class="card text-center" v-if="store.isLegal">
          <p class="text-3xl font-bold text-red-500">{{ queueCount }}</p>
          <p class="text-sm text-gray-500 mt-1">待审核</p>
        </div>
      </div>
      <div class="card" v-if="materials.length">
        <h3 class="font-semibold mb-3">最近提交</h3>
        <div v-for="m in materials.slice(0, 5)" :key="m.id"
             class="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
          <div>
            <router-link :to="`/result/${m.id}`" class="text-sky-700 hover:underline">{{ m.name }}</router-link>
            <span class="text-xs text-gray-400 ml-2">{{ m.industry }}</span>
          </div>
          <span class="text-xs px-2 py-0.5 rounded-full"
                :class="{
                  'bg-green-100 text-green-700': m.status === 'approved',
                  'bg-yellow-100 text-yellow-700': m.status === 'pending_legal',
                  'bg-red-100 text-red-700': m.status === 'returned',
                  'bg-gray-100 text-gray-600': m.status === 'draft',
                }">
            {{ m.status === 'approved' ? '已通过' : m.status === 'pending_legal' ? '待法务审核' : m.status === 'returned' ? '已退回' : m.status === 'draft' ? '草稿' : m.status }}
          </span>
        </div>
      </div>
      <p v-else-if="!loading" class="text-gray-400 text-center py-8">暂无提交记录，<router-link to="/submit" class="text-sky-700 hover:underline">去提交物料</router-link></p>
    </div>
  </DefaultLayout>
</template>
