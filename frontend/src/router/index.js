import { createRouter, createWebHistory } from 'vue-router'
import store from '../store'

const routes = [
  {
    path: '/',
    redirect: '/map'
  },
  {
    path: '/map',
    name: 'MapScreen',
    component: () => import('../views/MapScreen.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/data',
    name: 'Data',
    component: () => import('../views/Data.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/predict',
    name: 'Predict',
    component: () => import('../views/Predict.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/dispatch',
    name: 'Dispatch',
    component: () => import('../views/Dispatch.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/strategy',
    name: 'StrategyConfig',
    component: () => import('../views/StrategyConfig.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('../views/UserManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('../views/Analysis.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const user = store.getters.user
  
  // 免登录模式：所有 requiresAuth 页面均可直接访问
  // 仅保留管理员页面角色限制
  if (to.meta.requiresAdmin && user?.role !== 'admin') {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
