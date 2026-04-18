<template>
  <div class="analysis-container">
    <div class="header-section">
      <h1 class="page-title">
        <el-icon><DataAnalysis /></el-icon>
        算法对比分析
      </h1>
      <p class="subtitle">深度学习时间序列预测模型与启发式调度算法横向性能对比</p>
    </div>

    <el-tabs v-model="activeTab" class="analysis-tabs" @tab-click="handleTabClick">
      
      <!-- 预测模型对比 Tab -->
      <el-tab-pane label="深度预测模型对比" name="model">
        <div class="control-panel">
          <div class="panel-header">
            <h3>模型选择与配置</h3>
            <el-button type="primary" @click="runModelComparison" :loading="modelLoading">
              运行全维对比
              <el-icon class="el-icon--right"><VideoPlay /></el-icon>
            </el-button>
          </div>
          <div class="panel-body">
            <el-checkbox-group v-model="selectedModels" class="glass-checkbox-group">
              <el-checkbox v-for="model in availableModels" :key="model.value" :label="model.value" border>
                {{ model.label }}
              </el-checkbox>
            </el-checkbox-group>

            <!-- 曲线对比控制栏 -->
            <div class="chart-controls">
              <div class="control-group">
                <span class="control-label">数据模式</span>
                <el-radio-group v-model="compareMode" size="small" @change="runModelComparison">
                  <el-radio-button label="realtime">
                    <el-icon style="margin-right:4px"><VideoPlay /></el-icon>实时数据
                  </el-radio-button>
                  <el-radio-button label="testset">
                    <el-icon style="margin-right:4px"><DataLine /></el-icon>历史测试集
                  </el-radio-button>
                </el-radio-group>
              </div>
              <div class="control-group">
                <span class="control-label">对比变量</span>
                <el-radio-group v-model="compareTarget" size="small" @change="renderWindLineChart">
                  <el-radio-button label="wind_power">风电功率</el-radio-button>
                  <el-radio-button label="pv_power">光伏功率</el-radio-button>
                  <el-radio-button label="load">系统负荷</el-radio-button>
                </el-radio-group>
              </div>
              <div class="context-info" v-if="contextInfo">
                <el-icon style="color:#56d4ff;margin-right:4px"><InfoFilled /></el-icon>
                <span>{{ contextInfo }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="charts-grid" v-loading="modelLoading" element-loading-text="全维数据张量计算中，请稍候..." element-loading-background="rgba(11, 15, 25, 0.7)">
          
          <!-- 性能雷达图 -->
          <div class="chart-card radar-card">
            <div class="card-header">
              <h4>
                <el-icon><Aim /></el-icon>
                综合性能评估雷达
              </h4>
            </div>
            <div class="card-body">
              <div ref="radarChartRef" class="chart-container"></div>
            </div>
          </div>
          
          <!-- 模型评价指标表格 -->
          <div class="chart-card table-card">
            <div class="card-header">
              <h4>
                <el-icon><DataLine /></el-icon>
                预测精度量化分析
              </h4>
            </div>
            <div class="card-body custom-table-wrapper">
              <el-table :data="modelMetricsList" style="width: 100%" :row-class-name="tableRowClassName">
                <el-table-column prop="modelName" label="模型名称" width="160"></el-table-column>
                <el-table-column prop="mape" label="MAPE (%)" align="center">
                  <template #default="scope">
                    <span :class="{'best-value': isBestMetric('mape', scope.row.mape)}">{{ scope.row.mape }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="rmse" label="RMSE" align="center">
                  <template #default="scope">
                    <span :class="{'best-value': isBestMetric('rmse', scope.row.rmse)}">{{ scope.row.rmse }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="mae" label="MAE" align="center">
                  <template #default="scope">
                    <span :class="{'best-value': isBestMetric('mae', scope.row.mae)}">{{ scope.row.mae }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <!-- 预测 vs 真实值对比曲线 -->
          <div class="chart-card full-width">
            <div class="card-header">
              <h4>
                <el-icon><TrendCharts /></el-icon>
                {{ chartTitle }}
              </h4>
              <!-- 模式标签 -->
              <el-tag
                :type="compareMode === 'realtime' ? 'success' : 'info'"
                size="small"
                effect="dark"
                style="margin-left:12px"
              >
                {{ compareMode === 'realtime' ? '实时数据对比' : '历史测试集对比' }}
              </el-tag>
            </div>
            <div class="card-body">
              <div ref="windLineChartRef" class="chart-container extended-height"></div>
            </div>
          </div>

        </div>
      </el-tab-pane>

      <!-- 优化算法对比 Tab -->
      <el-tab-pane label="调度算法群智寻优对比" name="algorithm">
        <div class="control-panel">
          <div class="panel-header">
            <h3>算法池配置</h3>
            <el-button type="success" @click="runAlgorithmComparison" :loading="algoLoading">
              开启群智解算 (并行)
              <el-icon class="el-icon--right"><Cpu /></el-icon>
            </el-button>
          </div>
          <div class="panel-body">
            <el-checkbox-group v-model="selectedAlgos" class="glass-checkbox-group">
              <el-checkbox label="awpso" border>自适应权重粒子群 (AWPSO)</el-checkbox>
              <el-checkbox label="pso" border>经典粒子群 (PSO)</el-checkbox>
              <el-checkbox label="ga" border>遗传算法 (GA)</el-checkbox>
            </el-checkbox-group>
          </div>
        </div>

        <div class="charts-grid" v-loading="algoLoading" element-loading-text="正构建多维度帕累托寻优空间，求解中..." element-loading-background="rgba(11, 15, 25, 0.7)">
          
          <!-- 收敛曲线图 -->
          <div class="chart-card full-width">
            <div class="card-header">
              <h4>
                <el-icon><Share /></el-icon>
                寻优代数 - 适应度轨迹 (Convergence Map)
              </h4>
            </div>
            <div class="card-body">
              <div ref="convergenceChartRef" class="chart-container extended-height"></div>
            </div>
          </div>

          <!-- 调度收益对比 -->
          <div class="chart-card half-width">
            <div class="card-header">
              <h4>
                <el-icon><Money /></el-icon>
                日运行综合成本比较
              </h4>
            </div>
            <div class="card-body">
              <div ref="costBarChartRef" class="chart-container"></div>
            </div>
          </div>
          
          <!-- 耗时与弃电率对比 -->
          <div class="chart-card half-width">
            <div class="card-header">
              <h4>
                <el-icon><Timer /></el-icon>
                开销与弃风光率测算
              </h4>
            </div>
            <div class="card-body custom-table-wrapper">
              <el-table :data="algoMetricsList" style="width: 100%">
                <el-table-column prop="algoName" label="启发式算法" width="160"></el-table-column>
                <el-table-column prop="time_cost" label="计算耗时 (s)" align="center">
                  <template #default="scope">
                    <el-tag :type="scope.row.time_cost < 1 ? 'success' : 'warning'" effect="dark">
                      {{ scope.row.time_cost }} s
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="abandon_rate" label="光风弃电率" align="center">
                  <template #default="scope">
                    <span class="gradient-text">{{ (scope.row.abandon_rate * 100).toFixed(2) }}%</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
          
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, shallowRef, onBeforeUnmount, getCurrentInstance } from 'vue'
import { DataAnalysis, VideoPlay, Aim, DataLine, TrendCharts, Share, Cpu, Money, Timer, InfoFilled } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const activeTab = ref('model')

// 使用全局 $http（已配置 baseURL=http://localhost:5000 和拦截器）
const { proxy } = getCurrentInstance()
const $http = proxy.$http

// ----------------- Model Comparison -----------------
const selectedModels = ref(['attention_lstm', 'cnn_lstm', 'standard_lstm'])
const availableModels = [
  { label: 'Attention-LSTM (基石基线)', value: 'attention_lstm' },
  { label: 'CNN-LSTM (时空耦合)', value: 'cnn_lstm' },
  { label: '标准 LSTM (单维向)', value: 'standard_lstm' },
  { label: 'GRU (门控循环替代)', value: 'gru' },
  { label: 'Transformer (纯注意力焦点)', value: 'transformer' }
]

// 曲线对比控制
const compareMode   = ref('realtime')   // 'realtime' | 'testset'
const compareTarget = ref('wind_power') // 'wind_power' | 'pv_power' | 'load'
const contextInfo   = ref('')           // 上下文时间段说明
const currentMode   = ref('realtime')  // 后端实际使用的模式（可能因数据不足降级）

const targetLabelMap = {
  wind_power: '风力发电功率',
  pv_power:   '光伏发电功率',
  load:       '系统负荷',
}

const chartTitle = computed(() => {
  const target = targetLabelMap[compareTarget.value] || compareTarget.value
  const modeStr = currentMode.value === 'realtime' ? '最新实时数据' : '历史测试集 2023-11-07'
  return `${target} 预测 vs 真实值对比（${modeStr}，24步）`
})

const modelLoading = ref(false)
const modelData = reactive({ results: {} })
const modelMetricsList = ref([])

// Models UI References
const radarChartRef = ref(null)
const windLineChartRef = ref(null)
let radarChart = null
let windLineChart = null

const groundTruth = ref(null)   // 真实值序列（所有模型共用）

const runModelComparison = async () => {
  if (selectedModels.value.length === 0) return
  modelLoading.value = true
  try {
    const res = await $http.post('/api/analysis/model_compare', {
      models: selectedModels.value,
      mode:   compareMode.value      // 发送当前选择的模式
    })
    if (res.data && res.data.code === 200) {
      const payload = res.data.data
      if (payload && payload.results) {
        modelData.results  = payload.results
        currentMode.value  = payload.mode || compareMode.value
        contextInfo.value  = payload.context_info || ''

        const gt = payload.ground_truth
        if (gt && Array.isArray(gt.wind_power) && gt.wind_power.length > 0) {
          groundTruth.value = gt
        } else {
          groundTruth.value = null
        }
      } else if (payload) {
        modelData.results = payload
        groundTruth.value = null
      }
      processModelMetrics()
      await nextTick()
      renderRadarChart()
      renderWindLineChart()
    } else {
      console.error('[Analysis] API error:', res.data)
    }
  } catch (err) {
    console.error('模型比较提取失败:', err)
  } finally {
    modelLoading.value = false
  }
}

const getModelLabel = (val) => availableModels.find(m => m.value === val)?.label.split(' ')[0] || val

const processModelMetrics = () => {
  modelMetricsList.value = []
  for (const [mName, mData] of Object.entries(modelData.results)) {
    modelMetricsList.value.push({
      modelKey: mName,
      modelName: getModelLabel(mName),
      ...mData.metrics
    })
  }
  // Sort by MAPE
  modelMetricsList.value.sort((a, b) => a.mape - b.mape)
}

const isBestMetric = (key, value) => {
  if (modelMetricsList.value.length === 0) return false
  const minVal = Math.min(...modelMetricsList.value.map(item => item[key]))
  return value === minVal
}

const tableRowClassName = ({ rowIndex }) => {
  if (rowIndex === 0) return 'best-row'
  return ''
}

const renderRadarChart = () => {
  if (!radarChartRef.value) return
  if (!radarChart) radarChart = echarts.init(radarChartRef.value)
  
  const seriesData = []
  const maxMape = Math.max(...modelMetricsList.value.map(i => i.mape)) * 1.2 || 10
  const maxRmse = Math.max(...modelMetricsList.value.map(i => i.rmse)) * 1.2 || 30
  const maxMae = Math.max(...modelMetricsList.value.map(i => i.mae)) * 1.2 || 20
  
  // ECharts default colors mapped to dynamic palette
  const colors = ['#00f2fe', '#fbc2eb', '#f6d365', '#a18cd1', '#ff9a9e']

  modelMetricsList.value.forEach((item, idx) => {
    seriesData.push({
      value: [maxMape - item.mape, maxRmse - item.rmse, maxMae - item.mae],
      name: item.modelName,
      lineStyle: { width: 2, color: colors[idx % colors.length] },
      areaStyle: {
        color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
          { offset: 0, color: colors[idx % colors.length] + '22' },
          { offset: 1, color: colors[idx % colors.length] + '88' }
        ])
      }
    })
  })

  // Normalize mapping for radar (since smaller metric is better, we inverted it above conceptually for radar spread)
  const option = {
    backgroundColor: '#0d1b2a',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(13,27,42,0.95)', borderColor: '#2a4a6b', textStyle: { color: '#e8f4fd' } },
    legend: {
      data: modelMetricsList.value.map(i => i.modelName),
      bottom: 0,
      textStyle: { color: '#c8dff0', fontSize: 12 },
      itemWidth: 18, itemHeight: 4
    },
    radar: {
      shape: 'circle',
      indicator: [
        { name: '100-MAPE', max: maxMape },
        { name: '100-RMSE', max: maxRmse },
        { name: '100-MAE',  max: maxMae  }
      ],
      splitNumber: 4,
      axisName: { color: '#56d4ff', fontSize: 13, fontWeight: 600 },
      splitLine: {
        lineStyle: {
          color: ['#0f2a3e', '#142f45', '#1a374f', '#203f5a']
        }
      },
      splitArea: { areaStyle: { color: ['rgba(13,27,42,0.6)', 'rgba(14,31,51,0.6)', 'rgba(13,27,42,0.6)', 'rgba(14,31,51,0.6)'] } },
      axisLine: { lineStyle: { color: '#1e3a5f' } }
    },
    series: [{
      name: 'Metrics Radar',
      type: 'radar',
      data: seriesData
    }]
  }
  radarChart.setOption(option)
}

const renderWindLineChart = () => {
  if (!windLineChartRef.value) return

  // 每次销毁重建，防止 ECharts merge 模式残留旧 series
  if (windLineChart) { windLineChart.dispose(); windLineChart = null }
  windLineChart = echarts.init(windLineChartRef.value)

  const target = compareTarget.value   // 'wind_power' | 'pv_power' | 'load'
  const targetLabel = targetLabelMap[target] || target
  const unit = target === 'load' ? 'MW（负荷）' : 'MW'

  // X 轴：真实时间戳 or 0:00~23:00
  const xLabels = (groundTruth.value?.timestamps?.length > 0)
    ? groundTruth.value.timestamps
    : Array.from({length: 24}, (_, i) => `${i}:00`)

  const modelColors = ['#00cfff', '#ff6b6b', '#ffd166', '#06d6a0', '#c77dff']
  const seriesData = []

  // ---- 真实值曲线（白色实线 + 圆点）----
  const gt = groundTruth.value
  const gtData = gt?.[target]
  if (Array.isArray(gtData) && gtData.length > 0) {
    seriesData.push({
      name: '■ 真实值',
      type: 'line',
      smooth: false,
      symbol: 'circle',
      symbolSize: 6,
      data: gtData,
      lineStyle: { width: 3.5, color: '#ffffff' },
      itemStyle: { color: '#ffffff' },
      z: 100,
      emphasis: { focus: 'series', lineStyle: { width: 5 } }
    })
  }

  // ---- 各模型预测曲线 ----
  Object.entries(modelData.results).forEach(([mName, mData], idx) => {
    const color   = modelColors[idx % modelColors.length]
    const predArr = mData.predictions?.[target] || []

    // 计算与真实值的配对 MAE（当前 target）
    let stepMae = null
    if (Array.isArray(gtData) && gtData.length > 0 && predArr.length > 0) {
      const n = Math.min(predArr.length, gtData.length)
      stepMae = (predArr.slice(0, n).reduce(
        (sum, p, i) => sum + Math.abs(p - gtData[i]), 0
      ) / n).toFixed(2)
    }

    const label      = getModelLabel(mName)
    const seriesName = stepMae !== null ? `${label}（MAE=${stepMae}）` : label

    seriesData.push({
      name: seriesName,
      type: 'line',
      smooth: true,
      symbol: 'none',
      data: predArr,
      lineStyle: { width: 2.5, color },
      itemStyle: { color },
      z: 10 + idx,
      emphasis: { focus: 'series', lineStyle: { width: 4 } }
    })
  })

  const option = {
    backgroundColor: '#0d1b2a',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(13,27,42,0.95)',
      borderColor: '#2a4a6b',
      borderWidth: 1,
      textStyle: { color: '#e8f4fd', fontSize: 12 },
      formatter: (params) => {
        let html = `<div style="font-size:13px;font-weight:600;margin-bottom:6px;color:#7ecfff">${params[0]?.axisValue}</div>`
        params.forEach(p => {
          const isReal = p.seriesName.includes('真实值')
          const dot = `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};margin-right:6px;${isReal ? 'border:2px solid #fff' : ''}"></span>`
          const valStr = p.value !== undefined ? Number(p.value).toFixed(2) : '--'
          html += `<div style="${isReal ? 'font-weight:700' : ''};line-height:22px">${dot}${p.seriesName}: <b style="color:${p.color}">${valStr} MW</b></div>`
        })
        return html
      }
    },
    legend: {
      textStyle: { color: '#d0e8ff', fontSize: 12, fontWeight: '500' },
      top: 8, icon: 'roundRect', itemWidth: 20, itemHeight: 4, itemGap: 16
    },
    grid: { left: '4%', right: '3%', bottom: '12%', top: '14%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xLabels,
      axisLabel: {
        color: '#8ab4d4', fontSize: 11,
        rotate: xLabels.some(l => l.includes('-')) ? 35 : 0
      },
      axisLine: { lineStyle: { color: '#1e3a5f', width: 1.5 } },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: `${targetLabel} (${unit})`,
      nameTextStyle: { color: '#8ab4d4', fontSize: 12 },
      splitLine: { lineStyle: { color: '#162d45', type: 'dashed' } },
      axisLabel: { color: '#8ab4d4', fontSize: 11 },
      axisLine: { lineStyle: { color: '#1e3a5f' } }
    },
    series: seriesData
  }
  windLineChart.setOption(option, true)
}

