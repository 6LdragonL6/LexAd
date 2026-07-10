<!-- frontend/src/pages/HomePage.vue -->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
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
    <div class="max-w-4xl mx-auto p-4 lg:p-8">
      <h2 class="page-heading">
        {{ store.isMarketing ? '我的工作台' : store.isLegal ? '法务工作台' : '管理面板' }}
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
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
        <h3 class="font-semibold mb-3">{{ store.isLegal ? '最近审核物料' : '最近提交' }}</h3>
        <p v-if="navigationError" class="text-sm text-red-500 mb-2">{{ navigationError }}</p>
        <div v-for="m in materials.slice(0, 5)" :key="m.id"
             class="flex flex-col sm:flex-row sm:items-center sm:justify-between py-2 border-b border-gray-100 last:border-0 gap-1">
          <div>
            <button class="text-sky-700 hover:underline text-left" @click="openMaterial(m)">{{ m.name }}</button>
            <span class="text-xs text-gray-400 ml-2">{{ m.industry }}</span>
            <span v-if="m.current_version > 1" class="text-xs text-gray-400 ml-1">第{{ m.current_version }}次</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs px-2 py-0.5 rounded-full"
                  :class="{
                    'bg-green-100 text-green-700': m.status === 'approved',
                    'bg-blue-100 text-blue-700': m.status === 'conditional_approved',
                    'bg-yellow-100 text-yellow-700': m.status === 'pending_legal',
                    'bg-red-100 text-red-700': m.status === 'returned',
                    'bg-gray-100 text-gray-600': m.status === 'draft',
                    'bg-gray-100 text-gray-500': m.status === 'archived',
                  }">
              {{ m.status === 'approved' ? '已通过' : m.status === 'conditional_approved' ? '有条件通过' : m.status === 'pending_legal' ? '待法务审核' : m.status === 'returned' ? '已退回' : m.status === 'draft' ? '草稿' : m.status === 'archived' ? '已归档' : m.status }}
            </span>
          </div>
          <!-- Return info for marketing -->
          <div v-if="store.isMarketing && m.status === 'returned'" class="flex flex-wrap gap-2 items-center text-xs">
            <span class="text-orange-600">
              法务已退回
              <template v-if="getQueueInfo(m.id)?.return_reasons">：{{ getQueueInfo(m.id)?.return_reasons }}</template>
            </span>
            <span v-if="getQueueInfo(m.id)?.legal_notes" class="text-gray-500">备注：{{ getQueueInfo(m.id)?.legal_notes }}</span>
            <router-link :to="`/submit?edit=${m.id}`" class="text-sky-600 hover:underline">修改并重新提交</router-link>
            <button @click.stop="handleArchive(m)" :disabled="archiving[m.id]" class="text-gray-500 hover:text-gray-700 hover:underline">归档</button>
          </div>
        </div>
      </div>
      <p v-else-if="!loading" class="text-gray-400 text-center py-8">
        <template v-if="store.canSubmit">
          暂无提交记录，<router-link to="/submit" class="text-sky-700 hover:underline">去提交物料</router-link>
        </template>
        <template v-else>暂无需要处理的审核物料</template>
      </p>
    </div>
  </DefaultLayout>
</template>
