<script setup lang="ts">
import type { EngineResult } from '@/types'

defineProps<{ result: EngineResult }>()
</script>

<template>
  <div class="space-y-4">
    <h3 class="text-sm font-semibold text-gray-700">审查引擎·执行报告</h3>
    <details v-for="layer in [result.layer1, result.layer2, result.layer3, result.layer4]" :key="layer.layer" open class="text-sm">
      <summary class="font-medium text-gray-600 cursor-pointer py-1">{{ layer.layer }}</summary>
      <div class="pl-4 mt-1 space-y-1">
        <p v-for="exp in layer.explanations" :key="exp" class="text-gray-500">{{ exp }}</p>
        <div v-for="rule in layer.matched_rules" :key="rule.rule_id" class="text-xs py-1">
          <span class="text-red-600">{{ rule.rule_text }}</span>
          <span v-if="rule.source_law" class="text-gray-400 ml-2">— {{ rule.source_law }}</span>
        </div>
      </div>
    </details>
    <div class="border-t pt-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">修改建议</h4>
      <ul class="text-sm text-gray-600 space-y-1">
        <li v-for="s in result.suggestions" :key="s" class="flex items-start gap-1">
          <span class="text-blue-500">▸</span> {{ s }}
        </li>
      </ul>
    </div>
  </div>
</template>
