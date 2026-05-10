<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useReviewStore } from '@/stores/review'

const route = useRoute()
const store = useReviewStore()
const requestId = route.params.requestId as string

onMounted(() => {
  if (!store.currentResult || store.currentResult.request_id !== requestId) {
    store.fetchResult(requestId)
  }
})
</script>

<template>
  <div class="result-page">
    <h1>审查结果</h1>

    <div v-if="store.loading" class="status-msg">加载中...</div>
    <div v-else-if="store.error" class="status-msg error">{{ store.error }}</div>

    <template v-else-if="store.currentResult">
      <div class="meta">
        <span>请求 ID：{{ store.currentResult.request_id }}</span>
        <span>时间：{{ store.currentResult.created_at }}</span>
      </div>

      <!-- Input -->
      <section class="card">
        <h2>输入内容</h2>
        <pre>{{ store.currentResult.input.raw_text || '(无文本)' }}</pre>
        <p v-if="store.currentResult.input.image_meta.status === 'has_image'">
          图片：{{ store.currentResult.input.image_meta.filename }}
        </p>
        <p v-if="store.currentResult.preprocess.warnings.length" class="warnings">
          ⚠ {{ store.currentResult.preprocess.warnings.join('；') }}
        </p>
      </section>

      <!-- Three-layer Review -->
      <section class="card" v-for="layer in [
        { key: 'legal_review', label: '法律层面审查' },
        { key: 'industry_review', label: '行业层面审查' },
        { key: 'platform_review', label: '平台层面审查' },
      ]" :key="layer.key">
        <h2>{{ layer.label }}</h2>
        <p>状态：<span :class="store.currentResult.review[layer.key].status">
          {{ store.currentResult.review[layer.key].status }}
        </span></p>
        <p>风险评分：{{ store.currentResult.review[layer.key].risk_score }}</p>
        <p v-if="store.currentResult.review[layer.key].explanations.length">
          {{ store.currentResult.review[layer.key].explanations.join('；') }}
        </p>
        <p v-if="store.currentResult.review[layer.key].suggestions.length">
          建议：{{ store.currentResult.review[layer.key].suggestions.join('；') }}
        </p>
      </section>

      <!-- Case References -->
      <section class="card" v-if="store.currentResult.case_references.length">
        <h2>案例参考 ({{ store.currentResult.case_references.length }})</h2>
        <ul>
          <li v-for="c in store.currentResult.case_references" :key="c.case_id">
            <strong>{{ c.title }}</strong> — {{ c.summary }}
          </li>
        </ul>
      </section>

      <!-- Rewrite Templates -->
      <section class="card" v-if="store.currentResult.rewrite_templates.length">
        <h2>改写模板 ({{ store.currentResult.rewrite_templates.length }})</h2>
        <div v-for="t in store.currentResult.rewrite_templates" :key="t.template_id" class="template-item">
          <strong>{{ t.title }}</strong>
          <p>修改前：{{ t.before }}</p>
          <p>修改后：{{ t.after }}</p>
          <p class="note">{{ t.note }}</p>
        </div>
      </section>

      <!-- Penalty Assessment -->
      <section class="card">
        <h2>罚金评估</h2>
        <p>
          等级：{{ store.currentResult.penalty_assessment.penalty_level }} &mdash;
          金额：{{ store.currentResult.penalty_assessment.penalty_amount }}
        </p>
        <p>{{ store.currentResult.penalty_assessment.assessment_notes }}</p>
      </section>

      <!-- Final Result -->
      <section class="card final">
        <h2>最终结论</h2>
        <p class="overall-status">{{ store.currentResult.final_result.overall_status }}</p>
        <p>{{ store.currentResult.final_result.summary }}</p>
        <ul>
          <li v-for="(rec, i) in store.currentResult.final_result.recommendations" :key="i">
            {{ rec }}
          </li>
        </ul>
        <p class="note">{{ store.currentResult.final_result.notes }}</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.result-page { max-width: 800px; margin: 0 auto; }

h1 { color: #1a1a2e; }

.meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.8rem;
  color: #999;
  margin-bottom: 1.5rem;
}

.card {
  background: #f8f8f8;
  padding: 1.25rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.card h2 {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
  color: #1a1a2e;
}

pre {
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
  color: #444;
}

.status-msg { text-align: center; padding: 2rem; color: #888; }
.status-msg.error { color: #e94560; }

.warnings { color: #e67e22; font-size: 0.9rem; }

.template-item {
  border-top: 1px solid #ddd;
  padding-top: 0.75rem;
  margin-top: 0.75rem;
}

.note { font-size: 0.8rem; color: #999; }

.overall-status {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  background: #27ae60;
  color: #fff;
  font-weight: 600;
}

.final { border: 2px solid #27ae60; }
</style>
