import { defineConfig, presetUno, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [presetUno(), presetAttributify()],
  shortcuts: {
    'btn': 'appearance-none inline-flex items-center justify-center px-4 py-2 rounded-lg font-medium transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed select-none',
    'btn-primary': 'btn bg-[var(--color-brand)] text-[var(--color-text-inverse)] hover:bg-[var(--color-brand-hover)] active:bg-[var(--color-brand-active)]',
    'btn-danger': 'btn bg-[var(--color-danger)] text-white hover:opacity-90 active:opacity-85',
    'btn-outline': 'btn border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-brand)] hover:bg-[var(--color-brand-soft)] active:bg-[var(--color-surface-muted)]',
    'btn-ghost': 'btn text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-muted)] active:bg-[var(--color-border)]',
    'card': 'bg-[var(--color-surface)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded-xl shadow-sm p-6',
    'surface-inset': 'bg-[var(--color-surface-inset)] text-[var(--color-text-secondary)]',
    'surface-elevated': 'bg-[var(--color-surface-elevated)] text-[var(--color-text-primary)] border border-[var(--color-border)] shadow-sm',
    'input': 'w-full px-3 py-2 border border-[var(--color-border-strong)] rounded-lg bg-[var(--color-surface)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)] focus:border-transparent',
    'label': 'block text-sm font-medium text-[var(--color-text-secondary)] mb-1',
    'page-heading': 'text-xl font-bold text-[var(--color-text-primary)] mb-6',
    'app-page': 'min-h-screen flex flex-col bg-[var(--color-page)] text-[var(--color-text-primary)]',
  },
  safelist: [
    'bg-sky-600', 'bg-sky-700', 'bg-sky-800', 'bg-sky-50', 'bg-sky-100',
    'text-white', 'text-sky-600', 'text-sky-700',
    'bg-red-600', 'bg-red-700', 'text-red-500', 'text-red-600',
    'bg-green-100', 'bg-green-500', 'text-green-500', 'text-green-600', 'text-green-700',
    'bg-yellow-100', 'bg-yellow-500', 'text-yellow-500', 'text-yellow-600', 'text-yellow-700',
    'bg-orange-100', 'text-orange-500', 'text-orange-600', 'text-orange-700',
    'bg-gray-50', 'bg-gray-100', 'bg-gray-200', 'text-gray-400', 'text-gray-500', 'text-gray-600', 'text-gray-700', 'text-gray-800',
    'border-gray-200', 'border-gray-300', 'border-sky-200', 'border-sky-300', 'border-sky-500',
    'bg-blue-50', 'border-blue-500',
    'rounded-lg', 'rounded-xl', 'rounded-full',
    'shadow-sm',
    'px-3', 'px-4', 'py-1.5', 'py-2', 'py-3',
  ],
  theme: {
    colors: {
      brand: { primary: '#0EA5E9', danger: '#DC2626', warning: '#F59E0B', success: '#16A34A' },
    },
  },
})
