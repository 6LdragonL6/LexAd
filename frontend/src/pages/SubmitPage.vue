<!-- frontend/src/pages/SubmitPage.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const router = useRouter()

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
const materialTypes = ['文字', '图片', '视频脚本', '直播话术']
const submitting = ref(false)
const error = ref('')

async function handleSubmit() {
  error.value = ''
  submitting.value = true
  try {
    const res = await materialsApi.submit({
      ...form.value,
      deadline: form.value.deadline || undefined,
    })
    const material = res.data
    // Trigger AI review
    const reviewRes = await reviewsApi.aiReview(material.id)
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
        <div>
          <label class="block text-sm font-medium mb-1">物料名称 *</label>
          <input v-model="form.name" class="input" required placeholder="如：诺优能益生菌春节推广文案" />
        </div>
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
        <div>
          <label class="block text-sm font-medium mb-1">广告文案内容 *</label>
          <textarea v-model="form.raw_text" class="input h-40 resize-y" required
            placeholder="粘贴广告文案全文..."></textarea>
        </div>
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
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="submitting" class="btn-primary w-full">
          {{ submitting ? '提交并审查中...' : '提交并开始AI审查' }}
        </button>
      </form>
    </div>
  </DefaultLayout>
</template>