// ----------------- Algorithm Comparison -----------------
const selectedAlgos = ref(['awpso', 'pso', 'ga'])
const algoLoading = ref(false)
const algoData = reactive({ results: {} })
const algoMetricsList = ref([])

// Alg UI References
const convergenceChartRef = ref(null)
const costBarChartRef = ref(null)
let convergenceChart = null
let costBarChart = null

const runAlgorithmComparison = async () => {
  if (selectedAlgos.value.length === 0) return
  algoLoading.value = true
  try {
    const res = await $http.post('/api/analysis/algorithm_compare', {
      algorithms: selectedAlgos.value
    })
    if (res.data && res.data.code === 200) {
      algoData.results = res.data.data
      processAlgoMetrics()
      await nextTick()
      renderConvergenceChart()
      renderCostBarChart()
    }
  } catch (err) {
    console.error('算法对比提取失败:', err)
  } finally {
    algoLoading.value = false
  }
}

const getAlgoLabel = (val) => {
  const map = { 'awpso': '自适应权重PSO', 'pso': '经典粒子群', 'ga': '遗传算法' }
  return map[val] || val.toUpperCase()
}

const processAlgoMetrics = () => {
  algoMetricsList.value = []
  for (const [aName, aData] of Object.entries(algoData.results)) {
    algoMetricsList.value.push({
      algoKey: aName,
      algoName: getAlgoLabel(aName),
      time_cost: aData.time_cost,
      abandon_rate: aData.abandon_rate,
      total_cost: aData.total_cost
    })
  }
  algoMetricsList.value.sort((a, b) => a.total_cost - b.total_cost)
}

