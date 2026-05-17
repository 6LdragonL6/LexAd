<!-- frontend/src/pages/KnowledgePage.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { knowledgeApi } from '@/api/knowledge'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import type { LawItem } from '@/types'

const tab = ref<'laws' | 'cases' | 'templates'>('laws')
const laws = ref<LawItem[]>([])
const cases = ref<any[]>([])
const templates = ref<Record<string, string>>({})
const loading = ref(false)

async function loadTab() {
  loading.value = true
  if (tab.value === 'laws') {
    const res = await knowledgeApi.laws()
    laws.value = res.data.items
  } else if (tab.value === 'cases') {
    const res = await knowledgeApi.cases()
    cases.value = res.data.items
  } else {
    const res = await knowledgeApi.templates()
    templates.value = res.data.items
  }
  loading.value = false
}

onMounted(loadTab)
</script>

<template>
  <DefaultLayout>
    <div class="max-w-4xl mx-auto p-8">
      <h2 class="text-xl font-bold mb-6">法规数据库</h2>
      <div class="flex gap-1 mb-6 border-b">
        <button v-for="t in [{ k: 'laws', l: '法律法规' }, { k: 'cases', l: '行政处罚案例' }, { k: 'templates', l: '改写模板' }]" :key="t.k"
          @click="tab = t.k as any; loadTab()"
          :class="tab === t.k ? 'border-b-2 border-sky-500 text-sky-700' : 'text-gray-500'"
          class="px-4 py-2 text-sm font-medium">
          {{ t.l }}
        </button>
      </div>
      <div v-if="loading" class="text-gray-400 py-8 text-center">加载中...</div>
      <div v-else-if="tab === 'laws'" class="space-y-2">
        <div v-for="law in laws" :key="law.id" class="card text-sm">
          <p class="font-medium">{{ law.title }}</p>
        </div>
      </div>
      <div v-else-if="tab === 'cases'" class="space-y-2">
        <div v-for="c in cases" :key="c.id" class="card text-sm flex justify-between">
          <span>{{ c.title }}</span>
          <span class="text-gray-400">{{ c.province }}</span>
        </div>
      </div>
      <div v-else class="text-sm text-gray-600">
        <p>共 {{ Object.keys(templates).length }} 条改写模板</p>
        <div v-for="(replacement, original) in templates" :key="original" class="card mb-2 flex justify-between">
          <span class="text-red-500 line-through">{{ original }}</span>
          <span class="text-gray-400">→</span>
          <span class="text-green-600">{{ replacement }}</span>
        </div>
      </div>
    </div>
  </DefaultLayout>
</template>
