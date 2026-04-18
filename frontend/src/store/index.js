import { createStore } from 'vuex'
import axios from 'axios'

export default createStore({
  state: {
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    loading: false,
    sidebarCollapsed: false
  },
  
  getters: {
    isAuthenticated: state => !!state.token,
    user: state => state.user,
    isAdmin: state => state.user?.role === 'admin',
    loading: state => state.loading,
    sidebarCollapsed: state => state.sidebarCollapsed
  },
  
  mutations: {
    SET_TOKEN(state, token) {
      state.token = token
      if (token) {
        localStorage.setItem('token', token)
      } else {
        localStorage.removeItem('token')
      }
    },
    
    SET_USER(state, user) {
      state.user = user
      if (user) {
        localStorage.setItem('user', JSON.stringify(user))
      } else {
        localStorage.removeItem('user')
      }
    },
    
    SET_LOADING(state, loading) {
      state.loading = loading
    },
    
    TOGGLE_SIDEBAR(state) {
      state.sidebarCollapsed = !state.sidebarCollapsed
    }
  },
  
  actions: {
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
    
    async logout({ commit }) {
      commit('SET_TOKEN', null)
      commit('SET_USER', null)
    },
    
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
    
    toggleSidebar({ commit }) {
      commit('TOGGLE_SIDEBAR')
    }
  }
})
