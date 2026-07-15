<script setup lang="ts">
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useUserStore } from '@/stores/user'
import { brandsApi } from '@/api/brands'
import { knowledgeApi } from '@/api/knowledge'
import { adminSettingsApi } from '@/api/adminSettings'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BrandMemoryCard from '@/components/brand/BrandMemoryCard.vue'
import BrandProfilePanel from '@/components/brand/BrandProfilePanel.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { Brand, BrandProfile } from '@/types'

const store = useUserStore()
const brands = ref<Brand[]>([])
const searchText = ref('')
const selectedBrand = ref<Brand | null>(null)
const profile = ref<BrandProfile | null>(null)
const profileLoading = ref(false)
const profileError = ref('')
const saving = ref(false)
const saveError = ref('')
const industryOptions = ref<string[]>(['食品', '医疗', '教育', '汽车', '金融', '美妆', '直播电商'])

type ListState = 'loading' | 'ready' | 'empty' | 'error'
type LoadErrorKind = 'network' | 'forbidden' | 'server' | 'unknown'

interface LoadError {
  kind: LoadErrorKind
  message: string
}

const listState = ref<ListState>('loading')
const listError = ref<LoadError | null>(null)

const editForm = ref({
  name: '',
  aliases: '',
  industries: [] as string[],
  description: '',
})
const showEdit = ref(false)

onMounted(async () => {
  const [industryResult] = await Promise.allSettled([knowledgeApi.industries(), loadBrands()])
  if (industryResult.status === 'fulfilled') {
    industryOptions.value = industryResult.value.data.items.map(item => item.label || item.value)
  }
})

async function loadBrands(query = '', preserveExisting = false) {
  if (!preserveExisting) {
    listState.value = 'loading'
  }
  listError.value = null
  try {
    const res = await brandsApi.search(query)
    if (res.data.length === 0) {
      if (preserveExisting) {
        brands.value = []
      }
      listState.value = 'empty'
    } else {
      brands.value = res.data
      listState.value = 'ready'
    }
  } catch (e: any) {
    if (!preserveExisting) {
      brands.value = []
    }
    if (axios.isAxiosError(e)) {
      if (!e.response) {
        listError.value = { kind: 'network', message: '无法连接本地后端，请确认一键启动已成功完成。' }
      } else if (e.response.status === 403) {
        listError.value = { kind: 'forbidden', message: '当前账号无权访问品牌档案。' }
      } else if (e.response.status >= 500) {
        listError.value = { kind: 'server', message: e.response.data?.detail || '品牌服务暂时不可用。' }
      } else {
        listError.value = { kind: 'unknown', message: '加载品牌列表失败。' }
      }
    } else {
      listError.value = { kind: 'unknown', message: '加载品牌列表失败。' }
    }
    listState.value = 'error'
  }
}

async function selectBrand(brand: Brand) {
  selectedBrand.value = brand
  profile.value = null
  profileError.value = ''
  profileLoading.value = true
  try {
    const res = await brandsApi.profile(brand.id)
    profile.value = res.data
  } catch {
    profile.value = null
    profileError.value = '加载品牌档案失败，请重试。'
  } finally {
    profileLoading.value = false
  }
}

