<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Brand } from '@/types'

const props = defineProps<{
  modelValue: Brand | null
  brands: Brand[]
  loading: boolean
  error: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Brand | null]
  'search': [query: string]
  'create': [name: string]
}>()

const searchText = ref('')
const showDropdown = ref(false)
const creating = ref(false)

const filteredBrands = computed(() => {
  if (!searchText.value.trim()) return props.brands.slice(0, 20)
  const q = searchText.value.trim().toLowerCase().replace(/\s+/g, '')
  return props.brands.filter(b => {
    const name = b.name.toLowerCase().replace(/\s+/g, '')
    if (name.includes(q)) return true
    return (b.aliases || []).some((a: string) => a.toLowerCase().replace(/\s+/g, '').includes(q))
  }).slice(0, 20)
})

const exactMatch = computed(() => {
  if (!searchText.value.trim()) return null
  const q = searchText.value.trim().toLowerCase().replace(/\s+/g, '')
  return props.brands.find(b => b.name.toLowerCase().replace(/\s+/g, '') === q)
})

function selectBrand(brand: Brand) {
  emit('update:modelValue', brand)
  searchText.value = ''
  showDropdown.value = false
}

function clearBrand() {
  emit('update:modelValue', null)
  searchText.value = ''
}

async function handleCreate() {
  if (!searchText.value.trim() || creating.value) return
  creating.value = true
  try {
    emit('create', searchText.value.trim())
    searchText.value = ''
    showDropdown.value = false
  } finally {
    creating.value = false
  }
}

watch(() => props.modelValue, (val) => {
  if (!val) searchText.value = ''
})
</script>

<template>
  <div class="brand-selector">
    <label class="label">关联品牌（可选）</label>

    <!-- Selected brand chip -->
    <div v-if="modelValue" class="brand-chip">
      <span class="text-sm font-medium">{{ modelValue.name }}</span>
      <span class="text-xs text-gray-400 ml-2">{{ modelValue.industry || '未分类' }}</span>
      <button type="button" class="ml-auto text-gray-400 hover:text-red-500 text-lg leading-none px-1" @click="clearBrand" aria-label="清除品牌">&times;</button>
    </div>

    <!-- Search input -->
    <div v-if="!modelValue" class="relative">
      <input
        v-model="searchText"
        class="input"
        placeholder="搜索已有品牌或输入名称建立新品牌..."
        @focus="showDropdown = true"
        @blur="showDropdown = false"
        @input="emit('search', searchText)"
      />
      <div v-if="showDropdown && (searchText || brands.length)" class="brand-dropdown">
        <p v-if="loading" class="px-4 py-3 text-sm text-gray-400">搜索中...</p>
        <p v-else-if="error" class="px-4 py-3 text-sm text-red-500">{{ error }}</p>
        <template v-else>
          <button
            v-for="brand in filteredBrands"
            :key="brand.id"
            type="button"
            class="brand-dropdown-item"
            @mousedown.prevent="selectBrand(brand)"
          >
            <span>{{ brand.name }}</span>
            <span class="text-xs text-gray-400">{{ brand.industry || '未分类' }}</span>
          </button>
          <template v-if="searchText.trim() && !exactMatch">
            <div class="border-t border-gray-100 dark:border-gray-700 pt-1 mt-1">
              <button
                type="button"
                class="brand-dropdown-item text-sky-600"
                @mousedown.prevent="handleCreate"
                :disabled="creating"
              >
                {{ creating ? '创建中...' : `创建品牌「${searchText.trim()}」` }}
              </button>
            </div>
          </template>
        </template>
      </div>
    </div>
    <p class="text-xs text-gray-400 mt-1">选择品牌后可查看历史合规记录。品牌信息不参与本次 AI 风险评分。</p>
  </div>
</template>
