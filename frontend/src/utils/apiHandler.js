/**
 * API响应处理工具
 * 统一处理不同格式的API响应
 */

/**
 * 从API响应中提取数据
 * 支持两种格式：
 * 1. 直接数组格式: [data1, data2, ...]
 * 2. 包装格式: {code: 200, data: [data1, data2, ...]}
 * 
 * @param {Object} response - axios响应对象
 * @returns {Array|null} 提取的数据数组
 */
export function extractDataArray(response) {
  if (!response || !response.data) {
    console.error('API响应为空')
    return null
  }
  
  const responseData = response.data
  
  // 情况1: 直接返回数组格式
  if (Array.isArray(responseData)) {
    console.log('API返回直接数组格式，数据条数:', responseData.length)
    return responseData
  }
  
  // 情况2: 包装格式 {code: 200, data: [...]}
  if (responseData && responseData.code === 200 && Array.isArray(responseData.data)) {
    console.log('API返回包装格式，数据条数:', responseData.data.length)
    return responseData.data
  }
  
  // 情况3: 包装格式但有错误
  if (responseData && responseData.code !== 200) {
    console.error('API返回错误:', responseData.message || '未知错误')
    return null
  }
  
  console.error('API响应格式无法识别:', responseData)
  return null
}

/**
 * 检查API响应是否成功
 * @param {Object} response - axios响应对象
 * @returns {boolean} 是否成功
 */
export function isApiSuccess(response) {
  if (!response || !response.data) {
    return false
  }
  
  const responseData = response.data
  
  // 直接数组格式视为成功
  if (Array.isArray(responseData)) {
    return true
  }
  
  // 包装格式检查code
  if (responseData && responseData.code === 200) {
    return true
  }
  
  return false
}

/**
 * 获取API错误消息
 * @param {Object} response - axios响应对象
 * @returns {string} 错误消息
 */
export function getApiErrorMessage(response) {
  if (!response || !response.data) {
    return '未知错误'
  }
  
  const responseData = response.data
  
  // 直接数组格式通常不会返回错误
  if (Array.isArray(responseData)) {
    return '请求成功'
  }
  
  // 包装格式
  if (responseData) {
    return responseData.message || '未知错误'
  }
  
  return '未知错误'
}

/**
 * 安全的数据映射处理
 * @param {Array} dataArray - 数据数组
 * @param {Function} mapFn - 映射函数
 * @returns {Array} 处理后的数组
 */
export function safeMap(dataArray, mapFn) {
  if (!Array.isArray(dataArray)) {
    console.error('期望数组但得到:', typeof dataArray)
    return []
  }
  
  try {
    return dataArray.map(mapFn)
  } catch (error) {
    console.error('数据映射失败:', error)
    return []
  }
}

/**
 * 统一的API调用包装器
 * @param {Function} apiCall - API调用函数
 * @param {Object} options - 选项
 * @returns {Promise} 包装后的Promise
 */
export function wrapApiCall(apiCall, options = {}) {
  const {
    errorMessage = 'API调用失败',
    showLoading = false,
    loadingRef = null
  } = options
  
  return async (...args) => {
    try {
      if (showLoading && loadingRef) {
        loadingRef.value = true
      }
      
      const response = await apiCall(...args)
      
      if (isApiSuccess(response)) {
        const data = extractDataArray(response)
        return {
          success: true,
          data: data,
          message: '请求成功'
        }
      } else {
        return {
          success: false,
          data: null,
          message: getApiErrorMessage(response)
        }
      }
    } catch (error) {
      console.error('API调用异常:', error)
      return {
        success: false,
        data: null,
        message: error.message || errorMessage
      }
    } finally {
      if (showLoading && loadingRef) {
        loadingRef.value = false
      }
    }
  }
}

/**
 * 调试输出API响应
 * @param {string} apiName - API名称
 * @param {Object} response - 响应对象
 */
export function debugApiResponse(apiName, response) {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[${apiName}] API响应:`, response.data)
    
    if (Array.isArray(response.data)) {
      console.log(`[${apiName}] 直接数组格式，条数:`, response.data.length)
    } else if (response.data && response.data.code === 200) {
      console.log(`[${apiName}] 包装格式，条数:`, response.data.data?.length || 0)
    } else {
      console.log(`[${apiName}] 响应格式错误:`, response.data)
    }
  }
}