const renderConvergenceChart = () => {
  if (!convergenceChartRef.value) return
  if (!convergenceChart) convergenceChart = echarts.init(convergenceChartRef.value)
  
  const seriesData = []
  let maxIters = 0
  
  Object.entries(algoData.results).forEach(([aName, aData]) => {
    const hist = aData.fitness_history || []
    if (hist.length > maxIters) maxIters = hist.length
    seriesData.push({
      name: getAlgoLabel(aName),
      type: 'line',
      smooth: false,
      symbol: 'none',
      data: hist,
      lineStyle: { width: 3 },
      emphasis: { focus: 'series' }
    })
  })
  
  const xData = Array.from({length: maxIters}, (_, i) => i * 50)  // Our history saves every 50 iters

  const option = {
    backgroundColor: '#0d1b2a',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(13,27,42,0.95)', borderColor: '#2a4a6b', textStyle: { color: '#e8f4fd' } },
    legend: { textStyle: { color: '#c8dff0', fontSize: 12 }, top: 10, itemWidth: 20, itemHeight: 3 },
    grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      name: '迭代次数',
      nameLocation: 'middle',
      nameGap: 28,
      nameTextStyle: { color: '#7ecfff', fontSize: 12 },
      data: xData,
      axisLabel: { color: '#8ab4d4', fontSize: 11 },
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'log',
      name: '全局最佳适应度(Log)',
      nameTextStyle: { color: '#7ecfff', fontSize: 12 },
      splitLine: { lineStyle: { color: '#162d45', type: 'dashed' } },
      axisLabel: { color: '#8ab4d4', fontSize: 11 },
      axisLine: { lineStyle: { color: '#1e3a5f' } }
    },
    series: seriesData
  }
  convergenceChart.setOption(option)
}

