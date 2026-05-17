import { defineConfig, presetUno, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [presetUno(), presetAttributify()],
  shortcuts: {
    'btn': 'px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-primary': 'btn bg-sky-600 text-white hover:bg-sky-700',
    'btn-danger': 'btn bg-red-600 text-white hover:bg-red-700',
    'btn-outline': 'btn border border-sky-300 bg-white text-sky-600 hover:bg-sky-50',
    'card': 'bg-white rounded-xl shadow-sm border border-gray-200 p-6',
    'input': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500',
  },
  theme: {
    colors: {
      brand: { primary: '#0EA5E9', danger: '#DC2626', warning: '#F59E0B', success: '#16A34A' },
    },
  },
})
