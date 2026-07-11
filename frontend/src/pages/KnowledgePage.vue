<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { knowledgeApi } from '@/api/knowledge'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import type { KnowledgeCatalog, KnowledgeContent, KnowledgeItem } from '@/types'

const layers = [
  { key: 'L1', label: '法律法规' },
  { key: 'L2', label: '行业规则' },
  { key: 'L3', label: '处罚案例' },
  { key: 'L4', label: '平台规则' },
  { key: 'L5', label: '合规模板' },
] as const

const activeLayer = ref<(typeof layers)[number]['key']>('L1')
const catalog = ref<KnowledgeCatalog | null>(null)
const selectedGroup = ref('')
const selectedContent = ref<KnowledgeContent | null>(null)
const loading = ref(false)
const contentLoading = ref(false)
const error = ref('')

const groups = computed(() => {
  if (!catalog.value) return []
  return [...new Set(catalog.value.items.map((item) => item.group))]
})

const visibleItems = computed(() => {
  if (!catalog.value) return []
  if (!selectedGroup.value) return catalog.value.items
  return catalog.value.items.filter((item) => item.group === selectedGroup.value)
})

async function loadLayer(layer = activeLayer.value) {
  activeLayer.value = layer
  loading.value = true
  error.value = ''
  selectedContent.value = null
  selectedGroup.value = ''
  try {
    const response = await knowledgeApi.catalog(layer)
    catalog.value = response.data
    selectedGroup.value = groups.value[0] || ''
  } catch (requestError: any) {
    catalog.value = null
    error.value = requestError.response?.data?.detail || '知识库目录加载失败'
  } finally {
    loading.value = false
  }
}

async function openItem(item: KnowledgeItem) {
  contentLoading.value = true
  error.value = ''
  try {
    const response = await knowledgeApi.content(item.id)
    selectedContent.value = response.data
  } catch (requestError: any) {
    error.value = requestError.response?.data?.detail || '法规正文加载失败'
  } finally {
    contentLoading.value = false
  }
}

onMounted(() => loadLayer())
</script>

<template>
  <DefaultLayout>
    <div class="page-container max-w-6xl">
      <div class="responsive-toolbar mb-6">
        <div>
          <h2 class="page-heading !mb-1">法规数据库</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400">按知识层级浏览法规、行业规则、案例、平台规范和合规模板。</p>
        </div>
        <span v-if="catalog" class="text-xs text-gray-400 dark:text-gray-500">当前分类共 {{ catalog.total }} 项</span>
      </div>

      <div class="card !p-0 overflow-hidden">
        <div class="flex overflow-x-auto border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <button
            v-for="layer in layers"
            :key="layer.key"
            class="px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors"
            :class="activeLayer === layer.key
              ? 'border-sky-500 bg-white dark:bg-gray-900 text-sky-700 dark:text-sky-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white dark:hover:bg-gray-900'"
            @click="loadLayer(layer.key)"
          >
            <span class="font-bold mr-1">{{ layer.key }}</span>{{ layer.label }}
          </button>
        </div>

        <div v-if="loading" class="py-20 text-center">
          <div class="w-8 h-8 border-3 border-sky-100 border-t-sky-500 rounded-full animate-spin mx-auto mb-3" />
          <p class="text-sm text-gray-400 dark:text-gray-500">正在读取知识库目录...</p>
        </div>

        <div v-else-if="error && !catalog" class="py-16 px-4 text-center">
          <p class="text-sm text-red-500">{{ error }}</p>
          <button class="btn-outline mt-4 text-sm" @click="loadLayer()">重新加载</button>
        </div>

        <div v-else-if="catalog" class="grid grid-cols-1 lg:grid-cols-[220px_minmax(0,1fr)] min-h-520px min-w-0">
          <aside class="border-b lg:border-b-0 lg:border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-3">
            <p class="px-2 py-1 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase">分类目录</p>
            <div class="flex lg:block gap-2 overflow-x-auto lg:overflow-visible mt-1">
              <button
                v-for="group in groups"
                :key="group"
                class="block shrink-0 lg:w-full text-left px-3 py-2 rounded-lg text-sm transition-colors"
                :class="selectedGroup === group
                  ? 'bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-400 font-medium'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'"
                @click="selectedGroup = group; selectedContent = null"
              >
                {{ group }}
                <span class="ml-1 text-xs opacity-60">
                  {{ catalog.items.filter((item) => item.group === group).length }}
                </span>
              </button>
            </div>
          </aside>

          <main class="min-w-0">
            <div v-if="contentLoading" class="py-20 text-center text-sm text-gray-400 dark:text-gray-500">正文加载中...</div>

            <article v-else-if="selectedContent" class="p-4 sm:p-6">
              <button class="text-sm text-sky-600 hover:text-sky-700 mb-4" @click="selectedContent = null">
                ← 返回条目列表
              </button>
              <div class="border-b border-gray-100 dark:border-gray-700 pb-4 mb-5">
                <span class="inline-flex px-2 py-0.5 rounded-full bg-sky-50 dark:bg-sky-900/30 text-sky-700 dark:text-sky-400 text-xs font-medium">
                  {{ selectedContent.layer }}
                </span>
                <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mt-2 break-words">{{ selectedContent.title }}</h3>
              </div>
              <pre class="font-sans text-sm leading-7 text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words">{{ selectedContent.content }}</pre>
            </article>

            <div v-else class="p-4 sm:p-6">
              <div class="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-700">
                <h3 class="font-semibold text-gray-800 dark:text-gray-200">{{ selectedGroup || catalog.label }}</h3>
                <span class="text-xs text-gray-400 dark:text-gray-500">{{ visibleItems.length }} 项</span>
              </div>
              <div v-if="visibleItems.length" class="divide-y divide-gray-100 dark:divide-gray-700">
                <button
                  v-for="item in visibleItems"
                  :key="item.id"
                  class="w-full text-left py-3 px-2 text-sm text-gray-700 dark:text-gray-300 hover:text-sky-700 dark:hover:text-sky-400 hover:bg-sky-50 dark:hover:bg-sky-900/20 rounded-lg break-words transition-colors"
                  @click="openItem(item)"
                >
                  {{ item.title }}
                </button>
              </div>
              <p v-else class="py-16 text-center text-sm text-gray-400 dark:text-gray-500">该分类暂无知识库文件</p>
            </div>
          </main>
        </div>
      </div>

      <p v-if="error && catalog" class="mt-3 text-sm text-red-500">{{ error }}</p>
    </div>
  </DefaultLayout>
</template>