const renderCostBarChart = () => {
  if (!costBarChartRef.value) return
  if (!costBarChart) costBarChart = echarts.init(costBarChartRef.value)
  
  const names = algoMetricsList.value.map(i => i.algoName)
  const costs = algoMetricsList.value.map(i => i.total_cost)
  
  const option = {
    backgroundColor: '#0d1b2a',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: 'rgba(13,27,42,0.95)', borderColor: '#2a4a6b', textStyle: { color: '#e8f4fd' } },
    grid: { left: '3%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: '#8ab4d4', fontSize: 12, interval: 0 },
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '综合调度成本(元)',
      nameTextStyle: { color: '#7ecfff', fontSize: 12 },
      splitLine: { lineStyle: { color: '#162d45', type: 'dashed' } },
      axisLabel: { color: '#8ab4d4', fontSize: 11 },
      axisLine: { lineStyle: { color: '#1e3a5f' } }
    },
    series: [{
      name: '总成本',
      type: 'bar',
      barWidth: '40%',
      data: costs.map((val, idx) => ({
        value: val,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: idx === 0 ? '#00f2fe' : '#a18cd1' },
            { offset: 1, color: idx === 0 ? '#4facfe' : '#fbc2eb' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      }))
    }]
  }
  costBarChart.setOption(option)
}

