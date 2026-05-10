<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useReviewStore } from '@/stores/review'

const router = useRouter()
const store = useReviewStore()

const rawText = ref('')
const imageFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  imageFile.value = target.files?.[0] || null
}

async function handleSubmit() {
  if (!rawText.value.trim()) return
  try {
    await store.submit(rawText.value, imageFile.value || undefined)
    if (store.currentResult) {
      router.push(`/result/${store.currentResult.request_id}`)
    }
  } catch {
    // error handled in store
  }
}
</script>

<template>
  <div class="review-page">
    <h1>广告合规审查</h1>
    <p class="subtitle">输入广告文案，可选上传图片，系统将进行三层合规审查。</p>

    <form class="review-form" @submit.prevent="handleSubmit">
      <label class="field-label" for="rawText">广告文案内容</label>
      <textarea
        id="rawText"
        v-model="rawText"
        rows="6"
        placeholder="请输入或粘贴广告文案内容..."
        class="text-input"
      ></textarea>

      <label class="field-label" for="imageUpload">上传图片（可选）</label>
      <input
        id="imageUpload"
        ref="fileInput"
        type="file"
        accept="image/png,image/jpeg,image/jpg,image/bmp,image/tiff,image/webp"
        class="file-input"
        @change="onFileChange"
      />
      <span v-if="imageFile" class="file-name">{{ imageFile.name }}</span>

      <div class="form-actions">
        <button
          type="submit"
          class="btn btn-primary"
          :disabled="store.loading || !rawText.trim()"
        >
          {{ store.loading ? '审查中...' : '提交审查' }}
        </button>
      </div>

      <p v-if="store.error" class="error-msg">{{ store.error }}</p>
    </form>
  </div>
</template>

<style scoped>
.review-page { max-width: 680px; margin: 0 auto; }

h1 { color: #1a1a2e; }

.subtitle { color: #666; margin-bottom: 2rem; }

.review-form {
  background: #f8f8f8;
  padding: 1.5rem;
  border-radius: 8px;
}

.field-label {
  display: block;
  margin: 1rem 0 0.4rem;
  font-weight: 600;
  color: #333;
}

.field-label:first-of-type { margin-top: 0; }

.text-input {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 0.95rem;
  resize: vertical;
  box-sizing: border-box;
}

.file-input {
  display: block;
  margin-top: 0.3rem;
}

.file-name {
  display: inline-block;
  margin-top: 0.3rem;
  font-size: 0.85rem;
  color: #888;
}

.form-actions { margin-top: 1.5rem; }

.btn {
  padding: 0.6rem 2rem;
  border-radius: 6px;
  font-size: 0.95rem;
  border: none;
  cursor: pointer;
}

.btn-primary {
  background: #e94560;
  color: #fff;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-msg {
  margin-top: 1rem;
  color: #e94560;
  font-size: 0.9rem;
}
</style>
