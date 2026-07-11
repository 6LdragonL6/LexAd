<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import {
  adminKnowledgeApi,
  type KnowledgeAuditLog,
  type KnowledgeImportJob,
  type PlatformRuleSetDetail,
  type PublicOpinionEvent,
  type PublicOpinionEventDetail,
} from '@/api/adminKnowledge'

type TabKey = 'public-opinion' | 'platform-rules' | 'imports' | 'audit'

const tabs: { key: TabKey; label: string; description: string }[] = [
  { key: 'public-opinion', label: '舆情事件', description: '录入、整理、发布和归档案例' },
  { key: 'platform-rules', label: '平台规则', description: '维护平台规则版本和回滚' },
  { key: 'imports', label: '导入记录', description: '查看 JSON 预检和导入任务' },
  { key: 'audit', label: '审计日志', description: '追踪管理员资料操作' },
]

const activeTab = ref<TabKey>('public-opinion')
const loading = ref(false)
const error = ref('')
const notice = ref('')

const events = ref<PublicOpinionEvent[]>([])
const selectedEventId = ref('')
const selectedEvent = ref<PublicOpinionEventDetail | null>(null)
const eventFilter = ref('')
const showImportTools = ref(false)
const eventForm = ref({
  external_id: '',
  title: '',
  source_text: '',
  consequence_text: '',
  source_name: '',
  source_url: '',
  occurred_at: '',
})

const importText = ref('')
const importPreview = ref<KnowledgeImportJob | null>(null)
const importRunStructure = ref(false)

const platformRules = ref<PlatformRuleSetDetail[]>([])
const selectedRuleSetId = ref('')
const ruleSetForm = ref({
  platform_name: '',
  display_name: '',
  description: '',
})
const ruleVersionForm = ref({
  version_label: '',
  source_name: '',
  source_url: '',
  effective_at: '',
  raw_text: '',
  structured_rules: '[\n  {\n    "rule_id": "rule-001",\n    "text": "规则说明",\n    "keywords": ["触发关键词"],\n    "risk_level": "平台规则"\n  }\n]',
})

const importJobs = ref<KnowledgeImportJob[]>([])
const auditLogs = ref<KnowledgeAuditLog[]>([])

const selectedRuleSet = computed(() => platformRules.value.find((item) => item.rule_set.id === selectedRuleSetId.value) || null)
const selectedEventLatestVersion = computed(() => selectedEvent.value?.versions?.[0] || null)

