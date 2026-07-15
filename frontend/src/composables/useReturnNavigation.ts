import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import type { User } from '@/types'

export type ReturnSource = 'workbench' | 'legal-dashboard'

export function resolveReturnSource(value: unknown, role?: User['role']): ReturnSource {
  if (value === 'workbench' || value === 'legal-dashboard') return value
  return role === 'legal' || role === 'admin' ? 'legal-dashboard' : 'workbench'
}

export function useReturnNavigation() {
  const route = useRoute()
  const router = useRouter()
  const store = useUserStore()
  const source = computed(() => resolveReturnSource(route.query.from, store.user?.role))
  const returnLabel = computed(() => source.value === 'legal-dashboard' ? '返回法务审核台' : '返回工作台')

  function returnToSource(replace = false) {
    const target = source.value === 'legal-dashboard' ? { name: 'legal' } : { name: 'home' }
    return replace ? router.replace(target) : router.push(target)
  }

  return { source, returnLabel, returnToSource }
}
