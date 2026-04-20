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

/**
 * 地图站点API
 */

/**
 * 获取站点列表
 * @param {string} adcode - 行政区划代码
 * @param {string} level - 层级（nation, province, city）
 * @param {string} status - 状态筛选（active, inactive, all）
 * @returns {Promise} 站点列表
 */
export async function getSites(adcode = null, level = null, status = 'active') {
  const params = {}
  if (adcode) params.adcode = adcode
  if (level) params.level = level
  if (status && status !== 'all') params.status = status
  return apiGet('/api/map/sites', params)
}

/**
 * 获取单个站点详情
 * @param {number} id - 站点ID
 * @returns {Promise} 站点详情
 */
export async function getSite(id) {
  return apiGet(`/api/map/sites/${id}`)
}

/**
 * 创建新站点
 * @param {object} siteData - 站点数据
 * @returns {Promise} 创建结果
 */
export async function createSite(siteData) {
  return apiPost('/api/map/sites', siteData)
}

/**
 * 更新站点
 * @param {number} id - 站点ID
 * @param {object} updateData - 更新数据
 * @returns {Promise} 更新结果
 */
export async function updateSite(id, updateData) {
  return apiPut(`/api/map/sites/${id}`, updateData)
}

/**
 * 删除站点
 * @param {number} id - 站点ID
 * @returns {Promise} 删除结果
 */
export async function deleteSite(id) {
  return apiDelete(`/api/map/sites/${id}`)
}

/**
 * 获取地图统计信息
 * @returns {Promise} 统计信息
 */
export async function getMapStats() {
  return apiGet('/api/map/stats')
}

/**
 * 获取附近站点
 * @param {number} lng - 经度
 * @param {number} lat - 纬度
 * @param {number} radius - 半径（公里），默认50
 * @returns {Promise} 附近站点列表
 */
export async function getNearbySites(lng, lat, radius = 50) {
  return apiGet('/api/map/nearby', { lng, lat, radius })
}
