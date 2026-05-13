// Vue 应用入口 —— 创建应用实例，安装 Pinia 状态管理和 Vue Router，挂载到 #app
import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './styles/main.css'

const app = createApp(App)
app.use(createPinia())  // 全局状态管理
app.use(router)         // 路由
app.mount('#app')