async function retryProfile() {
  if (!selectedBrand.value) return
  await selectBrand(selectedBrand.value)
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
    industries: [...(selectedBrand.value.industries || [])],
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
      description: editForm.value.description.trim(),
      industries: store.isAdmin ? editForm.value.industries : undefined,
    })
    selectedBrand.value = updated.data
    const idx = brands.value.findIndex(b => b.id === updated.data.id)
    if (idx !== -1) brands.value[idx] = updated.data
    showEdit.value = false
    await selectBrand(updated.data)
  } catch (e: any) {
    saveError.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

function toggleBrandIndustry(industry: string) {
  const index = editForm.value.industries.indexOf(industry)
  if (index >= 0) editForm.value.industries.splice(index, 1)
  else editForm.value.industries.push(industry)
}

async function handleSuggestion(suggestionId: string, action: 'accept' | 'ignore' | 'restore') {
  if (!selectedBrand.value || !store.isAdmin) return
  saving.value = true
  saveError.value = ''
  try {
    const response = await brandsApi.reviewIndustrySuggestion(selectedBrand.value.id, suggestionId, action)
    profile.value = response.data
    selectedBrand.value = response.data.brand
    const index = brands.value.findIndex(item => item.id === response.data.brand.id)
    if (index >= 0) brands.value[index] = response.data.brand
  } catch (e: any) {
    saveError.value = e.response?.data?.detail || '行业建议处理失败'
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
    brands.value = brands.value.filter(b => b.id !== updated.data.id)
    selectedBrand.value = null
    profile.value = null
    profileError.value = ''
    if (brands.value.length === 0) {
      listState.value = 'empty'
    }
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
    const idx = brands.value.findIndex(b => b.id === updated.data.id)
    if (idx !== -1) {
      brands.value[idx] = updated.data
    }
    selectedBrand.value = updated.data
    profile.value = null
  } catch (e: any) {
    saveError.value = e.response?.data?.detail || '恢复失败'
  } finally {
    saving.value = false
  }
}

async function handleAdminDelete() {
  if (!selectedBrand.value) return
  if (!confirm(`将品牌「${selectedBrand.value.name}」移入回收站？历史物料不会被删除。`)) return
  saving.value = true
  saveError.value = ''
  try {
    const brandId = selectedBrand.value.id
    await adminSettingsApi.moveToRecycleBin('brand', brandId)
    brands.value = brands.value.filter(brand => brand.id !== brandId)
    selectedBrand.value = null
    profile.value = null
    if (!brands.value.length) listState.value = 'empty'
  } catch (e: any) {
    saveError.value = e.response?.data?.detail || '删除失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <DefaultLayout>
    <div class="page-container max-w-6xl">
      <div class="responsive-toolbar mb-6">
        <div>
          <h2 class="page-heading">品牌档案</h2>
          <p class="text-sm text-gray-400 mt-1">查看品牌的合规历史记录。品牌数据由物料提交自动关联。</p>
        </div>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-[300px_minmax(0,1fr)] gap-6">
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

          <div v-if="listState === 'loading'" class="text-gray-400 text-center py-8">加载中...</div>
          <div v-else-if="listState === 'error'" class="card">
            <EmptyState :message="listError?.message || '加载失败'">
              <template #action>
                <button class="btn-primary text-sm min-h-[36px] px-4" @click="loadBrands(searchText)">重新加载</button>
              </template>
            </EmptyState>
          </div>
          <div v-else-if="listState === 'empty'" class="card">
            <EmptyState message="暂无品牌记录" />
          </div>
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
              <span class="text-xs text-gray-400">{{ brand.industries?.join('、') || '未设定' }}</span>
            </button>
          </div>
        </div>

        <!-- Right: Profile panel -->
        <div class="space-y-5">
          <BrandMemoryCard
            v-if="selectedBrand"
            :profile="profile"
            :loading="profileLoading"
            mode="full"
            class="!mt-0"
          />

          <!-- Admin actions -->
          <div v-if="canEdit() && selectedBrand" class="card">
            <div class="flex items-center justify-between gap-3">
              <h3 class="font-semibold text-gray-800 dark:text-gray-200">管理操作</h3>
              <div class="flex gap-2">
                <button class="btn-outline text-sm min-h-[36px] px-3" @click="openEdit" :disabled="saving">编辑</button>
                <button v-if="store.isAdmin" class="btn-ghost text-sm min-h-[36px] px-3 text-red-600 hover:bg-red-50" @click="handleAdminDelete" :disabled="saving">删除</button>
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
              <div v-if="store.isAdmin">
                <label class="label">行业</label>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="industry in industryOptions"
                    :key="industry"
                    type="button"
                    class="rounded-full border px-3 py-1.5 text-sm transition-colors"
                    :class="editForm.industries.includes(industry)
                      ? 'border-sky-500 bg-sky-50 text-sky-700 dark:border-sky-500 dark:bg-sky-950/40 dark:text-sky-300'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-sky-300 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300'"
                    @click="toggleBrandIndustry(industry)"
                  >{{ industry }}</button>
                </div>
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

          <div v-if="store.isAdmin && profile?.industry_suggestions?.length" class="card">
            <div class="mb-4">
              <h3 class="font-semibold text-gray-800 dark:text-gray-100">物料记录建议</h3>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">根据该品牌历史与新提交物料产生，由管理员确认是否加入品牌常用行业。</p>
            </div>
            <div class="space-y-3">
              <div v-for="item in profile.industry_suggestions" :key="item.id" class="rounded-xl border border-gray-200 bg-gray-50/70 p-3 dark:border-gray-700 dark:bg-gray-800/70">
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-gray-800 dark:text-gray-100">{{ item.industry }}</span>
                      <StatusBadge :variant="item.status === 'pending' ? 'warning' : item.status === 'accepted' ? 'success' : 'gray'">
                        {{ item.status === 'pending' ? '待确认' : item.status === 'accepted' ? '已添加' : '已忽略' }}
                      </StatusBadge>
                    </div>
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">出现 {{ item.occurrence_count }} 次 · 最近：{{ item.latest_material_name || '历史物料' }}</p>
                  </div>
                  <div class="flex gap-2">
                    <button v-if="item.status === 'pending'" class="btn-primary text-xs" :disabled="saving" @click="handleSuggestion(item.id, 'accept')">添加到品牌</button>
                    <button v-if="item.status === 'pending'" class="btn-outline text-xs" :disabled="saving" @click="handleSuggestion(item.id, 'ignore')">忽略</button>
                    <button v-if="item.status === 'ignored'" class="btn-outline text-xs" :disabled="saving" @click="handleSuggestion(item.id, 'restore')">恢复审核</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Profile loading/error states -->
          <div v-if="profileLoading" class="text-gray-400 text-center py-8">加载品牌档案中...</div>
          <div v-else-if="profileError && selectedBrand" class="card">
            <EmptyState :message="profileError">
              <template #action>
                <button class="btn-primary text-sm min-h-[36px] px-4" @click="retryProfile">重试</button>
              </template>
            </EmptyState>
          </div>
          <BrandProfilePanel v-else :profile="profile" :loading="false" />
        </div>
      </div>
    </div>
  </DefaultLayout>
</template>
