<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BrandSelector from '@/components/brand/BrandSelector.vue'
import BrandMemoryCard from '@/components/brand/BrandMemoryCard.vue'
import { brandsApi } from '@/api/brands'
import { knowledgeApi } from '@/api/knowledge'
import type { Brand, BrandProfile } from '@/types'
import { useReturnNavigation } from '@/composables/useReturnNavigation'

const route = useRoute()
const router = useRouter()
const { source, returnLabel, returnToSource } = useReturnNavigation()
const MAX_FILE_SIZE = 10 * 1024 * 1024

const defaultIndustries = ['食品', '医疗', '教育', '汽车', '金融', '美妆', '直播电商']
const industries = ref([...defaultIndustries])
const defaultPlatforms = ['抖音', '小红书', '微信', '微博', '京东', '淘宝', '拼多多']
const platforms = ref([...defaultPlatforms])
const materialTypes = ['文字', '图片', 'PDF文档', 'Word文档', 'PPT演示', 'Excel表格', '视频脚本', '直播话术']
const allowedExtensions = '.jpg,.jpeg,.png,.gif,.bmp,.pdf,.docx,.pptx,.xlsx,.txt'

const form = ref({
  name: '',
  industries: [] as string[],
  platforms: [] as string[],
  material_type: '文字',
  raw_text: '',
  priority: 'normal',
  deadline: null as string | null,
})

const selectedFile = ref<File | null>(null)
const extractedText = ref('')
const previewQuality = ref<'good' | 'degraded' | 'minimal' | null>(null)
const isDragOver = ref(false)
const previewing = ref(false)
const submitting = ref(false)
const error = ref('')
const showMoreSettings = ref(false)
const editMaterialId = ref<string | null>(null)
const isResubmit = ref(false)
const resubmitVersion = ref(0)
const resubmitStatus = ref('')
const loadingEdit = ref(false)

const selectedBrand = ref<Brand | null>(null)
const brands = ref<Brand[]>([])
const brandSearchLoading = ref(false)
const brandSearchError = ref('')
const brandCreating = ref(false)
const brandCreateError = ref('')
const brandProfile = ref<BrandProfile | null>(null)
const brandProfileLoading = ref(false)
const BRAND_STORAGE_KEY = 'lexad-last-brand'

const finalText = computed({
  get: () => extractedText.value || form.value.raw_text,
  set: (val: string) => {
    if (selectedFile.value) extractedText.value = val
    else form.value.raw_text = val
  },
})

const canSubmit = computed(() => {
  return finalText.value.trim() && form.value.industries.length > 0 && form.value.platforms.length > 0 && !submitting.value
})

const orderedIndustries = computed(() => {
  const common = new Set(selectedBrand.value?.industries || [])
  return [...industries.value].sort((a, b) => Number(common.has(b)) - Number(common.has(a)))
})

const qualityLabel = computed(() => {
  if (previewQuality.value === 'good') return { text: '识别质量：良好', cls: 'text-green-600' }
  if (previewQuality.value === 'degraded') return { text: '识别质量：一般，建议核对', cls: 'text-yellow-600' }
  if (previewQuality.value === 'minimal') return { text: '识别质量：较低，请人工核对', cls: 'text-red-500' }
  return null
})

function fileSizeDisplay(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function guessMaterialType(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    jpg: '图片',
    jpeg: '图片',
    png: '图片',
    gif: '图片',
    bmp: '图片',
    pdf: 'PDF文档',
    docx: 'Word文档',
    doc: 'Word文档',
    pptx: 'PPT演示',
    xlsx: 'Excel表格',
    txt: '文字',
  }
  return map[ext] ?? '文字'
}

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) setFile(input.files[0])
  input.value = ''
}

function handleDrop(event: DragEvent) {
  isDragOver.value = false
  if (event.dataTransfer?.files?.[0]) setFile(event.dataTransfer.files[0])
}

