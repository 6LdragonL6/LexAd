<script setup lang="ts">
// 改写模板库页 —— 展示合规改写模板列表，帮助广告文案快速修正风险点
import { onMounted, ref } from 'vue'
import { listTemplates } from '@/api/review'
import type { TemplateItem } from '@/types'

const templates = ref<TemplateItem[]>([])  // 模板列表
const loading = ref(false)                 // 加载状态

onMounted(async () => {
  loading.value = true
  try {
    const res = await listTemplates()
    templates.value = res.items
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="templates-page">
    <h1>改写模板库</h1>
    <p class="subtitle">合规改写模板，帮助广告文案快速修正风险点。</p>

    <div v-if="loading" class="status-msg">加载中...</div>
    <div v-else-if="!templates.length" class="status-msg">暂无模板数据。</div>

    <div v-else class="template-list">
      <div v-for="item in templates" :key="item.template_id" class="template-card">
        <h3>{{ item.title }}</h3>
        <div class="compare">
          <p><strong>修改前：</strong>{{ item.before }}</p>
          <p><strong>修改后：</strong>{{ item.after }}</p>
        </div>
        <p class="note">{{ item.note }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.templates-page { max-width: 800px; margin: 0 auto; }

h1 { color: #1a1a2e; }

.subtitle { color: #666; margin-bottom: 2rem; }

.status-msg { text-align: center; padding: 2rem; color: #888; }

.template-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.template-card {
  background: #f8f8f8;
  padding: 1.25rem;
  border-radius: 8px;
}

.template-card h3 { margin: 0 0 0.75rem; color: #1a1a2e; }

.compare { margin-bottom: 0.5rem; }
.compare p { color: #555; line-height: 1.5; margin: 0.25rem 0; }

.note { font-size: 0.8rem; color: #999; }
</style>
