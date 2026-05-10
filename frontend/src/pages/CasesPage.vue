<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listCases } from '@/api/review'
import type { CaseItem } from '@/types'

const cases = ref<CaseItem[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await listCases()
    cases.value = res.items
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="cases-page">
    <h1>案例库</h1>
    <p class="subtitle">历史违规案例参考，辅助合规判断。</p>

    <div v-if="loading" class="status-msg">加载中...</div>
    <div v-else-if="!cases.length" class="status-msg">暂无案例数据。</div>

    <div v-else class="case-list">
      <div v-for="item in cases" :key="item.case_id" class="case-card">
        <h3>{{ item.title }}</h3>
        <p>{{ item.summary }}</p>
        <span class="case-id">ID: {{ item.case_id }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cases-page { max-width: 800px; margin: 0 auto; }

h1 { color: #1a1a2e; }

.subtitle { color: #666; margin-bottom: 2rem; }

.status-msg { text-align: center; padding: 2rem; color: #888; }

.case-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.case-card {
  background: #f8f8f8;
  padding: 1.25rem;
  border-radius: 8px;
}

.case-card h3 { margin: 0 0 0.5rem; color: #1a1a2e; }
.case-card p { color: #555; line-height: 1.5; }

.case-id {
  font-size: 0.75rem;
  color: #aaa;
}
</style>