// ----------------- Resize Handler -----------------
const handleResize = () => {
  radarChart?.resize()
  windLineChart?.resize()
  convergenceChart?.resize()
  costBarChart?.resize()
}

const handleTabClick = () => {
  setTimeout(() => {
    handleResize()
  }, 100)
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  // Initially run model comparison on load to show something immediately
  runModelComparison()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  radarChart?.dispose()
  windLineChart?.dispose()
  convergenceChart?.dispose()
  costBarChart?.dispose()
})
</script>

<style scoped>
/* ============================================================
   全局：深蓝科技主题，高对比度，方便阅读
   ============================================================ */
.analysis-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(160deg, #06111f 0%, #0a1a2e 50%, #0c1f38 100%);
  color: #e8f4fd;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.header-section {
  margin-bottom: 28px;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 26px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(90deg, #56d4ff 0%, #38b6ff 50%, #6ec6ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 1px;
}

.subtitle {
  margin: 0;
  color: #7ecfff;
  font-size: 14px;
  letter-spacing: 0.5px;
}

/* ============================================================
   Tabs
   ============================================================ */
.analysis-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  height: 46px;
  line-height: 46px;
  color: #7ecfff;
  font-weight: 500;
}
.analysis-tabs :deep(.el-tabs__item.is-active) {
  color: #38d9ff;
  font-weight: 700;
}
.analysis-tabs :deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, #38d9ff, #56d4ff);
  height: 3px;
  border-radius: 2px;
}
.analysis-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: #1a3550;
}

