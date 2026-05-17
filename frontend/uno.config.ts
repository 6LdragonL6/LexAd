import { defineConfig, presetUno, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [presetUno(), presetAttributify()],
  shortcuts: {
    'btn': 'appearance-none inline-flex items-center justify-center px-4 py-2 rounded-lg font-medium transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed select-none',
    'btn-primary': 'btn bg-sky-600 text-white hover:bg-sky-700 active:bg-sky-800',
    'btn-danger': 'btn bg-red-600 text-white hover:bg-red-700 active:bg-red-800',
    'btn-outline': 'btn border border-sky-300 bg-white text-sky-600 hover:bg-sky-50 active:bg-sky-100',
    'btn-ghost': 'btn text-gray-500 hover:bg-gray-100 active:bg-gray-200',
    'card': 'bg-white rounded-xl shadow-sm border border-gray-200 p-6',
    'input': 'w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent',
    'label': 'block text-sm font-medium text-gray-700 mb-1',
    'page-heading': 'text-xl font-bold text-gray-800 mb-6',
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
