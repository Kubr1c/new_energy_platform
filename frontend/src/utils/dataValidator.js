/**
 * 数据格式验证工具
 * 验证后端返回的数据格式是否符合前端期望
 */

/**
 * 验证调度历史数据格式
 * @param {Array} data - API返回的数据数组
 * @returns {Object} 验证结果
 */
export function validateDispatchHistoryFormat(data) {
  const result = {
    isValid: true,
    errors: [],
    warnings: [],
    sampleData: null,
    formatAnalysis: {}
  }

  if (!Array.isArray(data)) {
    result.isValid = false
    result.errors.push('数据不是数组格式')
    return result
  }

  if (data.length === 0) {
    result.warnings.push('数据数组为空')
    return result
  }

  const sampleRecord = data[0]
  result.sampleData = sampleRecord

  // 检查必需字段
  const requiredFields = [
    { name: 'id', type: 'number', required: true },
    { name: 'schedule_date', type: 'string', required: true },
    { name: 'charge_plan', type: 'array', required: true },
    { name: 'discharge_plan', type: 'array', required: true },
    { name: 'soc_curve', type: 'array', required: true },
    { name: 'abandon_rate', type: 'number', required: true },
    { name: 'cost', type: 'number', required: true }, // 注意：是cost不是total_cost
    { name: 'created_at', type: 'string', required: true }
  ]

  requiredFields.forEach(field => {
    const value = sampleRecord[field.name]
    const exists = field.name in sampleRecord
    const actualType = typeof value
    const isArray = Array.isArray(value)
    
    const typeMatch = field.type === 'array' ? isArray : actualType === field.type
    const valueValid = value !== null && value !== undefined

    if (!exists) {
      result.errors.push(`缺少必需字段: ${field.name}`)
      result.isValid = false
    } else if (!valueValid) {
      result.errors.push(`字段值为空: ${field.name}`)
      result.isValid = false
    } else if (!typeMatch) {
      result.errors.push(`字段类型不匹配: ${field.name} 期望${field.type}, 实际${actualType}`)
      result.isValid = false
    }

    result.formatAnalysis[field.name] = {
      exists,
      type: actualType,
      expectedType: field.type,
      typeMatch,
      value,
      isArray,
      arrayLength: isArray ? value.length : null
    }
  })

  // 检查数组字段长度
  const arrayFields = ['charge_plan', 'discharge_plan', 'soc_curve']
  arrayFields.forEach(fieldName => {
    const field = result.formatAnalysis[fieldName]
    if (field.isArray && field.arrayLength !== 24) {
      result.warnings.push(`${fieldName}数组长度不是24，实际长度: ${field.arrayLength}`)
    }
  })

  // 检查数值范围
  if (result.formatAnalysis.abandon_rate && result.formatAnalysis.abandon_rate.exists) {
    const rate = result.formatAnalysis.abandon_rate.value
    if (rate < 0 || rate > 1) {
      result.errors.push(`弃电率超出有效范围: ${rate}`)
      result.isValid = false
    }
  }

  if (result.formatAnalysis.cost && result.formatAnalysis.cost.exists) {
    const cost = result.formatAnalysis.cost.value
    if (cost < 0) {
      result.errors.push(`成本不能为负数: ${cost}`)
      result.isValid = false
    }
  }

  return result
}

/**
 * 生成格式验证报告
 * @param {Object} validationResult - 验证结果
 * @returns {string} 格式化的报告
 */
