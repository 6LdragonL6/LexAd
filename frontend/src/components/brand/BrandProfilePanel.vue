<script setup lang="ts">
import type { BrandProfile } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'

defineProps<{ profile: BrandProfile | null; loading: boolean }>()
</script>

<template>
  <div class="space-y-5">
    <div v-if="loading" class="text-gray-400 text-center py-8">加载品牌档案中...</div>

    <template v-else-if="profile">
      <div class="card">
        <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">{{ profile.brand.name }}</h3>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">行业</span>
            <span class="text-right text-gray-800 dark:text-gray-200">{{ profile.brand.industries?.join('、') || '未设定' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">状态</span>
            <StatusBadge :variant="profile.brand.status === 'active' ? 'success' : 'gray'">
              {{ profile.brand.status === 'active' ? '激活' : '已归档' }}
            </StatusBadge>
          </div>
          <div v-if="profile.brand.aliases?.length" class="flex justify-between">
            <span class="text-gray-500">别名</span>
            <span class="text-right text-gray-800 dark:text-gray-200">{{ profile.brand.aliases.join('、') }}</span>
          </div>
          <div v-if="profile.brand.description" class="pt-2 border-t border-gray-100 dark:border-gray-700">
            <p class="text-xs text-gray-400 mb-1">说明</p>
            <p class="text-gray-700 dark:text-gray-300">{{ profile.brand.description }}</p>
          </div>
        </div>
      </div>

      <div class="card">
        <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">审核指标</h3>
        <div class="grid grid-cols-2 gap-4">
          <div class="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p class="text-2xl font-bold text-gray-800 dark:text-gray-200">{{ profile.total_reviews }}</p>
            <p class="text-xs text-gray-400">总审核数</p>
          </div>
          <div class="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p class="text-2xl font-bold" :class="profile.pass_rate !== null && profile.pass_rate >= 80 ? 'text-green-600' : 'text-amber-600'">
              {{ profile.pass_rate !== null ? profile.pass_rate.toFixed(0) + '%' : '-' }}
            </p>
            <p class="text-xs text-gray-400">通过率</p>
          </div>
          <div class="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p class="text-2xl font-bold text-gray-800 dark:text-gray-200">{{ profile.decided_reviews }}</p>
            <p class="text-xs text-gray-400">已决定</p>
          </div>
          <div class="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p class="text-2xl font-bold text-gray-800 dark:text-gray-200">{{ profile.approved_count }}</p>
            <p class="text-xs text-gray-400">已通过</p>
          </div>
        </div>
        <div v-if="profile.avg_versions !== null" class="mt-3 text-sm text-gray-500 text-center">
          平均 {{ profile.avg_versions.toFixed(1) }} 次提交
        </div>
      </div>

      <div v-if="profile.top_violations?.length" class="card">
        <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">高频违规</h3>
        <div class="space-y-2">
          <div v-for="v in profile.top_violations" :key="v.rule_id"
               class="flex justify-between items-center text-sm py-1.5 border-b border-gray-50 dark:border-gray-700 last:border-0">
            <span class="text-gray-700 dark:text-gray-300">{{ v.rule_text }}</span>
            <span class="text-xs text-gray-400">{{ v.count }}次</span>
          </div>
        </div>
      </div>

      <div v-if="profile.recent_reviews?.length" class="card">
        <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">最近审核</h3>
        <div class="space-y-2">
          <div v-for="r in profile.recent_reviews" :key="r.id"
               class="flex justify-between items-center text-sm py-1.5 border-b border-gray-50 dark:border-gray-700 last:border-0">
            <span class="text-gray-700 dark:text-gray-300">第{{ r.version }}次 · 风险{{ r.ai_risk_score }}</span>
            <StatusBadge v-if="r.legal_decision" :variant="r.legal_decision === 'approved' ? 'success' : r.legal_decision === 'returned' ? 'danger' : 'warning'">
              {{ r.legal_decision === 'approved' ? '通过' : r.legal_decision === 'returned' ? '退回' : '条件通过' }}
            </StatusBadge>
          </div>
        </div>
      </div>

      <div v-if="profile.approved_materials?.length" class="card">
        <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">通过物料</h3>
        <div class="space-y-2">
          <div v-for="m in profile.approved_materials" :key="m.id"
               class="text-sm py-1 border-b border-gray-50 dark:border-gray-700 last:border-0">
            <p class="font-medium text-gray-800 dark:text-gray-200">{{ m.name }}</p>
            <p class="text-xs text-gray-400 truncate">{{ m.raw_text_preview || '无预览' }}</p>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="card text-center text-gray-400 py-8">暂无品牌档案数据</div>
  </div>
</template>
