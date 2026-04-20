/**
 * 路由配置文件
 * 定义应用的路由结构和权限控制
 */

import { createRouter, createWebHistory } from 'vue-router'
import store from '../store'

/**
 * 路由配置数组
 * 包含应用的所有页面路由
 */
const routes = [
  {
    path: '/',
    redirect: '/map',
    /**
     * 根路径重定向到地图页面
     */
  },
  {
    path: '/map',
    name: 'MapScreen',
    component: () => import('../views/MapScreen.vue'),
    meta: { requiresAuth: true },
    /**
     * 地图页面
     * @requiresAuth true - 需要登录
     */
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
    /**
     * 登录页面
     * @requiresAuth false - 无需登录
     */
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true },
    /**
     * 仪表盘页面
     * @requiresAuth true - 需要登录
     */
  },
  {
    path: '/data',
    name: 'Data',
    component: () => import('../views/Data.vue'),
    meta: { requiresAuth: true },
    /**
     * 数据管理页面
     * @requiresAuth true - 需要登录
     */
  },
  {
    path: '/predict',
    name: 'Predict',
    component: () => import('../views/Predict.vue'),
    meta: { requiresAuth: true },
    /**
     * 预测分析页面
     * @requiresAuth true - 需要登录
     */
  },
  {
    path: '/dispatch',
    name: 'Dispatch',
    component: () => import('../views/Dispatch.vue'),
    meta: { requiresAuth: true },
    /**
     * 调度管理页面
     * @requiresAuth true - 需要登录
     */
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History.vue'),
    meta: { requiresAuth: true },
    /**
     * 历史记录页面
     * @requiresAuth true - 需要登录
     */
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    /**
     * 系统设置页面
     * @requiresAuth true - 需要登录
     * @requiresAdmin true - 需要管理员权限
     */
  },
  {
    path: '/strategy',
    name: 'StrategyConfig',
    component: () => import('../views/StrategyConfig.vue'),
    meta: { requiresAuth: true },
    /**
     * 策略配置页面
     * @requiresAuth true - 需要登录
     */
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('../views/UserManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    /**
     * 用户管理页面
     * @requiresAuth true - 需要登录
     * @requiresAdmin true - 需要管理员权限
     */
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('../views/Analysis.vue'),
    meta: { requiresAuth: true },
    /**
     * 数据分析页面
     * @requiresAuth true - 需要登录
     */
  },
  {
    path: '/integrated',
    name: 'IntegratedDashboard',
    component: () => import('../views/IntegratedDashboard.vue'),
    meta: { requiresAuth: true },
    /**
     * 综合仪表盘页面
     * @requiresAuth true - 需要登录
     */
  }
]

/**
 * 创建路由实例
 */
const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

/**
 * 路由守卫
 * 处理页面访问权限控制
 * 
 * @param {Object} to - 目标路由
 * @param {Object} from - 来源路由
 * @param {Function} next - 继续导航的回调函数
 */
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

/**
 * 导出路由实例
 */
export default router
