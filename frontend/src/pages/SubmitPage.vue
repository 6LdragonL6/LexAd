<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BrandSelector from '@/components/brand/BrandSelector.vue'
import BrandMemoryCard from '@/components/brand/BrandMemoryCard.vue'
import { brandsApi } from '@/api/brands'
import type { Brand, BrandProfile } from '@/types'

const route = useRoute()
const router = useRouter()
const MAX_FILE_SIZE = 10 * 1024 * 1024

const industries = ['食品', '医疗', '教育', '汽车', '金融', '美妆', '直播电商']
const platforms = ['抖音', '小红书', '微信', '微博', '京东', '淘宝']
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
  brandSearchError.value = ''
  try {
    const res = await brandsApi.create({ name })
    if (res.data.brand) {
      selectedBrand.value = res.data.brand
      persistBrand(res.data.brand)
      await loadBrandProfile(res.data.brand.id)
    }
  } catch (e: any) {
    brandSearchError.value = e.response?.data?.detail || '创建品牌失败'
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
    } catch (e: any) {
      error.value = e.response?.data?.detail || '加载物料失败'
    } finally {
      loadingEdit.value = false
    }
  }
  restoreBrand()
  if (selectedBrand.value) {
    loadBrandProfile(selectedBrand.value.id)
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
      // Resubmit: update existing material then trigger AI review
      await materialsApi.update(editMaterialId.value, {
        name: autoMaterialName(),
        raw_text: finalText.value,
        industry: form.value.industries.join('、'),
        platforms: form.value.platforms,
        priority: form.value.priority,
        deadline: form.value.priority === 'normal' ? undefined : form.value.deadline || undefined,
        brand_id: selectedBrand.value?.id || null,
      })
      const reviewResponse = await reviewsApi.aiReview(editMaterialId.value)
      router.push(`/result/${reviewResponse.data.id}`)
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
      router.push(`/result/${reviewResponse.data.id}`)
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
          <p class="text-sm text-gray-500">只需提供物料内容、行业和投放平台即可开始法律与舆情双轴风险审查。</p>
        </div>
      </div>

        <div v-if="loadingEdit" class="text-gray-400 py-4 text-center">加载物料中...</div>
        <div v-else-if="isResubmit" class="bg-orange-50 border border-orange-200 rounded-lg px-4 py-3 mb-4">
          <p class="text-orange-800 font-medium">将作为第 {{ resubmitVersion + 1 }} 次提交重新进入审查</p>
          <p class="text-orange-600 text-sm mt-1">修改后重新提交，系统会使用新版本号进行审查。</p>
        </div>

        <form v-if="!loadingEdit" class="space-y-5" @submit.prevent="handleSubmit">
        <section class="card">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="font-semibold text-gray-800">1. 物料内容</h3>
              <p class="text-xs text-gray-400 mt-1">可以上传文件，也可以直接粘贴文案。</p>
            </div>
            <span class="text-xs text-gray-400">支持最大 10MB</span>
          </div>

          <div
            class="mt-4 border-2 border-dashed rounded-xl p-6 text-center transition-colors min-w-0"
            :class="isDragOver ? 'border-sky-500 bg-sky-50' : 'border-gray-300 bg-gray-50'"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleDrop"
          >
            <template v-if="!selectedFile">
              <p class="text-gray-700 font-medium">拖拽文件到这里，或点击选择文件</p>
              <p class="text-gray-400 text-xs mt-1">JPG / PNG / GIF / BMP / PDF / DOCX / PPTX / XLSX / TXT</p>
              <input type="file" :accept="allowedExtensions" class="mt-4 text-sm" @change="handleFileSelect" />
            </template>
            <template v-else>
              <p class="text-sm font-medium text-gray-800">{{ selectedFile.name }}</p>
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
          <BrandSelector
            :model-value="selectedBrand"
            :brands="brands"
            :loading="brandSearchLoading"
            :error="brandSearchError"
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
          <h3 class="font-semibold text-gray-800">2. 行业（可多选）</h3>
          <p class="text-xs text-gray-400 mt-1">可选择多个相关行业。系统会按多行业匹配法律规则、行业规则和舆情案例。</p>
          <div class="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            <button
              v-for="industry in industries"
              :key="industry"
              type="button"
              class="btn text-sm border break-words"
              :class="form.industries.includes(industry) ? 'bg-sky-600 text-white border-sky-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-sky-50'"
              @click="toggleIndustry(industry)"
            >
              {{ industry }}
            </button>
          </div>
        </section>

        <section class="card">
          <h3 class="font-semibold text-gray-800">3. 投放平台</h3>
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

        <section class="rounded-xl border border-gray-200 bg-white">
          <button
            type="button"
            class="w-full px-5 py-4 flex items-center justify-between text-left"
            @click="showMoreSettings = !showMoreSettings"
          >
            <span>
              <span class="block font-semibold text-gray-800">更多设置</span>
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
          {{ submitting ? (isResubmit ? '重新提交并审查中…' : '提交并审查中…') : (isResubmit ? '修改并重新审查' : '开始风险审查') }}
        </button>
      </form>
    </div>
  </DefaultLayout>
</template>
