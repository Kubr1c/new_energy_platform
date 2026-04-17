/**
 * 字段对比检查工具
 * 用于检查API返回数据与表格字段的对应关系
 */

/**
 * 表格字段配置
 */
export const TABLE_FIELDS = {
  id: {
    label: 'ID',
    prop: 'id',
    type: 'number',
    required: true,
    description: '调度记录的唯一标识'
  },
  schedule_date: {
    label: '调度日期',
    prop: 'schedule_date',
    type: 'string',
    required: true,
    description: '调度计划的日期'
  },
  total_cost: {
    label: '总成本(元)',
    prop: 'total_cost',
    type: 'number',
    required: true,
    description: '调度的总成本'
  },
  abandon_rate: {
    label: '弃电率',
    prop: 'abandon_rate',
    type: 'number',
    required: true,
    description: '弃电率（小数形式，如0.04表示4%）'
  },
  efficiency: {
    label: '调度效率',
    prop: 'efficiency',
    type: 'number',
    required: false,
    computed: true,
    description: '计算得出的调度效率'
  },
  total_charge: {
    label: '总充电量(MWh)',
    prop: 'total_charge',
    type: 'number',
    required: false,
    computed: true,
    description: '计算得出的总充电量'
  },
  total_discharge: {
    label: '总放电量(MWh)',
    prop: 'total_discharge',
    type: 'number',
    required: false,
    computed: true,
    description: '计算得出的总放电量'
  },
  created_at: {
    label: '创建时间',
    prop: 'created_at',
    type: 'string',
    required: true,
    description: '记录创建时间'
  },
  // 数组字段
  charge_plan: {
    label: '充电计划',
    prop: 'charge_plan',
    type: 'array',
    required: false,
    description: '24小时充电计划数组'
  },
  discharge_plan: {
    label: '放电计划',
    prop: 'discharge_plan',
    type: 'array',
    required: false,
    description: '24小时放电计划数组'
  },
  soc_curve: {
    label: 'SOC曲线',
    prop: 'soc_curve',
    type: 'array',
    required: false,
    description: '24小时SOC曲线数组'
  }
}

/**
 * 检查数据字段完整性
 * @param {Object} record - 单条记录
 * @returns {Object} 检查结果
 */
export function checkFieldCompleteness(record) {
  const results = {
    total: 0,
    present: 0,
    missing: [],
    invalid: [],
    computed: [],
    details: {}
  }

  Object.entries(TABLE_FIELDS).forEach(([field, config]) => {
    results.total++
    
    const value = record[field]
    const exists = field in record
    const isNull = value === null
    const isUndefined = value === undefined
    const isValidType = typeof value === config.type || (config.type === 'array' && Array.isArray(value))
    
    results.details[field] = {
      label: config.label,
      prop: config.prop,
      expectedType: config.type,
      actualType: typeof value,
      exists,
      value,
      isNull,
      isUndefined,
      isValidType,
      isComputed: config.computed || false,
      required: config.required || false,
      description: config.description
    }

    if (exists && !isNull && !isUndefined && isValidType) {
      results.present++
    } else if (config.computed) {
      results.computed.push(field)
    } else if (!exists) {
      results.missing.push(field)
    } else {
      results.invalid.push(field)
    }
  })

  return results
}

/**
 * 生成字段检查报告
 * @param {Object} checkResult - 检查结果
 * @returns {string} 格式化的报告
 */
export function generateFieldReport(checkResult) {
  let report = `📊 字段完整性检查报告\n\n`
  report += `总计字段: ${checkResult.total}\n`
  report += `存在字段: ${checkResult.present}\n`
  report += `缺失字段: ${checkResult.missing.length}\n`
  report += `无效字段: ${checkResult.invalid.length}\n`
  report += `计算字段: ${checkResult.computed.length}\n\n`

  if (checkResult.missing.length > 0) {
    report += `❌ 缺失字段:\n`
    checkResult.missing.forEach(field => {
      const config = TABLE_FIELDS[field]
      report += `  - ${config.label} (${field}): ${config.description}\n`
    })
  }

  if (checkResult.invalid.length > 0) {
    report += `⚠️  无效字段:\n`
    checkResult.invalid.forEach(field => {
      const config = TABLE_FIELDS[field]
      const detail = checkResult.details[field]
      report += `  - ${config.label} (${field}): 期望${config.expectedType}, 实际${detail.actualType}\n`
    })
  }

  if (checkResult.computed.length > 0) {
    report += `🔧 计算字段:\n`
    checkResult.computed.forEach(field => {
      const config = TABLE_FIELDS[field]
      report += `  - ${config.label} (${field}): ${config.description}\n`
    })
  }

  report += `\n📋 详细字段信息:\n`
  Object.entries(checkResult.details).forEach(([field, detail]) => {
    const status = detail.exists ? '✅' : (detail.isComputed ? '🔧' : '❌')
    const valueDisplay = detail.value === null ? 'null' : 
                       detail.value === undefined ? 'undefined' : 
                       Array.isArray(detail.value) ? `Array[${detail.value.length}]` : 
                       `${detail.actualType}(${detail.value})`
    
    report += `  ${status} ${detail.label} (${field}): ${valueDisplay}\n`
  })

  return report
}

/**
 * 验证弃电率字段
 * @param {*} abandonRate - 弃电率值
 * @returns {Object} 验证结果
 */
export function validateAbandonRate(abandonRate) {
  const result = {
    isValid: false,
    value: null,
    percentage: null,
    formatted: null,
    issues: []
  }

  // 类型检查
  if (typeof abandonRate !== 'number') {
    result.issues.push('弃电率不是数字类型')
    return result
  }

  result.value = abandonRate
  result.percentage = abandonRate * 100
  result.formatted = `${result.percentage.toFixed(2)}%`

  // 范围检查
  if (abandonRate < 0) {
    result.issues.push('弃电率不能为负数')
  } else if (abandonRate > 1) {
    result.issues.push('弃电率不能大于1（100%）')
  }

  // 合理性检查
  if (abandonRate > 0.5) {
    result.issues.push('弃电率超过50%，可能数据有误')
  }

  result.isValid = result.issues.length === 0
  return result
}

/**
 * 创建数据对比表格
 * @param {Object} apiData - API返回的数据
 * @param {Object} tableData - 表格显示的数据
 * @returns {Array} 对比结果
 */
export function createComparisonTable(apiData, tableData) {
  const comparison = []
  
  Object.entries(TABLE_FIELDS).forEach(([field, config]) => {
    const apiValue = apiData[field]
    const tableValue = tableData[field]
    
    comparison.push({
      field,
      label: config.label,
      apiValue,
      tableValue,
      isMatch: JSON.stringify(apiValue) === JSON.stringify(tableValue),
      type: config.type,
      isComputed: config.computed || false
    })
  })

  return comparison
}
