import { defineConfig, presetUno, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [presetUno(), presetAttributify()],
  shortcuts: {
    'btn': 'px-4 py-2 rounded-lg font-medium transition-colors',
    'btn-primary': 'btn bg-blue-600 text-white hover:bg-blue-700',
    'btn-danger': 'btn bg-red-600 text-white hover:bg-red-700',
    'btn-outline': 'btn border border-gray-300 hover:bg-gray-50',
    'card': 'bg-white rounded-xl shadow-sm border border-gray-200 p-6',
    'input': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
  },
  theme: {
    colors: {
      brand: { primary: '#2563EB', danger: '#DC2626', warning: '#F59E0B', success: '#16A34A' },
    },
  },
})
