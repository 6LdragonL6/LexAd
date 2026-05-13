// Axios HTTP 客户端实例 —— 配置基础 URL、超时和错误拦截
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',  // API 基础路径，可通过环境变量覆盖
  timeout: 30000,                                            // 请求超时 30 秒
  headers: { 'Content-Type': 'application/json' },
})

// 响应拦截器：统一处理错误日志
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('[API Error]', message)
    return Promise.reject(error)
  },
)

export default apiClient