function setFile(file: File) {
  const ext = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
  if (!allowedExtensions.includes(ext)) {
    error.value = '不支持的文件格式。支持 JPG / PNG / PDF / DOCX / PPTX / XLSX / TXT'
    return
  }
  if (file.size > MAX_FILE_SIZE) {
    error.value = '文件过大，上限 10MB。请压缩后重试'
    return
  }
  error.value = ''
  selectedFile.value = file
  extractedText.value = ''
  previewQuality.value = null
  form.value.material_type = guessMaterialType(file.name)
  if (!form.value.name) form.value.name = file.name.replace(/\.[^.]+$/, '')
}

function removeFile() {
  selectedFile.value = null
  extractedText.value = ''
  previewQuality.value = null
}

function togglePlatform(platform: string) {
  const index = form.value.platforms.indexOf(platform)
  if (index >= 0) form.value.platforms.splice(index, 1)
  else form.value.platforms.push(platform)
}

function toggleIndustry(industry: string) {
  const index = form.value.industries.indexOf(industry)
  if (index >= 0) form.value.industries.splice(index, 1)
  else form.value.industries.push(industry)
}

async function loadPlatforms() {
  try {
    const response = await knowledgeApi.platforms()
    const activeLabels = response.data.items.map(item => platformDisplayName(item.value, item.label)).filter(Boolean)
    platforms.value = Array.from(new Set([...defaultPlatforms, ...activeLabels]))
  } catch {
    platforms.value = [...defaultPlatforms]
  }
}

async function loadIndustries() {
  try {
    const response = await knowledgeApi.industries()
    industries.value = response.data.items.map(item => item.label || item.value)
  } catch {
    industries.value = [...defaultIndustries]
  }
}

function platformDisplayName(value: string, label: string): string {
  const aliases = `${value} ${label}`.toLowerCase()
  if (/pinduoduo|\bpdd\b|拼多多/.test(aliases)) return '拼多多'
  if (/xiaohongshu|\bxhs\b|小红书/.test(aliases)) return '小红书'
  if (/douyin|抖音/.test(aliases)) return '抖音'
  if (/wechat|weixin|微信/.test(aliases)) return '微信'
  if (/weibo|微博/.test(aliases)) return '微博'
  if (/jingdong|\bjd\b|京东/.test(aliases)) return '京东'
  if (/taobao|\btb\b|淘宝/.test(aliases)) return '淘宝'
  return label || value
}

async function handlePreview() {
  if (!selectedFile.value) return
  previewing.value = true
  error.value = ''
  try {
    const response = await materialsApi.previewText(selectedFile.value)
    extractedText.value = response.data.text
    previewQuality.value = response.data.quality
  } catch (requestError: any) {
    error.value = requestError.response?.data?.detail || '文本提取失败'
  } finally {
    previewing.value = false
  }
}

function autoMaterialName() {
  if (form.value.name.trim()) return form.value.name.trim()
  if (selectedFile.value) return selectedFile.value.name.replace(/\.[^.]+$/, '')
  const summary = finalText.value.trim().slice(0, 24)
  return summary ? `${summary}${finalText.value.trim().length > 24 ? '…' : ''}` : '未命名广告物料'
}

function restoreBrand() {
  const stored = localStorage.getItem(BRAND_STORAGE_KEY)
  if (stored) {
    try { selectedBrand.value = JSON.parse(stored) } catch { /* ignore */ }
  }
}

function persistBrand(brand: Brand | null) {
  if (brand) localStorage.setItem(BRAND_STORAGE_KEY, JSON.stringify(brand))
  else localStorage.removeItem(BRAND_STORAGE_KEY)
}

async function searchBrands(query: string) {
  brandSearchLoading.value = true
  brandSearchError.value = ''
  brandCreateError.value = ''
  try {
    const res = await brandsApi.search(query)
    brands.value = res.data
  } catch (e: any) {
    brandSearchError.value = e.response?.data?.detail || '搜索品牌失败'
  } finally {
    brandSearchLoading.value = false
  }
}

