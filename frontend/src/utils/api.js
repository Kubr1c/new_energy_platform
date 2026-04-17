/**
 * API工具函数
 * 统一处理API调用和错误
 */

import axios from 'axios'

/**
 * 通用API请求方法
 * @param {string} method - HTTP方法
 * @param {string} url - 请求URL
 * @param {object} data - 请求数据
 * @param {object} config - 额外配置
 * @returns {Promise} API响应
 */
export async function apiRequest(method, url, data = null, config = {}) {
  try {
    console.log(`API请求: ${method.toUpperCase()} ${url}`, data)
    
    const response = await axios({
      method,
      url,
      data,
      ...config
    })
    
    console.log(`API响应:`, response.data)
    
    // 检查响应格式
    if (response.data && typeof response.data.code === 'number') {
      if (response.data.code === 200) {
        return {
          success: true,
          data: response.data.data,
          message: response.data.message
        }
      } else {
        return {
          success: false,
          data: null,
          message: response.data.message || '请求失败'
        }
      }
    } else {
      console.error('API响应格式错误:', response.data)
      return {
        success: false,
        data: null,
        message: '响应格式错误'
      }
    }
  } catch (error) {
    console.error(`API请求失败: ${method.toUpperCase()} ${url}`, error)
    return {
      success: false,
      data: null,
      message: error.message || '网络请求失败'
    }
  }
}

/**
 * GET请求
 */
export function apiGet(url, params = {}, config = {}) {
  return apiRequest('get', url, null, { ...config, params })
}

/**
 * POST请求
 */
export function apiPost(url, data, config = {}) {
  return apiRequest('post', url, data, config)
}

/**
 * PUT请求
 */
export function apiPut(url, data, config = {}) {
  return apiRequest('put', url, data, config)
}

/**
 * DELETE请求
 */
export function apiDelete(url, config = {}) {
  return apiRequest('delete', url, null, config)
}

/**
 * 格式化数字显示
 */
export function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '0'
  return Number(value).toFixed(decimals)
}

/**
 * 格式化百分比显示
 */
export function formatPercent(value, decimals = 2) {
  if (value === null || value === undefined) return '0%'
  return `${(Number(value) * 100).toFixed(decimals)}%`
}