/* ============================================================
   控制面板
   ============================================================ */
.control-panel {
  background: linear-gradient(135deg, #0e1f33 0%, #112840 100%);
  border: 1px solid #1e3a5f;
  border-radius: 12px;
  margin-bottom: 24px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 100, 180, 0.15);
}

.panel-header {
  padding: 16px 24px;
  border-bottom: 1px solid #1e3a5f;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0, 100, 180, 0.08);
}

.panel-header h3 {
  margin: 0;
  font-weight: 600;
  font-size: 15px;
  color: #d0e8ff;
}

.panel-body {
  padding: 20px 24px;
}

.glass-checkbox-group :deep(.el-checkbox) {
  margin-right: 16px;
  margin-bottom: 10px;
  background: rgba(30, 58, 95, 0.4);
  border-color: #2a5080;
  color: #9ecff0;
  font-size: 13px;
}
.glass-checkbox-group :deep(.el-checkbox.is-checked) {
  background: rgba(56, 217, 255, 0.12);
  border-color: #38d9ff;
}
.glass-checkbox-group :deep(.el-checkbox.is-checked .el-checkbox__label) {
  color: #38d9ff;
}

/* ============================================================
   图表网格和卡片
   ============================================================ */
.charts-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.chart-card {
  background: linear-gradient(135deg, #0e1f33 0%, #112840 100%);
  border: 1px solid #1e3a5f;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 24px rgba(0, 80, 160, 0.2);
  transition: box-shadow 0.2s;
}
.chart-card:hover {
  box-shadow: 0 6px 32px rgba(56, 217, 255, 0.15);
}

.radar-card { flex: 1; min-width: 350px; }
.table-card { flex: 2; min-width: 500px; }
.full-width { width: 100%; flex: 0 0 100%; }
.half-width { flex: 1; min-width: 450px; }

/* ============================================================
   卡片头部
   ============================================================ */
.card-header {
  padding: 14px 20px;
  border-bottom: 1px solid #1e3a5f;
  background: linear-gradient(90deg, rgba(56,217,255,0.06) 0%, transparent 100%);
}

.card-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #d0e8ff;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: 0.5px;
}
.card-header h4 .el-icon {
  color: #38d9ff;
}

