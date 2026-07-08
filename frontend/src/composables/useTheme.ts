import { computed, ref } from 'vue'

export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'lexad-theme'
const preferences: ThemePreference[] = ['system', 'light', 'dark']

const themePreference = ref<ThemePreference>(readStoredPreference())
const systemTheme = ref<ResolvedTheme>(readSystemTheme())
let mediaQuery: MediaQueryList | null = null

const resolvedTheme = computed<ResolvedTheme>(() => {
  return themePreference.value === 'system' ? systemTheme.value : themePreference.value
})

function isThemePreference(value: string | null): value is ThemePreference {
  return !!value && preferences.includes(value as ThemePreference)
}

function safeLocalStorage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

function readStoredPreference(): ThemePreference {
  if (typeof window === 'undefined') return 'system'
  const stored = safeLocalStorage()?.getItem(STORAGE_KEY) ?? null
  return isThemePreference(stored) ? stored : 'system'
}

function readSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function persistPreference(preference: ThemePreference) {
  const storage = safeLocalStorage()
  if (!storage) return
  storage.setItem(STORAGE_KEY, preference)
}

function applyTheme() {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.dataset.theme = resolvedTheme.value
  root.dataset.themePreference = themePreference.value
  root.style.colorScheme = resolvedTheme.value
}

function handleSystemThemeChange(event: MediaQueryListEvent) {
  systemTheme.value = event.matches ? 'dark' : 'light'
  applyTheme()
}

export function initializeTheme() {
  if (typeof window === 'undefined') return
  mediaQuery = window.matchMedia?.('(prefers-color-scheme: dark)') ?? null
  systemTheme.value = mediaQuery?.matches ? 'dark' : 'light'
  applyTheme()

  mediaQuery?.removeEventListener?.('change', handleSystemThemeChange)
  mediaQuery?.addEventListener?.('change', handleSystemThemeChange)
}

export function setThemePreference(preference: ThemePreference) {
  themePreference.value = preference
  persistPreference(preference)
  applyTheme()
}

export function useTheme() {
  return {
    themePreference,
    resolvedTheme,
    setThemePreference,
  }
}