export function generateFormatReport(validationResult) {
  let report = `📊 数据格式验证报告\n\n`
  
  report += `验证状态: ${validationResult.isValid ? '✅ 通过' : '❌ 失败'}\n`
  report += `错误数量: ${validationResult.errors.length}\n`
  report += `警告数量: ${validationResult.warnings.length}\n\n`

  if (validationResult.errors.length > 0) {
    report += `❌ 错误详情:\n`
    validationResult.errors.forEach((error, index) => {
      report += `  ${index + 1}. ${error}\n`
    })
  }

  if (validationResult.warnings.length > 0) {
    report += `⚠️  警告详情:\n`
    validationResult.warnings.forEach((warning, index) => {
      report += `  ${index + 1}. ${warning}\n`
    })
  }

  report += `\n📋 字段格式分析:\n`
  Object.entries(validationResult.formatAnalysis).forEach(([fieldName, analysis]) => {
    const status = analysis.exists ? '✅' : '❌'
    const typeStatus = analysis.typeMatch ? '✅' : '❌'
    const valueDisplay = analysis.isArray 
      ? `Array[${analysis.arrayLength}]`
      : analysis.value === null 
        ? 'null' 
        : `${analysis.type}(${analysis.value})`
    
    report += `  ${status} ${fieldName}: ${valueDisplay} (类型: ${typeStatus} ${analysis.expectedType})\n`
  })

  if (validationResult.sampleData) {
    report += `\n📝 示例数据:\n`
    report += JSON.stringify(validationResult.sampleData, null, 2)
  }

  return report
}

/**
 * 检查数据是否符合预期格式
 * @param {Array} data - 数据数组
 * @returns {Object} 检查结果
 */
export function checkExpectedFormat(data) {
  const expectedFormat = {
    id: 'number',
    schedule_date: 'string (YYYY-MM-DD)',
    charge_plan: 'array (24 numbers)',
    discharge_plan: 'array (24 numbers)',
    soc_curve: 'array (24 numbers)',
    abandon_rate: 'number (0-1)',
    cost: 'number (>0)',
    created_at: 'string (ISO datetime)'
  }

  const checkResult = {
    isExpected: true,
    mismatches: [],
    details: {}
  }

  if (!Array.isArray(data) || data.length === 0) {
    checkResult.isExpected = false
    checkResult.mismatches.push('数据为空或格式错误')
    return checkResult
  }

  const sample = data[0]
  Object.entries(expectedFormat).forEach(([field, expected]) => {
    const actual = sample[field]
    const actualType = Array.isArray(actual) ? 'array' : typeof actual
    const actualValue = Array.isArray(actual) ? `[${actual.length} items]` : String(actual)
    
    const isMatch = 
      (field === 'id' && actualType === 'number') ||
      (field === 'schedule_date' && typeof actual === 'string') ||
      (field === 'charge_plan' && actualType === 'array') ||
      (field === 'discharge_plan' && actualType === 'array') ||
      (field === 'soc_curve' && actualType === 'array') ||
      (field === 'abandon_rate' && actualType === 'number') ||
      (field === 'cost' && actualType === 'number') ||
      (field === 'created_at' && typeof actual === 'string')

    if (!isMatch) {
      checkResult.isExpected = false
      checkResult.mismatches.push(`${field}: 期望${expected}, 实际${actualType}(${actualValue})`)
    }

    checkResult.details[field] = {
      expected,
      actual: actualValue,
      actualType,
      isMatch
    }
  })

  return checkResult
}

/**
 * 创建标准化的调度记录
 * @param {Object} rawRecord - 原始记录
 * @returns {Object} 标准化后的记录
 */
export function normalizeDispatchRecord(rawRecord) {
  const normalized = { ...rawRecord }
  
  // 字段映射：cost -> total_cost
  if ('cost' in rawRecord && !('total_cost' in rawRecord)) {
    normalized.total_cost = rawRecord.cost
    console.log('字段映射: cost -> total_cost, 值:', rawRecord.cost)
  }
  
  // 确保数值字段是数字类型
  if (typeof normalized.abandon_rate === 'string') {
    normalized.abandon_rate = parseFloat(normalized.abandon_rate)
  }
  
  if (typeof normalized.cost === 'string') {
    normalized.cost = parseFloat(normalized.cost)
    if ('total_cost' in normalized) {
      normalized.total_cost = parseFloat(normalized.total_cost)
    }
  }
  
  // 计算衍生字段
  if (Array.isArray(normalized.charge_plan)) {
    normalized.total_charge = normalized.charge_plan.reduce((sum, val) => sum + (val || 0), 0)
  }
  
  if (Array.isArray(normalized.discharge_plan)) {
    normalized.total_discharge = normalized.discharge_plan.reduce((sum, val) => sum + (val || 0), 0)
  }
  
  return normalized
}
