import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import axios from 'axios'

// 配置axios默认值
axios.defaults.baseURL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:5000'
axios.defaults.timeout = 120000 // 增加超时时间至 120 秒以容纳大规模模拟计算

// 请求拦截器
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
axios.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          router.push('/login')
          break
        case 403:
          ElementPlus.ElMessage.error('权限不足')
          break
        case 404:
          ElementPlus.ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElementPlus.ElMessage.error('服务器内部错误')
          break
        default:
          ElementPlus.ElMessage.error(error.response.data.message || '请求失败')
      }
    } else {
      ElementPlus.ElMessage.error('网络连接失败')
    }
    return Promise.reject(error)
  }
)

const app = createApp(App)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.config.globalProperties.$http = axios
app.use(store)
app.use(router)
app.use(ElementPlus)

app.mount('#app')