function statusText(status: string) {
  const map: Record<string, string> = {
    draft: '草稿',
    ai_processing: 'AI 整理中',
    pending_review: '待复核',
    published: '已发布',
    archived: '已归档',
    active: '生效中',
    expired: '已失效',
    uploaded: '已上传',
    validated: '预检通过',
    validation_failed: '预检有错误',
    importing: '导入中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function statusClass(status: string) {
  if (['published', 'active', 'completed', 'validated'].includes(status)) return 'bg-green-100 text-green-700'
  if (['archived', 'expired'].includes(status)) return 'bg-gray-100 text-gray-600'
  if (['validation_failed', 'failed'].includes(status)) return 'bg-red-100 text-red-600'
  return 'bg-yellow-100 text-yellow-700'
}

function formatDate(value: string | null | undefined) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function showError(requestError: any, fallback: string) {
  error.value = requestError.response?.data?.detail || fallback
}

function clearMessage() {
  error.value = ''
  notice.value = ''
}

async function loadEvents() {
  const response = await adminKnowledgeApi.listPublicOpinionEvents({ keyword: eventFilter.value || undefined })
  events.value = response.data.items
  if (!selectedEventId.value && events.value.length) selectedEventId.value = events.value[0].id
  if (selectedEventId.value) await loadEventDetail(selectedEventId.value)
}

async function loadEventDetail(id: string) {
  selectedEventId.value = id
  const response = await adminKnowledgeApi.getPublicOpinionEvent(id)
  selectedEvent.value = response.data
}

async function createEvent() {
  clearMessage()
  loading.value = true
  try {
    const response = await adminKnowledgeApi.createPublicOpinionEvent({
      external_id: eventForm.value.external_id || null,
      title: eventForm.value.title,
      source_text: eventForm.value.source_text,
      consequence_text: eventForm.value.consequence_text,
      source_meta: {
        sources: eventForm.value.source_name || eventForm.value.source_url
          ? [{ name: eventForm.value.source_name, url: eventForm.value.source_url }]
          : [],
        occurred_at: eventForm.value.occurred_at || null,
      },
    })
    notice.value = '舆情案例已保存为草稿。可以继续点击“AI 帮我整理事件”，再人工复核发布。'
    selectedEventId.value = response.data.id
    eventForm.value = { external_id: '', title: '', source_text: '', consequence_text: '', source_name: '', source_url: '', occurred_at: '' }
    await loadEvents()
  } catch (requestError: any) {
    showError(requestError, '舆情案例保存失败')
  } finally {
    loading.value = false
  }
}

async function structureEvent(id: string) {
  clearMessage()
  loading.value = true
  try {
    await adminKnowledgeApi.structurePublicOpinionEvent(id)
    notice.value = '系统已整理事件，请复核黄色/不确定字段后再发布。'
    await loadEventDetail(id)
    await loadEvents()
  } catch (requestError: any) {
    showError(requestError, 'AI 整理失败')
  } finally {
    loading.value = false
  }
}

async function publishEvent(id: string) {
  clearMessage()
  loading.value = true
  try {
    await adminKnowledgeApi.publishPublicOpinionEvent(id)
    notice.value = '舆情案例已发布，将进入后续审核任务的资料库。'
    await loadEvents()
  } catch (requestError: any) {
    showError(requestError, '发布失败')
  } finally {
    loading.value = false
  }
}

async function archiveEvent(id: string) {
  if (!window.confirm('确认归档该案例？归档后新审核不再检索该案例，历史审核仍可追溯。')) return
  clearMessage()
  loading.value = true
  try {
    await adminKnowledgeApi.archivePublicOpinionEvent(id)
    notice.value = '舆情案例已归档。'
    await loadEvents()
  } catch (requestError: any) {
    showError(requestError, '归档失败')
  } finally {
    loading.value = false
  }
}

async function restoreEvent(id: string) {
  clearMessage()
  loading.value = true
  try {
    await adminKnowledgeApi.restorePublicOpinionEvent(id)
    notice.value = '舆情案例已恢复发布。'
    await loadEvents()
  } catch (requestError: any) {
    showError(requestError, '恢复失败')
  } finally {
    loading.value = false
  }
}

async function deleteDraft(id: string) {
  if (!window.confirm('确认删除该草稿？已发布案例不能物理删除。')) return
  clearMessage()
  loading.value = true
  try {
    await adminKnowledgeApi.deletePublicOpinionEvent(id)
    notice.value = '草稿已删除。'
    selectedEventId.value = ''
    selectedEvent.value = null
    await loadEvents()
  } catch (requestError: any) {
    showError(requestError, '删除失败')
  } finally {
    loading.value = false
  }
}

async function loadImportTemplate() {
  clearMessage()
  try {
    const response = await adminKnowledgeApi.getPublicOpinionImportTemplate()
    importText.value = JSON.stringify(response.data, null, 2)
    notice.value = '模板已填入文本框。普通录入不需要使用 JSON；批量导入时再使用。'
  } catch (requestError: any) {
    showError(requestError, '模板加载失败')
  }
}

async function previewImport() {
  clearMessage()
  loading.value = true
  try {
    const payload = JSON.parse(importText.value)
    const response = await adminKnowledgeApi.previewPublicOpinionImport(payload)
    importPreview.value = response.data
    notice.value = response.data.invalid_items
      ? '预检完成：存在需要修复的记录。合格记录可导入为草稿。'
      : '预检通过：可以确认导入为草稿。'
    await loadImports()
  } catch (requestError: any) {
    if (requestError instanceof SyntaxError) error.value = 'JSON 格式无法识别，请检查括号、逗号和引号。'
    else showError(requestError, '预检失败')
  } finally {
    loading.value = false
  }
}

async function confirmImport() {
  if (!importPreview.value) return
  clearMessage()
  loading.value = true
  try {
    const duplicateActions: Record<string, string> = {}
    const duplicates = importPreview.value.error_summary?.duplicate_external_ids || []
    duplicates.forEach((id: string) => { duplicateActions[id] = 'skip' })
    await adminKnowledgeApi.confirmPublicOpinionImport(importPreview.value.id, {
      duplicate_actions: duplicateActions,
      run_structure: importRunStructure.value,
    })
    notice.value = '合格记录已导入为草稿。请逐条复核后发布。'
    importPreview.value = null
    await Promise.all([loadEvents(), loadImports()])
  } catch (requestError: any) {
    showError(requestError, '确认导入失败')
  } finally {
    loading.value = false
  }
}

async function loadPlatformRules() {
  const response = await adminKnowledgeApi.listPlatformRules()
  platformRules.value = response.data.items
  if (!selectedRuleSetId.value && platformRules.value.length) selectedRuleSetId.value = platformRules.value[0].rule_set.id
}

async function createRuleSet() {
  clearMessage()
  loading.value = true
  try {
    const response = await adminKnowledgeApi.createPlatformRuleSet(ruleSetForm.value)
    notice.value = '平台规则集已创建。接下来添加规则版本并启用。'
    selectedRuleSetId.value = response.data.id
    ruleSetForm.value = { platform_name: '', display_name: '', description: '' }
    await loadPlatformRules()
  } catch (requestError: any) {
    showError(requestError, '平台规则集创建失败')
  } finally {
    loading.value = false
  }
}

async function createRuleVersion() {
  if (!selectedRuleSetId.value) return
  clearMessage()
  loading.value = true
  try {
    const structuredRules = JSON.parse(ruleVersionForm.value.structured_rules || '[]')
    await adminKnowledgeApi.createPlatformRuleVersion(selectedRuleSetId.value, {
      version_label: ruleVersionForm.value.version_label,
      source_name: ruleVersionForm.value.source_name,
      source_url: ruleVersionForm.value.source_url,
      effective_at: ruleVersionForm.value.effective_at || null,
      raw_text: ruleVersionForm.value.raw_text,
      structured_rules: structuredRules,
    })
    notice.value = '平台规则版本已保存为草稿。确认无误后可启用。'
    ruleVersionForm.value = {
      version_label: '',
      source_name: '',
      source_url: '',
      effective_at: '',
      raw_text: '',
      structured_rules: '[\n  {\n    "rule_id": "rule-001",\n    "text": "规则说明",\n    "keywords": ["触发关键词"],\n    "risk_level": "平台规则"\n  }\n]',
    }
    await loadPlatformRules()
  } catch (requestError: any) {
    if (requestError instanceof SyntaxError) error.value = '结构化规则不是有效 JSON。'
    else showError(requestError, '平台规则版本创建失败')
  } finally {
    loading.value = false
  }
}

async function activateRuleVersion(id: string, rollback = false) {
  const text = rollback ? '确认回滚到该版本？' : '确认启用该版本？同平台其他生效版本会失效。'
  if (!window.confirm(text)) return
  clearMessage()
  loading.value = true
  try {
    if (rollback) await adminKnowledgeApi.rollbackPlatformRuleVersion(id)
    else await adminKnowledgeApi.activatePlatformRuleVersion(id)
    notice.value = rollback ? '平台规则已回滚。' : '平台规则版本已启用。'
    await loadPlatformRules()
  } catch (requestError: any) {
    showError(requestError, rollback ? '回滚失败' : '启用失败')
  } finally {
    loading.value = false
  }
}

async function loadImports() {
  const response = await adminKnowledgeApi.listImportJobs()
  importJobs.value = response.data
}

async function loadAuditLogs() {
  const response = await adminKnowledgeApi.listAuditLogs()
  auditLogs.value = response.data
}

async function loadAll() {
  loading.value = true
  clearMessage()
  try {
    await Promise.all([loadEvents(), loadPlatformRules(), loadImports(), loadAuditLogs()])
  } catch (requestError: any) {
    showError(requestError, '资料中心加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <DefaultLayout>
    <div class="page-container max-w-7xl">
      <div class="responsive-toolbar mb-6">
        <div>
          <h2 class="page-heading !mb-1">管理员资料中心</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400">维护舆情案例、平台规则版本、导入记录和审计日志。所有写操作仅管理员可用。</p>
        </div>
        <button class="btn-outline text-sm shrink-0" :disabled="loading" @click="loadAll">刷新资料</button>
      </div>

      <div v-if="notice" class="mb-4 rounded-xl border border-green-200 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 px-4 py-3 text-sm">
        {{ notice }}
      </div>
      <div v-if="error" class="mb-4 rounded-xl border border-red-200 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 px-4 py-3 text-sm">
        {{ error }}
      </div>

      <div class="card !p-0 overflow-hidden">
        <div class="flex overflow-x-auto border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="min-w-36 px-4 py-3 text-left border-b-2 transition-colors"
            :class="activeTab === tab.key ? 'border-sky-500 bg-white dark:bg-gray-900 text-sky-700 dark:text-sky-400' : 'border-transparent text-gray-500 dark:text-gray-400 hover:bg-white dark:hover:bg-gray-900'"
            @click="activeTab = tab.key"
          >
            <span class="block text-sm font-semibold">{{ tab.label }}</span>
            <span class="block text-xs mt-0.5">{{ tab.description }}</span>
          </button>
        </div>

        <section v-if="activeTab === 'public-opinion'" class="p-4 lg:p-6">
          <div class="grid grid-cols-1 xl:grid-cols-[420px_minmax(0,1fr)] gap-6">
            <div class="space-y-4">
              <div class="rounded-xl border border-sky-100 dark:border-sky-900 bg-sky-50 dark:bg-sky-900/20 p-4">
                <h3 class="font-semibold text-gray-800 dark:text-gray-200">新增舆情案例</h3>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">普通管理员只需要描述事件和后果，不需要理解 JSON。</p>
                <div class="mt-4 space-y-3">
                  <label class="block">
                    <span class="label">事件标题</span>
                    <input v-model="eventForm.title" class="input" placeholder="例如：某品牌广告引发消费者尊重争议" />
                  </label>
                  <label class="block">
                    <span class="label">这件事发生了什么</span>
                    <textarea v-model="eventForm.source_text" class="input min-h-32" placeholder="粘贴新闻、内部记录或自然语言说明" />
                  </label>
                  <label class="block">
                    <span class="label">造成了什么后果</span>
                    <textarea v-model="eventForm.consequence_text" class="input min-h-24" placeholder="描述声誉、业务、监管或其他影响" />
                  </label>
                  <details class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
                    <summary class="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300">可选信息</summary>
                    <div class="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <input v-model="eventForm.external_id" class="input" placeholder="外部编号" />
                      <input v-model="eventForm.occurred_at" class="input" type="date" />
                      <input v-model="eventForm.source_name" class="input" placeholder="来源名称" />
                      <input v-model="eventForm.source_url" class="input" placeholder="来源链接" />
                    </div>
                  </details>
                  <button class="btn-primary w-full" :disabled="loading || !eventForm.source_text.trim()" @click="createEvent">
                    保存为草稿
                  </button>
                </div>
              </div>

              <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                <div class="flex items-center justify-between gap-2">
                  <h3 class="font-semibold text-gray-800 dark:text-gray-200">舆情资料库</h3>
                  <span class="text-xs text-gray-400 dark:text-gray-500">{{ events.length }} 条</span>
                </div>
                <input v-model="eventFilter" class="input mt-3" placeholder="按关键词搜索" @keyup.enter="loadEvents" />
                <div class="mt-3 max-h-96 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700">
                  <button
                    v-for="event in events"
                    :key="event.id"
                    class="w-full text-left py-3 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                    :class="selectedEventId === event.id ? 'bg-sky-50 dark:bg-sky-900/20' : ''"
                    @click="loadEventDetail(event.id)"
                  >
                    <span class="block font-medium text-gray-800 dark:text-gray-200 truncate">{{ event.title || '未命名案例' }}</span>
                    <span class="mt-1 inline-flex px-2 py-0.5 rounded-full text-xs" :class="statusClass(event.status)">
                      {{ statusText(event.status) }}
                    </span>
                    <span class="ml-2 text-xs text-gray-400">{{ formatDate(event.updated_at) }}</span>
                  </button>
                </div>
              </div>
            </div>

            <div class="min-w-0">
              <div v-if="selectedEvent" class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 lg:p-5">
                <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                  <div>
                    <span class="inline-flex px-2 py-0.5 rounded-full text-xs" :class="statusClass(selectedEvent.event.status)">
                      {{ statusText(selectedEvent.event.status) }}
                    </span>
                    <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mt-2">{{ selectedEvent.event.title || '未命名案例' }}</h3>
                    <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">更新时间：{{ formatDate(selectedEvent.event.updated_at) }}</p>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <button class="btn-outline text-sm" :disabled="loading" @click="structureEvent(selectedEvent.event.id)">AI 帮我整理事件</button>
                    <button v-if="selectedEvent.event.status !== 'published'" class="btn-primary text-sm" :disabled="loading" @click="publishEvent(selectedEvent.event.id)">发布</button>
                    <button v-if="selectedEvent.event.status === 'published'" class="btn-outline text-sm" :disabled="loading" @click="archiveEvent(selectedEvent.event.id)">归档</button>
                    <button v-if="selectedEvent.event.status === 'archived'" class="btn-outline text-sm" :disabled="loading" @click="restoreEvent(selectedEvent.event.id)">恢复</button>
                    <button v-if="selectedEvent.event.status === 'draft'" class="btn-danger text-sm" :disabled="loading" @click="deleteDraft(selectedEvent.event.id)">删除草稿</button>
                  </div>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-5">
                  <div>
                    <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">事件材料</h4>
                    <p class="rounded-lg bg-gray-50 dark:bg-gray-700 p-3 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{{ selectedEvent.event.source_text || '暂无' }}</p>
                  </div>
                  <div>
                    <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">后果描述</h4>
                    <p class="rounded-lg bg-gray-50 dark:bg-gray-700 p-3 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{{ selectedEvent.event.consequence_text || '暂无' }}</p>
                  </div>
                </div>

                <div class="mt-5">
                  <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">系统整理结果</h4>
                  <div v-if="selectedEventLatestVersion" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
                      <p class="text-xs text-gray-400 dark:text-gray-500">摘要</p>
                      <p class="text-sm text-gray-700 dark:text-gray-300 mt-1">{{ selectedEventLatestVersion.summary || '暂无摘要' }}</p>
                    </div>
                    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
                      <p class="text-xs text-gray-400 dark:text-gray-500">风险议题</p>
                      <p class="text-sm text-gray-700 dark:text-gray-300 mt-1">{{ selectedEventLatestVersion.risk_topics?.join('、') || '待补充' }}</p>
                    </div>
                    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
                      <p class="text-xs text-gray-400 dark:text-gray-500">受影响群体</p>
                      <p class="text-sm text-gray-700 dark:text-gray-300 mt-1">{{ selectedEventLatestVersion.affected_groups?.join('、') || '待补充' }}</p>
                    </div>
                    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
                      <p class="text-xs text-gray-400 dark:text-gray-500">置信度 / 整理方式</p>
                      <p class="text-sm text-gray-700 dark:text-gray-300 mt-1">{{ selectedEventLatestVersion.confidence ?? 0 }} / {{ selectedEventLatestVersion.model_name }}</p>
                    </div>
                  </div>
                  <p v-else class="rounded-lg bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400 p-3 text-sm">尚未整理。点击“AI 帮我整理事件”后再人工复核。</p>
                </div>
              </div>
              <div v-else class="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-10 text-center text-gray-400 dark:text-gray-500">
                请选择一个舆情案例，或先新增草稿。
              </div>

              <div class="mt-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                <button class="text-sm font-semibold text-sky-700 dark:text-sky-400" @click="showImportTools = !showImportTools">
                  {{ showImportTools ? '收起更多工具' : '更多工具：JSON 批量导入' }}
                </button>
                <div v-if="showImportTools" class="mt-4 space-y-3">
                  <div class="flex flex-wrap gap-2">
                    <button class="btn-outline text-sm" @click="loadImportTemplate">填入模板</button>
                    <button class="btn-outline text-sm" :disabled="!importText.trim()" @click="previewImport">预检 JSON</button>
                    <button class="btn-primary text-sm" :disabled="!importPreview" @click="confirmImport">确认导入为草稿</button>
                    <label class="inline-flex items-center gap-2 text-sm text-gray-600">
                      <input v-model="importRunStructure" type="checkbox" />
                      导入后自动整理
                    </label>
                  </div>
                  <textarea v-model="importText" class="input font-mono text-xs min-h-64" placeholder="将舆情 JSON 粘贴到这里。普通录入不需要使用该工具。" />
                  <div v-if="importPreview" class="rounded-lg bg-gray-50 dark:bg-gray-700 p-3 text-sm text-gray-700 dark:text-gray-300">
                    <p>预检结果：{{ statusText(importPreview.status) }}；总计 {{ importPreview.total_items }}，合格 {{ importPreview.valid_items }}，需修复 {{ importPreview.invalid_items }}</p>
                    <pre v-if="importPreview.error_summary" class="mt-2 text-xs whitespace-pre-wrap text-gray-700 dark:text-gray-300">{{ JSON.stringify(importPreview.error_summary, null, 2) }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section v-else-if="activeTab === 'platform-rules'" class="p-4 lg:p-6">
          <div class="grid grid-cols-1 xl:grid-cols-[380px_minmax(0,1fr)] gap-6">
            <div class="space-y-4">
              <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                <h3 class="font-semibold text-gray-800 dark:text-gray-200">新增平台规则集</h3>
                <div class="mt-3 space-y-3">
                  <input v-model="ruleSetForm.platform_name" class="input" placeholder="平台标识，例如抖音" />
                  <input v-model="ruleSetForm.display_name" class="input" placeholder="显示名称，例如 抖音" />
                  <textarea v-model="ruleSetForm.description" class="input min-h-20" placeholder="规则集说明" />
                  <button class="btn-primary w-full" :disabled="loading || !ruleSetForm.platform_name || !ruleSetForm.display_name" @click="createRuleSet">创建规则集</button>
                </div>
              </div>

              <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                <h3 class="font-semibold text-gray-800 dark:text-gray-200">平台列表</h3>
                <div class="mt-3 divide-y divide-gray-100 dark:divide-gray-700">
                  <button
                    v-for="item in platformRules"
                    :key="item.rule_set.id"
                    class="w-full text-left py-3 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                    :class="selectedRuleSetId === item.rule_set.id ? 'bg-sky-50 dark:bg-sky-900/20' : ''"
                    @click="selectedRuleSetId = item.rule_set.id"
                  >
                    <span class="block font-medium text-gray-800 dark:text-gray-200">{{ item.rule_set.display_name }}</span>
                    <span class="text-xs text-gray-400 dark:text-gray-500">{{ item.rule_set.platform_name }}</span>
                    <span v-if="item.active_version" class="ml-2 inline-flex px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs">
                      当前 {{ item.active_version.version_label }}
                    </span>
                  </button>
                </div>
              </div>
            </div>

            <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 lg:p-5">
              <div v-if="selectedRuleSet">
                <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                  <div>
                    <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-200">{{ selectedRuleSet.rule_set.display_name }}</h3>
                    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ selectedRuleSet.rule_set.description || '暂无说明' }}</p>
                  </div>
                  <span class="text-xs text-gray-400 dark:text-gray-500">版本数：{{ selectedRuleSet.versions.length }}</span>
                </div>

                <div class="mt-5 rounded-xl border border-sky-100 dark:border-sky-900 bg-sky-50 dark:bg-sky-900/20 p-4">
                  <h4 class="font-semibold text-gray-800 dark:text-gray-200">新增规则版本</h4>
                  <div class="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-3">
                    <input v-model="ruleVersionForm.version_label" class="input" placeholder="版本号，例如 2026-07" />
                    <input v-model="ruleVersionForm.effective_at" class="input" type="datetime-local" />
                    <input v-model="ruleVersionForm.source_name" class="input" placeholder="来源名称" />
                    <input v-model="ruleVersionForm.source_url" class="input" placeholder="来源链接" />
                    <textarea v-model="ruleVersionForm.raw_text" class="input min-h-28 lg:col-span-2" placeholder="规则正文" />
                    <textarea v-model="ruleVersionForm.structured_rules" class="input min-h-40 font-mono text-xs lg:col-span-2" />
                  </div>
                  <button class="btn-primary mt-3" :disabled="loading || !ruleVersionForm.version_label" @click="createRuleVersion">保存版本草稿</button>
                </div>

                <div class="mt-5">
                  <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">版本历史</h4>
                  <div class="space-y-3">
                    <div v-for="version in selectedRuleSet.versions" :key="version.id" class="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                      <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                        <div>
                          <span class="inline-flex px-2 py-0.5 rounded-full text-xs" :class="statusClass(version.status)">
                            {{ statusText(version.status) }}
                          </span>
                          <h5 class="font-semibold text-gray-800 dark:text-gray-200 mt-2">{{ version.version_label }}</h5>
                          <p class="text-xs text-gray-400 dark:text-gray-500">创建：{{ formatDate(version.created_at) }}；启用：{{ formatDate(version.activated_at) }}</p>
                        </div>
                        <div class="flex flex-wrap gap-2">
                          <button v-if="version.status !== 'active'" class="btn-outline text-sm" @click="activateRuleVersion(version.id)">启用</button>
                          <button v-if="version.status !== 'active'" class="btn-outline text-sm" @click="activateRuleVersion(version.id, true)">回滚到此版本</button>
                        </div>
                      </div>
                      <div class="mt-3 text-xs text-gray-500 dark:text-gray-400">
                        差异：新增 {{ version.diff_summary?.added_count || 0 }}，修改 {{ version.diff_summary?.changed_count || 0 }}，删除 {{ version.diff_summary?.removed_count || 0 }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <p v-else class="py-20 text-center text-gray-400 dark:text-gray-500">请先创建或选择平台规则集。</p>
            </div>
          </div>
        </section>

        <section v-else-if="activeTab === 'imports'" class="p-4 lg:p-6">
          <div class="table-scroll">
            <table class="min-w-full text-sm">
              <thead class="bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                <tr>
                  <th class="text-left px-3 py-2">文件</th>
                  <th class="text-left px-3 py-2">状态</th>
                  <th class="text-left px-3 py-2">总数</th>
                  <th class="text-left px-3 py-2">合格</th>
                  <th class="text-left px-3 py-2">需修复</th>
                  <th class="text-left px-3 py-2">时间</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                <tr v-for="job in importJobs" :key="job.id">
                  <td class="px-3 py-3 text-gray-700 dark:text-gray-300">{{ job.file_name }}</td>
                  <td class="px-3 py-3"><span class="px-2 py-0.5 rounded-full text-xs" :class="statusClass(job.status)">{{ statusText(job.status) }}</span></td>
                  <td class="px-3 py-3 text-gray-700 dark:text-gray-300">{{ job.total_items }}</td>
                  <td class="px-3 py-3 text-gray-700 dark:text-gray-300">{{ job.valid_items }}</td>
                  <td class="px-3 py-3 text-gray-700 dark:text-gray-300">{{ job.invalid_items }}</td>
                  <td class="px-3 py-3 text-gray-400 dark:text-gray-500">{{ formatDate(job.created_at) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="!importJobs.length" class="py-16 text-center text-gray-400 dark:text-gray-500">暂无导入记录。</p>
          </div>
        </section>

        <section v-else class="p-4 lg:p-6">
          <div class="space-y-3">
            <div v-for="log in auditLogs" :key="log.id" class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
              <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2">
                <div>
                  <span class="text-sm font-semibold text-gray-800 dark:text-gray-200">{{ log.action }}</span>
                  <span class="ml-2 text-xs text-gray-400 dark:text-gray-500">{{ log.target_type }} / {{ log.target_id }}</span>
                </div>
                <span class="text-xs text-gray-400 dark:text-gray-500">{{ formatDate(log.created_at) }}</span>
              </div>
              <details class="mt-2">
                <summary class="cursor-pointer text-xs text-sky-600">查看变更内容</summary>
                <pre class="mt-2 rounded-lg bg-gray-50 dark:bg-gray-700 p-3 text-xs whitespace-pre-wrap text-gray-700 dark:text-gray-300">{{ JSON.stringify({ before: log.before_state, after: log.after_state }, null, 2) }}</pre>
              </details>
            </div>
            <p v-if="!auditLogs.length" class="py-16 text-center text-gray-400 dark:text-gray-500">暂无审计日志。</p>
          </div>
        </section>
      </div>
    </div>
  </DefaultLayout>
</template>