async function createBrand(name: string) {
  if (brandCreating.value) return
  brandCreating.value = true
  brandCreateError.value = ''
  try {
    const res = await brandsApi.create({ name })
    if (res.data.brand) {
      selectedBrand.value = res.data.brand
      persistBrand(res.data.brand)
      await loadBrandProfile(res.data.brand.id)
    }
  } catch (e: any) {
    brandCreateError.value = e.response?.data?.detail || '创建品牌失败'
  } finally {
    brandCreating.value = false
  }
}

function selectBrand(brand: Brand) {
  selectedBrand.value = brand
  persistBrand(brand)
  loadBrandProfile(brand.id)
}

function clearBrand() {
  selectedBrand.value = null
  persistBrand(null)
  brandProfile.value = null
}

async function loadBrandProfile(brandId: string) {
  brandProfileLoading.value = true
  try {
    const res = await brandsApi.profile(brandId)
    brandProfile.value = res.data
  } catch {
    brandProfile.value = null
  } finally {
    brandProfileLoading.value = false
  }
}

onMounted(async () => {
  void loadPlatforms()
  void loadIndustries()
  const editId = route.query.edit as string | undefined
  if (editId) {
    editMaterialId.value = editId
    loadingEdit.value = true
    try {
      const mRes = await materialsApi.get(editId)
      const m = mRes.data
      if (m.status !== 'returned') {
        error.value = '该物料当前状态不允许重新提交'
        return
      }
      isResubmit.value = true
      resubmitVersion.value = m.current_version
      resubmitStatus.value = m.status
      form.value.name = m.name
      form.value.raw_text = m.raw_text
      form.value.industries = m.industry ? m.industry.split('、') : []
      form.value.platforms = m.platforms || []
      form.value.material_type = m.material_type
      form.value.priority = m.priority as string
      form.value.deadline = m.deadline ? m.deadline.slice(0, 16) : null
      if (m.brand_id) {
        const profileRes = await brandsApi.profile(m.brand_id)
        selectedBrand.value = profileRes.data.brand
        brandProfile.value = profileRes.data
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || '加载物料失败'
    } finally {
      loadingEdit.value = false
    }
  }
  if (!isResubmit.value) {
    restoreBrand()
    if (selectedBrand.value) loadBrandProfile(selectedBrand.value.id)
  }
  searchBrands('')
})

async function handleSubmit() {
  error.value = ''
  if (!finalText.value.trim()) {
    error.value = '请上传文件或粘贴广告文案'
    return
  }
  if (!form.value.industries.length) {
    error.value = '请选择至少一个行业'
    return
  }
  if (!form.value.platforms.length) {
    error.value = '请选择至少一个投放平台'
    return
  }

  submitting.value = true
  try {
    if (isResubmit.value && editMaterialId.value) {
      const reviewResponse = await materialsApi.resubmit(editMaterialId.value, {
        name: autoMaterialName(),
        raw_text: finalText.value,
        industry: form.value.industries.join('、'),
        platforms: form.value.platforms,
        material_type: form.value.material_type,
        priority: form.value.priority,
        deadline: form.value.priority === 'normal' ? undefined : form.value.deadline || undefined,
      })
      router.push({ name: 'result', params: { id: reviewResponse.data.id }, query: { from: source.value } })
    } else {
      // New submission
      const fd = new FormData()
      const body = JSON.stringify({
        ...form.value,
        name: autoMaterialName(),
        industry: form.value.industries.join('、'),
        raw_text: finalText.value,
        deadline: form.value.priority === 'normal' ? undefined : form.value.deadline || undefined,
        brand_id: selectedBrand.value?.id || null,
      })
      fd.append('body', body)
      if (selectedFile.value) fd.append('file', selectedFile.value)

      const materialResponse = await materialsApi.submit(fd)
      const reviewResponse = await reviewsApi.aiReview(materialResponse.data.id)
      router.push({ name: 'result', params: { id: reviewResponse.data.id }, query: { from: source.value } })
    }
  } catch (requestError: any) {
    error.value = requestError.response?.data?.detail || '提交失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <DefaultLayout>
    <div class="page-container max-w-3xl">
      <div class="responsive-toolbar mb-6">
        <div>
          <h2 class="page-heading !mb-1">提交广告物料</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400">只需提供物料内容、行业和投放平台即可开始法规与舆情双轴审查。</p>
        </div>
        <button type="button" class="btn-outline text-sm shrink-0" @click="returnToSource()">{{ returnLabel }}</button>
      </div>

        <div v-if="loadingEdit" class="text-gray-400 py-4 text-center">加载物料中...</div>
        <div v-else-if="isResubmit" class="bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800 rounded-lg px-4 py-3 mb-4">
          <p class="text-orange-800 dark:text-orange-200 font-medium">将作为第 {{ resubmitVersion + 1 }} 次提交重新进入审查</p>
          <p class="text-orange-600 dark:text-orange-300 text-sm mt-1">修改后重新提交，系统会使用新版本号进行审查。</p>
        </div>

        <form v-if="!loadingEdit" class="space-y-5" @submit.prevent="handleSubmit">
        <section class="card">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="font-semibold text-gray-800 dark:text-gray-100">1. 物料内容</h3>
              <p class="text-xs text-gray-400 mt-1">可以上传文件，也可以直接粘贴文案。</p>
            </div>
            <span class="text-xs text-gray-400">支持最大 10MB</span>
          </div>

          <div
            class="mt-4 border-2 border-dashed rounded-xl p-6 text-center transition-colors min-w-0"
            :class="isDragOver ? 'border-sky-500 bg-sky-50 dark:bg-sky-950/30' : 'border-gray-300 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/60'"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleDrop"
          >
            <template v-if="!selectedFile">
              <p class="text-gray-700 dark:text-gray-200 font-medium">拖拽文件到这里，或点击选择文件</p>
              <p class="text-gray-400 text-xs mt-1">JPG / PNG / GIF / BMP / PDF / DOCX / PPTX / XLSX / TXT</p>
              <input type="file" :accept="allowedExtensions" class="mt-4 text-sm" @change="handleFileSelect" />
            </template>
            <template v-else>
              <p class="text-sm font-medium text-gray-800 dark:text-gray-100">{{ selectedFile.name }}</p>
              <p class="text-xs text-gray-400 mt-1">{{ fileSizeDisplay(selectedFile.size) }} · {{ form.material_type }}</p>
              <div class="flex items-center justify-center gap-3 mt-4">
                <button type="button" class="btn-outline text-sm" :disabled="previewing" @click="handlePreview">
                  {{ previewing ? '提取中…' : '预览提取文本' }}
                </button>
                <button type="button" class="text-sm text-red-500 hover:underline" @click="removeFile">
                  移除
                </button>
              </div>
            </template>
          </div>

          <div class="mt-4">
            <div class="flex items-center justify-between mb-1">
              <label class="label !mb-0">广告文案内容</label>
              <span v-if="qualityLabel" :class="qualityLabel.cls" class="text-xs">{{ qualityLabel.text }}</span>
            </div>
            <textarea
              v-model="finalText"
              class="input min-h-44 resize-y"
              placeholder="粘贴广告文案全文。上传文件后，也可以在这里核对和修改提取文本。"
            />
          </div>
        </section>

        <!-- Brand selection -->
        <section class="card">
          <div v-if="isResubmit" class="rounded-xl border border-sky-200 dark:border-sky-800 bg-sky-50/70 dark:bg-sky-950/30 p-4">
            <p class="text-xs font-semibold text-sky-700 dark:text-sky-300">本物料品牌已锁定</p>
            <p class="mt-1 font-medium text-gray-800 dark:text-gray-100">{{ selectedBrand?.name || '未关联品牌' }}</p>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">重新提交会保持首次品牌归属，不能新增、清空或更换品牌。</p>
          </div>
          <BrandSelector
            v-else
            :model-value="selectedBrand"
            :brands="brands"
            :loading="brandSearchLoading"
            :error="brandSearchError"
            :creating="brandCreating"
            :create-error="brandCreateError"
            @update:model-value="(b: Brand | null) => { if (b) selectBrand(b); else clearBrand(); }"
            @search="searchBrands"
            @create="createBrand"
          />
          <BrandMemoryCard
            :profile="brandProfile"
            :loading="brandProfileLoading"
          />
        </section>

        <section class="card">
          <h3 class="font-semibold text-gray-800 dark:text-gray-100">2. 行业（可多选）</h3>
          <p class="text-xs text-gray-400 mt-1">可选择多个相关行业。系统会按多行业匹配法律规则、行业规则和舆情案例。</p>
          <div class="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            <button
              v-for="industry in orderedIndustries"
              :key="industry"
              type="button"
              class="btn text-sm border break-words"
              :class="form.industries.includes(industry) ? 'bg-sky-600 text-white border-sky-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-sky-50 dark:bg-gray-900 dark:text-gray-300 dark:border-gray-700 dark:hover:bg-gray-800'"
              @click="toggleIndustry(industry)"
            >
              <span>{{ industry }}</span>
              <span v-if="selectedBrand?.industries?.includes(industry)" class="ml-1 text-[10px] opacity-80">品牌常用</span>
            </button>
          </div>
        </section>

        <section class="card">
          <h3 class="font-semibold text-gray-800 dark:text-gray-100">3. 投放平台</h3>
          <p class="text-xs text-gray-400 mt-1">系统会按平台规则版本执行 L4 审核，并固定本次审核快照。</p>
          <div class="mt-4 flex flex-wrap gap-2">
            <button
              v-for="platform in platforms"
              :key="platform"
              type="button"
              :class="form.platforms.includes(platform) ? 'btn-primary text-sm' : 'btn-outline text-sm'"
              @click="togglePlatform(platform)"
            >
              {{ platform }}
            </button>
          </div>
        </section>

        <section class="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <button
            type="button"
            class="w-full px-5 py-4 flex items-center justify-between text-left"
            @click="showMoreSettings = !showMoreSettings"
          >
            <span>
              <span class="block font-semibold text-gray-800 dark:text-gray-100">更多设置</span>
              <span class="block text-xs text-gray-400 mt-1">物料名称、类型、优先级和截止时间。可不填写。</span>
            </span>
            <span class="text-sm text-sky-600">{{ showMoreSettings ? '收起' : '展开' }}</span>
          </button>
          <div v-if="showMoreSettings" class="px-5 pb-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label>
              <span class="label">物料名称</span>
              <input v-model="form.name" class="input" placeholder="不填则自动生成" />
            </label>
            <label>
              <span class="label">物料类型</span>
              <select v-model="form.material_type" class="input">
                <option v-for="type in materialTypes" :key="type" :value="type">{{ type }}</option>
              </select>
            </label>
            <label>
              <span class="label">优先级</span>
              <select v-model="form.priority" class="input">
                <option value="normal">普通</option>
                <option value="urgent">加急（24h）</option>
                <option value="extreme">极速（4h）</option>
              </select>
            </label>
            <label v-if="form.priority !== 'normal'">
              <span class="label">截止时间</span>
              <input v-model="form.deadline" type="datetime-local" class="input" />
            </label>
          </div>
        </section>

        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>

        <button type="submit" :disabled="!canSubmit" class="btn-primary w-full min-h-12">
          {{ submitting ? (isResubmit ? '重新提交并审查中…' : '提交并审查中…') : (isResubmit ? '修改并重新审查' : '开始自动审查') }}
        </button>
      </form>
    </div>
  </DefaultLayout>
</template>
