/**
 * 数据处理工具函数
 * 统一处理API响应和数据格式化
 */

/**
 * 检查API响应是否成功
 * @param {Object} response - API响应对象
 * @returns {boolean} 是否成功
 */
export function isApiSuccess(response) {
  return response && response.data && response.data.code === 200
}

/**
 * 从API响应中提取数据
 * @param {Object} response - API响应对象
 * @returns {Array|Object|null} 提取的数据
 */
export function extractApiData(response) {
  if (!isApiSuccess(response)) {
    return null
  }
  
  const data = response.data.data
  
  // 如果是数组，直接返回
  if (Array.isArray(data)) {
    return data
  }
  
  // 如果是对象，检查是否有data属性
  if (typeof data === 'object' && data !== null) {
    return data.data || data
  }
  
  return data
}

/**
 * 安全的数值格式化
 * @param {number|string|null|undefined} value - 要格式化的值
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的字符串
 */
export function safeFormatNumber(value, decimals = 2) {
  if (value === null || value === undefined || value === '') {
    return '0'
  }
  
  const num = Number(value)
  if (isNaN(num)) {
    return '0'
  }
  
  return num.toFixed(decimals)
}

/**
 * 安全的百分比格式化
 * @param {number|null|undefined} value - 要格式化的值
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的百分比字符串
 */
export function safeFormatPercent(value, decimals = 2) {
  if (value === null || value === undefined || value === '') {
    return '0.00%'
  }
  
  const num = Number(value)
  if (isNaN(num)) {
    return '0.00%'
  }
  
  return (num * 100).toFixed(decimals) + '%'
}

/**
 * 安全的数组访问
 * @param {Array} array - 数组
 * @param {number} index - 索引
 * @param {*} defaultValue - 默认值
 * @returns {*} 数组元素或默认值
 */
export function safeArrayAccess(array, index, defaultValue = 0) {
  if (!Array.isArray(array) || index < 0 || index >= array.length) {
    return defaultValue
  }
  
  return array[index]
}

/**
 * 检查并调度效率
 * @param {Object} record - 调度记录
 * @returns {number} 计算的效率值
 */
export function calculateDispatchEfficiency(record) {
  try {
    const baseEfficiency = 0.85
    const costFactor = Math.max(0, 1 - ((record.total_cost || 10000) - 10000) / 20000)
    const abandonFactor = Math.max(0, 1 - (record.abandon_rate || 0))
    
    return baseEfficiency * costFactor * abandonFactor
  } catch (error) {
    console.error('计算调度效率失败:', error)
    return 0.85 // 返回默认值
  }
}

/**
 * 生成24小时数据数组
 * @param {Array} data - 数据数组
 * @param {string} field - 字段名
 * @returns {Array} 24小时数据数组
 */
export function generate24HourData(data, field) {
  if (!Array.isArray(data)) {
    return Array(24).fill(0)
  }
  
  return Array.from({length: 24}, (_, i) => {
    const item = data[i]
    return item ? (item[field] || 0) : 0
  })
}

/**
 * 处理API错误
 * @param {Object} error - 错误对象
 * @param {string} defaultMessage - 默认错误消息
 * @returns {string} 错误消息
 */
export function handleApiError(error, defaultMessage = '请求失败') {
  if (error.response) {
    // HTTP错误
    return error.response.data?.message || `HTTP ${error.response.status} 错误`
  } else if (error.request) {
    // 网络错误
    return '网络连接失败'
  } else {
    // 其他错误
    return error.message || defaultMessage
  }
}

/**
 * 调试日志输出
 * @param {string} label - 标签
 * @param {*} data - 数据
 */
export function debugLog(label, data) {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[${label}]`, data)
  }
}

/**
 * 验证调度数据完整性
 * @param {Object} dispatchData - 调度数据
 * @returns {Object} 验证结果
 */
export function validateDispatchData(dispatchData) {
  const result = {
    isValid: true,
    errors: []
  }
  
  if (!dispatchData) {
    result.isValid = false
    result.errors.push('调度数据为空')
    return result
  }
  
  // 检查必需字段
  const requiredFields = ['id', 'schedule_date', 'total_cost', 'abandon_rate']
  for (const field of requiredFields) {
    if (!(field in dispatchData)) {
      result.isValid = false
      result.errors.push(`缺少必需字段: ${field}`)
    }
  }
  
  // 检查数组长度
  const arrayFields = ['charge_plan', 'discharge_plan', 'soc_curve']
  for (const field of arrayFields) {
    if (dispatchData[field] && !Array.isArray(dispatchData[field])) {
      result.isValid = false
      result.errors.push(`${field} 应该是数组`)
    }
  }
  
  return result
}
