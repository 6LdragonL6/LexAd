import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  // Render 免费实例冷启动可能接近一分钟，首个登录请求需要更长容忍时间。
  timeout: 90_000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const requestUrl = String(err.config?.url || '')
    const hadSession = Boolean(err.config?.headers?.Authorization)
    if (err.response?.status === 401 && hadSession && !requestUrl.includes('/auth/login')) {
      localStorage.removeItem('access_token')
      if (window.location.pathname !== '/login') {
        window.location.replace('/login')
      }
    }
    return Promise.reject(err)
  },
)

export default client
