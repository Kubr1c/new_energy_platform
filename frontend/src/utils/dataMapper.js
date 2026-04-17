/**
 * 数据映射检查工具
 * 用于验证API返回数据与表格字段的对应关系
 */

/**
 * 检查调度记录数据完整性
 * @param {Array} data - 调度数据数组
 * @returns {Object} 检查结果
 */
export function validateDispatchData(data) {
  if (!Array.isArray(data)) {
    return {
      isValid: false,
      error: '数据不是数组格式',
      details: null
    }
  }

  if (data.length === 0) {
    return {
      isValid: true,
      error: null,
      details: { message: '数据为空数组', count: 0 }
    }
  }

  const expectedFields = [
    'id',
    'schedule_date', 
    'total_cost',
    'cost', // API可能返回的字段名
    'abandon_rate',
    'charge_plan',
    'discharge_plan',
    'soc_curve',
    'created_at'
  ]

  const firstRecord = data[0]
  const actualFields = Object.keys(firstRecord)
  
  const missingFields = expectedFields.filter(field => !actualFields.includes(field))
  const extraFields = actualFields.filter(field => !expectedFields.includes(field))
  
  const fieldAnalysis = expectedFields.map(field => {
    let value = firstRecord[field]
    let exists = actualFields.includes(field)
    
    // 特殊处理：cost字段映射到total_cost
    if (field === 'total_cost' && !exists && 'cost' in firstRecord) {
      value = firstRecord.cost
      exists = true
    }
    
    return {
      field,
      exists,
      value,
      type: typeof value,
      isNull: value === null,
      isUndefined: value === undefined,
      isArray: Array.isArray(value),
      arrayLength: Array.isArray(value) ? value.length : null,
      isMapped: field === 'total_cost' && 'cost' in firstRecord
    }
  })

  return {
    isValid: missingFields.length === 0,
    error: missingFields.length > 0 ? `缺少字段: ${missingFields.join(', ')}` : null,
    details: {
      count: data.length,
      expectedFields,
      actualFields,
      missingFields,
      extraFields,
      fieldAnalysis,
      sampleRecord: firstRecord
    }
  }
}

/**
 * 生成数据映射报告
 * @param {Object} validationResult - 验证结果
 * @returns {string} 格式化的报告
 */
export function generateDataReport(validationResult) {
  if (!validationResult.isValid) {
    return `❌ 数据验证失败: ${validationResult.error}`
  }

  const { details } = validationResult
  let report = `✅ 数据验证通过\n\n`
  report += `📊 数据概览:\n`
  report += `  - 记录数量: ${details.count}\n`
  report += `  - 期望字段数: ${details.expectedFields.length}\n`
  report += `  - 实际字段数: ${details.actualFields.length}\n\n`
  
  if (details.missingFields.length > 0) {
    report += `⚠️  缺少字段: ${details.missingFields.join(', ')}\n\n`
  }
  
  if (details.extraFields.length > 0) {
    report += `ℹ️  额外字段: ${details.extraFields.join(', ')}\n\n`
  }
  
  report += `📋 字段详细分析:\n`
  details.fieldAnalysis.forEach(field => {
    const status = field.exists ? '✅' : '❌'
    const valueInfo = field.isArray 
      ? `Array[${field.arrayLength}]` 
      : field.isNull 
        ? 'null' 
        : field.isUndefined 
          ? 'undefined' 
          : `${field.type}(${field.value})`
    
    const mappingInfo = field.isMapped ? ' 🔄 从cost字段映射' : ''
    report += `  ${status} ${field.field}: ${valueInfo}${mappingInfo}\n`
  })
  
  report += `\n📝 示例记录:\n`
  report += JSON.stringify(details.sampleRecord, null, 2)
  
  return report
}

/**
 * 检查表格字段映射
 * @param {Object} record - 单条记录
 * @returns {Object} 映射检查结果
 */
export function checkTableMapping(record) {
  const tableColumns = {
    'ID': 'id',
    '调度日期': 'schedule_date',
    '总成本(元)': 'total_cost',
    '弃电率': 'abandon_rate',
    '调度效率': 'efficiency', // 计算字段
    '总充电量(MWh)': 'total_charge', // 计算字段
    '总放电量(MWh)': 'total_discharge', // 计算字段
    '创建时间': 'created_at'
  }

  const mappingResults = Object.entries(tableColumns).map(([label, field]) => {
    const value = record[field]
    const exists = field in record
    const isComputed = ['efficiency', 'total_charge', 'total_discharge'].includes(field)
    
    return {
      label,
      field,
      exists,
      isComputed,
      value,
      type: typeof value,
      displayValue: isComputed ? '[计算字段]' : value
    }
  })

  return {
    tableColumns,
    mappingResults,
    hasAllFields: mappingResults.every(result => result.exists || result.isComputed)
  }
}

/**
 * 格式化数值显示
 * @param {*} value - 原始值
 * @param {number} decimals - 小数位数
 * @param {string} suffix - 后缀
 * @returns {string} 格式化后的值
 */
export function formatDisplayValue(value, decimals = 2, suffix = '') {
  if (value === null || value === undefined) {
    return `0${suffix}`
  }
  
  const num = Number(value)
  if (isNaN(num)) {
    return `0${suffix}`
  }
  
  return `${num.toFixed(decimals)}${suffix}`
}

/**
 * 创建调试版本的表格显示
 * @param {Array} data - 数据数组
 * @returns {Array} 调试版本的数据
 */
export function createDebugData(data) {
  return data.map((record, index) => {
    const debugRecord = { ...record }
    
    // 添加调试字段
    debugRecord._debugIndex = index + 1
    debugRecord._debugAbandonRatePercent = formatDisplayValue(record.abandon_rate, 2, '%')
    debugRecord._debugCostFormatted = formatDisplayValue(record.total_cost, 2, '元')
    debugRecord._debugEfficiencyCalculated = record.efficiency ? formatDisplayValue(record.efficiency * 100, 1, '%') : '[未计算]'
    
    // 检查数组字段
    if (Array.isArray(record.charge_plan)) {
      debugRecord._debugChargePlanSum = record.charge_plan.reduce((sum, val) => sum + (val || 0), 0).toFixed(2)
    }
    
    if (Array.isArray(record.discharge_plan)) {
      debugRecord._debugDischargePlanSum = record.discharge_plan.reduce((sum, val) => sum + (val || 0), 0).toFixed(2)
    }
    
    return debugRecord
  })
}
