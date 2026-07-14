<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { adminSettingsApi } from '@/api/adminSettings'
import type { AiConfigStatus, RecycleBinEntry, RecycleTargetType } from '@/types'

const tab = ref<'ai' | 'recycle'>('ai')
const aiConfig = ref<AiConfigStatus | null>(null)
const apiKey = ref('')
const aiLoading = ref(false)
const aiMessage = ref('')
const aiError = ref('')
const recycleItems = ref<RecycleBinEntry[]>([])
const recycleTotal = ref(0)
const recycleLoading = ref(false)
const recycleError = ref('')
const typeFilter = ref<RecycleTargetType | ''>('')
const busyEntries = ref<Record<string, boolean>>({})

const typeLabels: Record<RecycleTargetType, string> = {
  material: '物料',
  brand: '品牌',
  public_opinion_event: '舆情案例',
  platform_rule_set: '平台规则',
}

const sourceLabel = computed(() => {
  if (aiConfig.value?.source === 'database') return '管理员配置'
  if (aiConfig.value?.source === 'environment') return '服务器环境变量'
  return '未配置'
})

function formatTime(value: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

async function loadAiConfig() {
  aiError.value = ''
  try {
    aiConfig.value = (await adminSettingsApi.getAiConfig()).data
  } catch (e: any) {
    aiError.value = e.response?.data?.detail || '读取 AI 配置失败'
  }
}

async function saveApiKey() {
  if (!apiKey.value.trim() || aiLoading.value) return
  aiLoading.value = true
  aiError.value = ''
  aiMessage.value = ''
  try {
    aiConfig.value = (await adminSettingsApi.saveAiConfig(apiKey.value.trim())).data
    aiMessage.value = 'API Key 已验证并保存，新的模型调用将立即生效。'
  } catch (e: any) {
    aiError.value = e.response?.data?.detail || '保存失败，原有配置未被覆盖'
  } finally {
    apiKey.value = ''
    aiLoading.value = false
  }
}

async function testApiKey() {
  if (aiLoading.value) return
  aiLoading.value = true
  aiError.value = ''
  aiMessage.value = ''
  try {
    const candidateKey = apiKey.value.trim()
    aiMessage.value = (await adminSettingsApi.testAiConfig(candidateKey || undefined)).data.message
  } catch (e: any) {
    aiError.value = e.response?.data?.detail || '连通性测试失败'
  } finally {
    aiLoading.value = false
  }
}

async function clearApiKey() {
  if (!confirm('确认清除管理员保存的 API Key？服务器环境变量配置（如有）不会被修改。')) return
  aiLoading.value = true
  aiError.value = ''
  aiMessage.value = ''
  try {
    await adminSettingsApi.clearAiConfig()
    await loadAiConfig()
    aiMessage.value = '管理员配置已清除。'
  } catch (e: any) {
    aiError.value = e.response?.data?.detail || '清除失败'
  } finally {
    aiLoading.value = false
  }
}

async function loadRecycleBin() {
  recycleLoading.value = true
  recycleError.value = ''
  try {
    const response = await adminSettingsApi.listRecycleBin(typeFilter.value || undefined)
    recycleItems.value = response.data.items
    recycleTotal.value = response.data.total
  } catch (e: any) {
    recycleError.value = e.response?.data?.detail || '读取回收站失败'
  } finally {
    recycleLoading.value = false
  }
}

async function restoreEntry(entry: RecycleBinEntry) {
  if (!confirm(`确认恢复「${entry.display_name}」？`)) return
  busyEntries.value[entry.id] = true
  try {
    await adminSettingsApi.restore(entry.id)
    await loadRecycleBin()
  } catch (e: any) {
    recycleError.value = e.response?.data?.detail || '恢复失败'
  } finally {
    busyEntries.value[entry.id] = false
  }
}

async function purgeEntry(entry: RecycleBinEntry) {
  if (!confirm(`永久删除「${entry.display_name}」？此操作无法恢复。`)) return
  busyEntries.value[entry.id] = true
  try {
    await adminSettingsApi.purge(entry.id)
    await loadRecycleBin()
  } catch (e: any) {
    recycleError.value = e.response?.data?.detail || '永久删除失败'
  } finally {
    busyEntries.value[entry.id] = false
  }
}

onMounted(async () => {
  await Promise.all([loadAiConfig(), loadRecycleBin()])
})
</script>

<template>
  <DefaultLayout>
    <div class="page-container max-w-6xl">
      <PageHeader title="系统管理" description="配置 DeepSeek 服务并管理运行后新增的数据" />

      <div class="flex flex-wrap gap-2 mb-5" role="tablist" aria-label="系统管理分类">
        <button class="btn-outline" :class="{ 'border-sky-500 text-sky-600': tab === 'ai' }" @click="tab = 'ai'">AI 配置</button>
        <button class="btn-outline" :class="{ 'border-sky-500 text-sky-600': tab === 'recycle' }" @click="tab = 'recycle'">回收站（{{ recycleTotal }}）</button>
      </div>

      <section v-if="tab === 'ai'" class="space-y-5">
        <div class="card">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 class="font-semibold text-gray-800 dark:text-gray-100">DeepSeek 调用配置</h3>
              <p class="text-sm text-gray-500 mt-1">仅 API Key 可配置，地址和模型由系统固定。</p>
            </div>
            <span class="px-3 py-1 rounded-full text-xs" :class="aiConfig?.configured ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
              {{ aiConfig?.configured ? '已配置' : '未配置' }}
            </span>
          </div>
          <dl class="grid sm:grid-cols-2 gap-4 mt-5 text-sm">
            <div><dt class="text-gray-400">服务地址</dt><dd class="mt-1 break-all">{{ aiConfig?.base_url || 'https://api.deepseek.com' }}</dd></div>
            <div><dt class="text-gray-400">固定模型</dt><dd class="mt-1 font-mono">{{ aiConfig?.model || 'deepseek-v4-flash' }}</dd></div>
            <div><dt class="text-gray-400">配置来源</dt><dd class="mt-1">{{ sourceLabel }}</dd></div>
            <div><dt class="text-gray-400">当前密钥</dt><dd class="mt-1 font-mono">{{ aiConfig?.masked_key || '—' }}</dd></div>
            <div><dt class="text-gray-400">最近更新</dt><dd class="mt-1">{{ formatTime(aiConfig?.updated_at || null) }}</dd></div>
            <div><dt class="text-gray-400">最近验证</dt><dd class="mt-1">{{ formatTime(aiConfig?.validated_at || null) }}</dd></div>
          </dl>
        </div>

        <form class="card" @submit.prevent="saveApiKey">
          <label class="label" for="deepseek-key">新的 API Key</label>
          <input id="deepseek-key" v-model="apiKey" class="input mt-2" type="password" autocomplete="new-password" placeholder="输入后将先验证，再替换当前配置" :disabled="aiLoading" />
          <p class="text-xs text-gray-400 mt-2">系统不会回显或记录明文。验证失败时保留原配置。</p>
          <p v-if="aiMessage" class="text-sm text-green-600 mt-3">{{ aiMessage }}</p>
          <p v-if="aiError" role="alert" class="text-sm text-red-600 mt-3">{{ aiError }}</p>
          <div class="flex flex-wrap gap-2 mt-4">
            <button type="submit" class="btn-primary" :disabled="aiLoading || !apiKey.trim()">{{ aiLoading ? '处理中…' : '验证并保存' }}</button>
            <button type="button" class="btn-outline" :disabled="aiLoading || (!apiKey.trim() && !aiConfig?.configured)" @click="testApiKey">
              {{ apiKey.trim() ? '测试输入的 Key' : '测试当前配置' }}
            </button>
            <button type="button" class="btn-outline text-red-600" :disabled="aiLoading || aiConfig?.source !== 'database'" @click="clearApiKey">清除管理员配置</button>
          </div>
        </form>
      </section>

      <section v-else class="card">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h3 class="font-semibold text-gray-800 dark:text-gray-100">回收站</h3>
            <p class="text-sm text-gray-500 mt-1">数据保留 15 天，到期自动永久清理。</p>
          </div>
          <div class="flex gap-2">
            <select v-model="typeFilter" class="input min-w-[150px]" @change="loadRecycleBin">
              <option value="">全部类型</option>
              <option v-for="(label, value) in typeLabels" :key="value" :value="value">{{ label }}</option>
            </select>
            <button class="btn-outline" :disabled="recycleLoading" @click="loadRecycleBin">刷新</button>
          </div>
        </div>
        <p v-if="recycleError" role="alert" class="text-sm text-red-600 mb-4">{{ recycleError }}</p>
        <div v-if="recycleLoading" class="py-12 text-center text-gray-400">正在加载回收站…</div>
        <div v-else-if="!recycleItems.length" class="py-12 text-center text-gray-400">回收站为空</div>
        <div v-else class="space-y-3">
          <article v-for="entry in recycleItems" :key="entry.id" class="border border-gray-200 dark:border-gray-700 rounded-xl p-4 flex flex-col md:flex-row md:items-center gap-3">
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-800">{{ typeLabels[entry.target_type] }}</span>
                <h4 class="font-medium truncate">{{ entry.display_name }}</h4>
              </div>
              <p class="text-xs text-gray-400 mt-2">删除于 {{ formatTime(entry.deleted_at) }} · 剩余 {{ entry.remaining_days }} 天</p>
            </div>
            <div class="flex gap-2 shrink-0">
              <button class="btn-outline text-sm" :disabled="busyEntries[entry.id]" @click="restoreEntry(entry)">恢复</button>
              <button class="btn-outline text-sm text-red-600" :disabled="busyEntries[entry.id]" @click="purgeEntry(entry)">永久删除</button>
            </div>
          </article>
        </div>
      </section>
    </div>
  </DefaultLayout>
</template>
