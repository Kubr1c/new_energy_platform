/**
 * Vuex 状态管理存储
 * 管理用户认证、全局状态和UI状态
 */

import { createStore } from 'vuex'
import axios from 'axios'

/**
 * 创建并导出Vuex store实例
 */
export default createStore({
  /**
   * 全局状态
   */
  state: {
    /**
     * 用户认证令牌
     * @type {string|null}
     */
    token: localStorage.getItem('token') || null,
    
    /**
     * 用户信息
     * @type {Object|null}
     */
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    
    /**
     * 加载状态
     * @type {boolean}
     */
    loading: false,
    
    /**
     * 侧边栏折叠状态
     * @type {boolean}
     */
    sidebarCollapsed: false
  },
  
  /**
   * 状态计算属性
   */
  getters: {
    /**
     * 检查用户是否已认证
     * @param {Object} state - 全局状态
     * @returns {boolean} 是否已认证
     */
    isAuthenticated: state => !!state.token,
    
    /**
     * 获取用户信息
     * @param {Object} state - 全局状态
     * @returns {Object|null} 用户信息
     */
    user: state => state.user,
    
    /**
     * 检查用户是否为管理员
     * @param {Object} state - 全局状态
     * @returns {boolean} 是否为管理员
     */
    isAdmin: state => state.user?.role === 'admin',
    
    /**
     * 获取加载状态
     * @param {Object} state - 全局状态
     * @returns {boolean} 加载状态
     */
    loading: state => state.loading,
    
    /**
     * 获取侧边栏折叠状态
     * @param {Object} state - 全局状态
     * @returns {boolean} 侧边栏折叠状态
     */
    sidebarCollapsed: state => state.sidebarCollapsed
  },
  
  /**
   * 同步状态更新方法
   */
  mutations: {
    /**
     * 设置认证令牌
     * @param {Object} state - 全局状态
     * @param {string|null} token - 认证令牌
     */
    SET_TOKEN(state, token) {
      state.token = token
      if (token) {
        localStorage.setItem('token', token)
      } else {
        localStorage.removeItem('token')
      }
    },
    
    /**
     * 设置用户信息
     * @param {Object} state - 全局状态
     * @param {Object|null} user - 用户信息
     */
    SET_USER(state, user) {
      state.user = user
      if (user) {
        localStorage.setItem('user', JSON.stringify(user))
      } else {
        localStorage.removeItem('user')
      }
    },
    
    /**
     * 设置加载状态
     * @param {Object} state - 全局状态
     * @param {boolean} loading - 加载状态
     */
    SET_LOADING(state, loading) {
      state.loading = loading
    },
    
    /**
     * 切换侧边栏折叠状态
     * @param {Object} state - 全局状态
     */
    TOGGLE_SIDEBAR(state) {
      state.sidebarCollapsed = !state.sidebarCollapsed
    }
  },
  
  /**
   * 异步操作方法
   */
  actions: {
    /**
     * 用户登录
     * @param {Object} context - Vuex上下文
     * @param {Object} credentials - 登录凭证
     * @param {string} credentials.username - 用户名
     * @param {string} credentials.password - 密码
     * @returns {Promise<Object>} 登录结果
     */
    async login({ commit }, credentials) {
      try {
        commit('SET_LOADING', true)
        const response = await axios.post('/api/auth/login', credentials)
        
        if (response.data.code === 200) {
          commit('SET_TOKEN', response.data.data.token)
          commit('SET_USER', response.data.data.user)
          return { success: true, data: response.data.data }
        } else {
          return { success: false, message: response.data.message }
        }
      } catch (error) {
        return { success: false, message: error.message || 'login failed' }
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    /**
     * 用户登出
     * @param {Object} context - Vuex上下文
     */
    async logout({ commit }) {
      commit('SET_TOKEN', null)
      commit('SET_USER', null)
    },
    
    /**
     * 用户注册
     * @param {Object} context - Vuex上下文
     * @param {Object} userData - 用户数据
     * @returns {Promise<Object>} 注册结果
     */
    async register({ commit }, userData) {
      try {
        commit('SET_LOADING', true)
        const response = await axios.post('/api/auth/register', userData)
        
        if (response.data.code === 200) {
          return { success: true, data: response.data.data }
        } else {
          return { success: false, message: response.data.message }
        }
      } catch (error) {
        return { success: false, message: error.message || 'registration failed' }
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    /**
     * 修改密码
     * @param {Object} context - Vuex上下文
     * @param {Object} passwordData - 密码数据
     * @returns {Promise<Object>} 修改结果
     */
    async changePassword({ commit }, passwordData) {
      try {
        commit('SET_LOADING', true)
        const response = await axios.post('/api/auth/change_password', passwordData)
        
        if (response.data.code === 200) {
          return { success: true, message: response.data.message }
        } else {
          return { success: false, message: response.data.message }
        }
      } catch (error) {
        return { success: false, message: error.message || 'password change failed' }
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    /**
     * 切换侧边栏状态
     * @param {Object} context - Vuex上下文
     */
    toggleSidebar({ commit }) {
      commit('TOGGLE_SIDEBAR')
    }
  }
})
