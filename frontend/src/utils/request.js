import axios from "axios"
import { ElMessage } from "element-plus"

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api",
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token")
  if (token && !config.skipAuth) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error?.response?.data?.error ||
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      "请求失败"

    if (!error?.config?.silentError) {
      ElMessage.error(message)
    }

    if (error?.response?.status === 401) {
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
      window.location.href = "/login"
    }

    return Promise.reject(error)
  },
)

export default request
