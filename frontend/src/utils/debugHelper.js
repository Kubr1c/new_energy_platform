/**
 * 调试辅助工具
 * 用于排查数据显示问题
 */

/**
 * 调试对象属性
 * @param {Object} obj - 要调试的对象
 * @param {string} name - 对象名称
 */
export function debugObject(obj, name = 'Object') {
  if (process.env.NODE_ENV === 'development') {
    console.log(`=== 调试 ${name} ===`)
    console.log('完整对象:', obj)
    
    if (obj && typeof obj === 'object') {
      Object.keys(obj).forEach(key => {
        const value = obj[key]
        const type = typeof value
        console.log(`${key}: ${type} = ${value}`)
        
        // 特别检查数字类型
        if (type === 'number') {
          console.log(`  - 数值: ${value}`)
          console.log(`  - 百分比: ${(value * 100).toFixed(2)}%`)
        }
      })
    }
    console.log(`=== 调试 ${name} 结束 ===\n`)
  }
}

/**
 * 调试数组对象
 * @param {Array} array - 要调试的数组
 * @param {string} name - 数组名称
 */
export function debugArray(array, name = 'Array') {
  if (process.env.NODE_ENV === 'development') {
    console.log(`=== 调试 ${name} ===`)
    console.log('数组长度:', array.length)
    
    if (array.length > 0) {
      console.log('第一个元素:', array[0])
      console.log('第一个元素的键:', Object.keys(array[0]))
    }
    console.log(`=== 调试 ${name} 结束 ===\n`)
  }
}

/**
 * 安全的数值转换
 * @param {*} value - 要转换的值
 * @param {number} defaultValue - 默认值
 * @returns {number} 转换后的数字
 */
export function safeNumber(value, defaultValue = 0) {
  if (value === null || value === undefined || value === '') {
    return defaultValue
  }
  
  const num = Number(value)
  return isNaN(num) ? defaultValue : num
}

/**
 * 格式化弃电率显示
 * @param {*} rate - 弃电率值
 * @returns {string} 格式化后的字符串
 */
export function formatAbandonRate(rate) {
  const numRate = safeNumber(rate, 0)
  const percentage = (numRate * 100).toFixed(2)
  return `${percentage}%`
}

/**
 * 获取弃电率类型
 * @param {*} rate - 弃电率值
 * @returns {string} 类型
 */
export function getAbandonRateType(rate) {
  const numRate = safeNumber(rate, 0)
  if (numRate < 0.02) return 'success'
  if (numRate < 0.05) return 'warning'
  return 'danger'
}

/**
 * 创建调试版本的表格列组件
 * @param {Function} originalColumn - 原始列组件
 * @param {string} fieldName - 字段名
 * @returns {Function} 增强后的列组件
 */
export function createDebugColumn(originalColumn, fieldName) {
  return {
    ...originalColumn,
    renderHeader: (params) => {
      // 添加调试信息到表头
      return [
        h('span', params.column.label),
        h('el-tooltip', {
          content: `调试字段: ${fieldName}`,
          placement: 'top'
        }, [
          h('el-icon', { style: 'margin-left: 5px; color: #409eff;' }, { icon: 'InfoFilled' })
        ])
      ]
    }
  }
}
