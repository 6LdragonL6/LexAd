<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { brandsApi } from '@/api/brands'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BrandProfilePanel from '@/components/brand/BrandProfilePanel.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { Brand, BrandProfile } from '@/types'

const store = useUserStore()
const brands = ref<Brand[]>([])
const searchText = ref('')
const loading = ref(true)
const error = ref('')
const selectedBrand = ref<Brand | null>(null)
const profile = ref<BrandProfile | null>(null)
const profileLoading = ref(false)
const saving = ref(false)
const saveError = ref('')

const editForm = ref({
  name: '',
  aliases: '',
  industry: '',
  description: '',
})
const showEdit = ref(false)

onMounted(async () => {
  await loadBrands()
})

async function loadBrands(query = '') {
  loading.value = true
  error.value = ''
  try {
    const res = await brandsApi.search(query)
    brands.value = res.data
  } catch (e: any) {
    error.value = e.response?.data?.detail || '加载品牌列表失败'
  } finally {
    loading.value = false
  }
}

async function selectBrand(brand: Brand) {
  selectedBrand.value = brand
  profile.value = null
  profileLoading.value = true
  try {
    const res = await brandsApi.profile(brand.id)
    profile.value = res.data
  } catch {
    profile.value = null
  } finally {
    profileLoading.value = false
  }
}

function handleSearch() {
  loadBrands(searchText.value)
}

function canEdit(): boolean {
  return store.isLegal || store.isAdmin
}

function openEdit() {
  if (!selectedBrand.value) return
  editForm.value = {
    name: selectedBrand.value.name,
    aliases: (selectedBrand.value.aliases || []).join('、'),
    industry: selectedBrand.value.industry || '',
    description: selectedBrand.value.description || '',
  }
  showEdit.value = true
  saveError.value = ''
}

function cancelEdit() {
  showEdit.value = false
  saveError.value = ''
}

async function handleSave() {
  if (!selectedBrand.value) return
  saving.value = true
  saveError.value = ''
  try {
    const aliases = editForm.value.aliases
      .split(/[、,]/)
      .map(s => s.trim())
      .filter(Boolean)
    const updated = await brandsApi.update(selectedBrand.value.id, {
      name: editForm.value.name.trim() || undefined,
      aliases: aliases.length ? aliases : undefined,
      industry: editForm.value.industry.trim(),
      description: editForm.value.description.trim(),
    })
    selectedBrand.value = updated.data
    showEdit.value = false
    await selectBrand(updated.data)
  } catch (e: any) {
    saveError.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function handleArchive() {
  if (!selectedBrand.value) return
  if (!confirm(`确认归档品牌「${selectedBrand.value.name}」？归档后不可用于新提交。`)) return
  saving.value = true
  saveError.value = ''
  try {
    const updated = await brandsApi.update(selectedBrand.value.id, { status: 'archived' })
    selectedBrand.value = updated.data
    profile.value = null
  } catch (e: any) {
    saveError.value = e.response?.data?.detail || '归档失败'
  } finally {
    saving.value = false
  }
}

async function handleReactivate() {
  if (!selectedBrand.value) return
  if (!confirm(`确认恢复品牌「${selectedBrand.value.name}」？`)) return
  saving.value = true
  saveError.value = ''
  try {
    const updated = await brandsApi.update(selectedBrand.value.id, { status: 'active' })
    selectedBrand.value = updated.data
    profile.value = null
  } catch (e: any) {
    saveError.value = e.response?.data?.detail || '恢复失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <DefaultLayout>
    <div class="max-w-6xl mx-auto p-4 lg:p-8">
      <div class="mb-6">
        <h2 class="page-heading">品牌档案</h2>
        <p class="text-sm text-gray-400 mt-1">查看品牌的合规历史记录。品牌数据由物料提交自动关联。</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6">
        <!-- Left: Brand list -->
        <div class="space-y-4">
          <div class="flex gap-2">
            <input
              v-model="searchText"
              class="input"
              placeholder="搜索品牌名称..."
              @keyup.enter="handleSearch"
            />
            <button class="btn-primary min-h-[44px] px-4" @click="handleSearch">搜索</button>
          </div>

          <div v-if="loading" class="text-gray-400 text-center py-8">加载中...</div>
          <div v-else-if="error" class="text-red-500 text-center py-8">{{ error }}</div>
          <div v-else-if="!brands.length" class="card text-center text-gray-400 py-8">暂无品牌记录</div>
          <div v-else class="card !p-0 overflow-hidden">
            <button
              v-for="brand in brands"
              :key="brand.id"
              class="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 border-b border-gray-100 dark:border-gray-700 last:border-0 transition-colors"
              :class="{ 'bg-sky-50 dark:bg-sky-900/20 border-l-2 border-l-sky-500': selectedBrand?.id === brand.id }"
              @click="selectBrand(brand)"
            >
              <div class="flex items-center gap-2">
                <span class="font-medium text-gray-800 dark:text-gray-200">{{ brand.name }}</span>
                <StatusBadge :variant="brand.status === 'active' ? 'success' : 'gray'" class="ml-auto">
                  {{ brand.status === 'active' ? '激活' : '已归档' }}
                </StatusBadge>
              </div>
              <span class="text-xs text-gray-400">{{ brand.industry || '未设定' }}</span>
            </button>
          </div>
        </div>

        <!-- Right: Profile panel -->
        <div class="space-y-5">
          <!-- Admin actions -->
          <div v-if="canEdit() && selectedBrand" class="card">
            <div class="flex items-center justify-between gap-3">
              <h3 class="font-semibold text-gray-800 dark:text-gray-200">管理操作</h3>
              <div class="flex gap-2">
                <button class="btn-outline text-sm min-h-[36px] px-3" @click="openEdit" :disabled="saving">编辑</button>
                <button
                  v-if="selectedBrand.status === 'active'"
                  class="btn-ghost text-sm min-h-[36px] px-3 text-red-600 hover:bg-red-50"
                  @click="handleArchive"
                  :disabled="saving"
                >归档</button>
                <button
                  v-else
                  class="btn-ghost text-sm min-h-[36px] px-3 text-green-600 hover:bg-green-50"
                  @click="handleReactivate"
                  :disabled="saving"
                >恢复</button>
              </div>
            </div>
            <p v-if="saveError" class="text-sm text-red-500 mt-2">{{ saveError }}</p>

            <!-- Edit form -->
            <div v-if="showEdit" class="mt-4 space-y-3 border-t border-gray-100 dark:border-gray-700 pt-4">
              <div>
                <label class="label">品牌名称</label>
                <input v-model="editForm.name" class="input" />
              </div>
              <div>
                <label class="label">别名（用顿号或逗号分隔）</label>
                <input v-model="editForm.aliases" class="input" placeholder="例如：Nestlé、Nestle" />
              </div>
              <div>
                <label class="label">行业</label>
                <input v-model="editForm.industry" class="input" />
              </div>
              <div>
                <label class="label">说明</label>
                <textarea v-model="editForm.description" class="input min-h-20" placeholder="品牌说明..." />
              </div>
              <div class="flex gap-2">
                <button class="btn-primary text-sm" @click="handleSave" :disabled="saving">
                  {{ saving ? '保存中...' : '保存' }}
                </button>
                <button class="btn-outline text-sm" @click="cancelEdit">取消</button>
              </div>
            </div>
          </div>

          <BrandProfilePanel :profile="profile" :loading="profileLoading" />
        </div>
      </div>
    </div>
  </DefaultLayout>
</template>
