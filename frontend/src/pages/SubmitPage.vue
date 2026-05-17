<!-- frontend/src/pages/SubmitPage.vue -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const router = useRouter()
const MAX_FILE_SIZE = 10 * 1024 * 1024

const form = ref({
  name: '',
  industry: '',
  platforms: [] as string[],
  material_type: '文字',
  raw_text: '',
  priority: 'normal',
  deadline: null as string | null,
})

const industries = ['食品', '医疗', '教育', '汽车', '金融', '美妆', '直播电商']
const platforms = ['抖音', '小红书', '微信', '微博', '京东', '淘宝']
const materialTypes = ['文字', '图片', 'PDF文档', 'Word文档', 'PPT演示', 'Excel表格', '视频脚本', '直播话术']
const submitting = ref(false)
const error = ref('')

const selectedFile = ref<File | null>(null)
const extractedText = ref('')
const previewQuality = ref<'good' | 'degraded' | 'minimal' | null>(null)
const previewing = ref(false)
const isDragOver = ref(false)

const allowedExtensions = '.jpg,.jpeg,.png,.gif,.bmp,.pdf,.docx,.doc,.pptx,.xlsx,.txt'

function fileSizeDisplay(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function guessMaterialType(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    jpg: '图片', jpeg: '图片', png: '图片', gif: '图片', bmp: '图片',
    pdf: 'PDF文档',
    docx: 'Word文档', doc: 'Word文档',
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

function handleDrop(e: DragEvent) {
  isDragOver.value = false
  if (e.dataTransfer?.files?.[0]) setFile(e.dataTransfer.files[0])
}

function setFile(file: File) {
  const ext = '.' + (file.name.split('.').pop()?.toLowerCase() ?? '')
  if (!allowedExtensions.includes(ext)) {
    error.value = '不支持的文件格式，支持：JPG/PNG/PDF/DOCX/DOC/PPTX/XLSX/TXT'
    return
  }
  if (file.size > MAX_FILE_SIZE) {
    error.value = '文件过大（上限 10MB），请压缩后重试'
    return
  }
  error.value = ''
  selectedFile.value = file
  extractedText.value = ''
  previewQuality.value = null
  form.value.material_type = guessMaterialType(file.name)
}

function removeFile() {
  selectedFile.value = null
  extractedText.value = ''
  previewQuality.value = null
}

async function handlePreview() {
  if (!selectedFile.value) return
  previewing.value = true
  error.value = ''
  try {
    const res = await materialsApi.previewText(selectedFile.value)
    extractedText.value = res.data.text
    previewQuality.value = res.data.quality
  } catch (e: any) {
    error.value = e.response?.data?.detail || '文本提取失败'
  } finally {
    previewing.value = false
  }
}

const qualityLabel = computed(() => {
  if (previewQuality.value === 'good') return { text: '识别质量：良好', cls: 'text-green-600' }
  if (previewQuality.value === 'degraded') return { text: '识别质量：一般（已使用降级方案）', cls: 'text-yellow-600' }
  if (previewQuality.value === 'minimal') return { text: '识别质量：较低，建议人工核对', cls: 'text-red-500' }
  return null
})

const finalText = computed({
  get: () => extractedText.value || form.value.raw_text,
  set: (val: string) => {
    if (selectedFile.value) {
      extractedText.value = val
    } else {
      form.value.raw_text = val
    }
  },
})

async function handleSubmit() {
  error.value = ''
  submitting.value = true

  const fd = new FormData()
  const body = JSON.stringify({
    ...form.value,
    raw_text: finalText.value,
    deadline: form.value.deadline || undefined,
  })
  fd.append('body', body)
  if (selectedFile.value) {
    fd.append('file', selectedFile.value)
  }

  try {
    const res = await materialsApi.submit(fd)
    const reviewRes = await reviewsApi.aiReview(res.data.id)
    router.push(`/result/${reviewRes.data.id}`)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '提交失败'
  } finally {
    submitting.value = false
  }
}

function togglePlatform(p: string) {
  const idx = form.value.platforms.indexOf(p)
  if (idx >= 0) form.value.platforms.splice(idx, 1)
  else form.value.platforms.push(p)
}
</script>

<template>
  <DefaultLayout>
    <div class="max-w-2xl mx-auto p-8">
      <h2 class="text-xl font-bold mb-6">提交广告物料</h2>
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <!-- Name -->
        <div>
          <label class="block text-sm font-medium mb-1">物料名称 *</label>
          <input v-model="form.name" class="input" required placeholder="如：诺优能益生菌春节推广文案" />
        </div>

        <!-- Industry + Type -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">行业类型</label>
            <select v-model="form.industry" class="input">
              <option value="">请选择</option>
              <option v-for="ind in industries" :key="ind" :value="ind">{{ ind }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">物料类型</label>
            <select v-model="form.material_type" class="input">
              <option v-for="mt in materialTypes" :key="mt" :value="mt">{{ mt }}</option>
            </select>
          </div>
        </div>

        <!-- Platforms -->
        <div>
          <label class="block text-sm font-medium mb-1">投放平台</label>
          <div class="flex flex-wrap gap-2">
            <button type="button" v-for="p in platforms" :key="p"
              @click="togglePlatform(p)"
              :class="form.platforms.includes(p) ? 'btn-primary text-sm' : 'btn-outline text-sm'">
              {{ p }}
            </button>
          </div>
        </div>

        <!-- File upload area -->
        <div>
          <label class="block text-sm font-medium mb-1">上传文件（可选）</label>
          <div
            class="border-2 border-dashed rounded-lg p-6 text-center transition-colors"
            :class="isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300'"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleDrop"
          >
            <template v-if="!selectedFile">
              <p class="text-gray-500 mb-2">拖拽文件到此处 或 点击选择</p>
              <p class="text-gray-400 text-xs">
                支持 JPG / PNG / GIF / BMP / PDF / DOCX / DOC / PPTX / XLSX / TXT，单文件最大 10MB
              </p>
              <input
                type="file"
                :accept="allowedExtensions"
                class="mt-3 text-sm"
                @change="handleFileSelect"
              />
            </template>
            <template v-else>
              <div class="flex items-center justify-center gap-3">
                <span class="text-sm font-medium">{{ selectedFile.name }}</span>
                <span class="text-xs text-gray-500">({{ fileSizeDisplay(selectedFile.size) }})</span>
              </div>
              <div class="flex items-center justify-center gap-3 mt-3">
                <button type="button" class="btn-outline text-sm" :disabled="previewing" @click="handlePreview">
                  {{ previewing ? '提取中...' : '预览提取文本' }}
                </button>
                <button type="button" class="text-sm text-red-500 hover:underline" @click="removeFile">
                  移除
                </button>
              </div>
            </template>
          </div>
        </div>

        <!-- Text content: with quality label if file was processed -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="text-sm font-medium">广告文案内容 *</label>
            <span v-if="qualityLabel" :class="qualityLabel.cls" class="text-xs">{{ qualityLabel.text }}</span>
          </div>
          <textarea
            v-model="finalText"
            class="input h-40 resize-y"
            required
            :placeholder="selectedFile ? '预览提取的文本，可编辑修改' : '粘贴广告文案全文...'"
          ></textarea>
        </div>

        <!-- Priority + Deadline -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">优先级</label>
            <select v-model="form.priority" class="input">
              <option value="normal">普通</option>
              <option value="urgent">加急 (24h)</option>
              <option value="extreme">极速 (4h)</option>
            </select>
          </div>
          <div v-if="form.priority !== 'normal'">
            <label class="block text-sm font-medium mb-1">截止时间</label>
            <input v-model="form.deadline" type="datetime-local" class="input" />
          </div>
        </div>

        <!-- Error + Submit -->
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="submitting" class="btn-primary w-full">
          {{ submitting ? '提交并审查中...' : '提交并开始AI审查' }}
        </button>
      </form>
    </div>
  </DefaultLayout>
</template>