.card-body {
  padding: 20px;
  flex: 1;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.extended-height {
  height: 440px;
}

/* ============================================================
   表格 — 高对比深蓝主题
   ============================================================ */
.custom-table-wrapper :deep(.el-table) {
  background-color: transparent !important;
  --el-table-border-color: #1e3a5f;
  --el-table-header-bg-color: rgba(14, 31, 51, 0.9);
  --el-table-row-hover-bg-color: rgba(56, 217, 255, 0.06);
  font-size: 13px;
}
.custom-table-wrapper :deep(.el-table tr),
.custom-table-wrapper :deep(.el-table td.el-table__cell) {
  background-color: transparent !important;
  color: #c8dff0;
  border-bottom-color: #162d45;
}
.custom-table-wrapper :deep(.el-table th.el-table__cell) {
  background-color: rgba(14, 31, 51, 0.95) !important;
  color: #7ecfff;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 2px solid #1e3a5f;
}
.custom-table-wrapper :deep(.best-row td) {
  background-color: rgba(56, 217, 255, 0.05) !important;
}

/* ============================================================
   最优指标高亮
   ============================================================ */
.best-value {
  color: #38d9ff;
  font-weight: 700;
  font-size: 14px;
  text-shadow: 0 0 10px rgba(56, 217, 255, 0.6);
}

.gradient-text {
  background: linear-gradient(90deg, #56d4ff 0%, #38b6ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 700;
  font-size: 14px;
}

/* ============================================================
   雷达图和收敛图也同步改为深色背景
   ============================================================ */
.chart-container, .extended-height {
  background: #0d1b2a;
  border-radius: 8px;
}

/* ============================================================
   曲线对比控制栏
   ============================================================ */
.chart-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #1e3a5f;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-label {
  font-size: 13px;
  color: #7ecfff;
  font-weight: 500;
  white-space: nowrap;
}

.context-info {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #8ab4d4;
  background: rgba(56, 217, 255, 0.06);
  border: 1px solid rgba(56, 217, 255, 0.2);
  border-radius: 6px;
  padding: 5px 10px;
  flex: 1;
  min-width: 0;
}

/* Element Plus 单选按钮深色适配 */
.analysis-container :deep(.el-radio-button__inner) {
  background: rgba(14, 31, 51, 0.8);
  border-color: #2a4a6b;
  color: #8ab4d4;
  font-size: 12px;
}
.analysis-container :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #1e3a5f, #0e2a45);
  border-color: #38d9ff;
  color: #38d9ff;
  box-shadow: 0 0 8px rgba(56, 217, 255, 0.3);
}

/* 卡片标题的 tag 对齐 */
.card-header h4 {
  display: flex;
  align-items: center;
}
</style>
