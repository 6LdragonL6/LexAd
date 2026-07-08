import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { initializeTheme } from './composables/useTheme'
import '@unocss/reset/tailwind.css'
import 'uno.css'
import './styles/main.css'

initializeTheme()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
