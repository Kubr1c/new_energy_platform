<template>
  <div class="integrated-dashboard">
    <!-- 头部导航区域 -->
    <div class="dashboard-header">
      <div class="header-left">
        <h1 class="dashboard-title">
          <el-icon><DataAnalysis /></el-icon>
          新能源系统集成监控大屏
        </h1>
        <p class="dashboard-subtitle">实时数据、预测分析、优化调度一站式总览</p>
      </div>
      <div class="header-right">
        <div class="time-display">{{ currentTime }}</div>
        <div class="header-actions">
          <el-button type="primary" size="small" @click="refreshAllData" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
          <el-button type="success" size="small" @click="runQuickPrediction">
            <el-icon><VideoPlay /></el-icon>
            执行预测
          </el-button>
          <el-button type="warning" size="small" @click="goToDispatch">
            <el-icon><Cpu /></el-icon>
            执行调度
          </el-button>
        </div>
      </div>
    </div>

    <!-- 快速导航卡片 -->
    <div class="quick-nav">
      <el-card class="nav-card" v-for="nav in quickNavItems" :key="nav.name" 
               @click="handleNavClick(nav.route)" shadow="hover">
        <div class="nav-card-content">
          <el-icon :size="24" :color="nav.color"><component :is="nav.icon" /></el-icon>
          <span>{{ nav.name }}</span>
        </div>
      </el-card>
    </div>

    <!-- 主内容区域 - 网格布局 -->
    <div class="dashboard-grid">
      <!-- 实时数据统计卡片 -->
      <el-card class="grid-card stats-card" shadow="always">
        <template #header>
          <div class="card-header">
            <h3><el-icon><TrendCharts /></el-icon> 实时系统状态</h3>
            <el-tag :type="systemStatus.type" size="small">{{ systemStatus.text }}</el-tag>
          </div>
        </template>
        <div class="stats-container">
          <div class="stat-item" v-for="stat in realtimeStats" :key="stat.name">
            <div class="stat-icon" :style="{ backgroundColor: stat.bgColor }">
              <el-icon :color="stat.color"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
            <div class="stat-trend" :class="stat.trend">
              <el-icon v-if="stat.trend === 'up'"><Top /></el-icon>
              <el-icon v-if="stat.trend === 'down'"><Bottom /></el-icon>
              <span v-if="stat.trend !== 'stable'">{{ stat.change }}%</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 实时功率曲线 -->
      <el-card class="grid-card chart-card" shadow="always">
        <template #header>
          <div class="card-header">
            <h3><el-icon><DataLine /></el-icon> 实时功率曲线 (24小时)</h3>
          </div>
        </template>
        <div class="chart-container">
          <v-chart class="chart" :option="powerChartOption" autoresize v-if="!loadingData" />
          <div v-else class="chart-loading">
            <el-icon class="loading-icon"><Loading /></el-icon>
            <span>加载数据中...</span>
          </div>
        </div>
      </el-card>

      <!-- 储能SOC状态 -->
      <el-card class="grid-card soc-card" shadow="always">
        <template #header>
          <div class="card-header">
            <h3><el-icon><Battery /></el-icon> 储能系统状态</h3>
            <el-tag :type="socStatus.type" size="small">{{ socStatus.text }}</el-tag>
          </div>
        </template>
        <div class="soc-container">
          <div class="soc-gauge">
            <el-progress
              type="circle"
              :percentage="socValue"
              :color="socColor"
              :width="120"
              :stroke-width="12"
            />
            <div class="soc-label">当前SOC</div>
          </div>
          <div class="soc-details">
            <div class="soc-detail-item">
              <span class="detail-label">充电功率</span>
              <span class="detail-value">{{ chargePower }} MW</span>
            </div>
            <div class="soc-detail-item">
              <span class="detail-label">放电功率</span>
              <span class="detail-value">{{ dischargePower }} MW</span>
            </div>
            <div class="soc-detail-item">
              <span class="detail-label">健康度 (SOH)</span>
              <span class="detail-value">{{ sohValue }}%</span>
            </div>
            <div class="soc-detail-item">
              <span class="detail-label">循环次数</span>
              <span class="detail-value">{{ cycleCount }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 最新预测结果 -->
      <el-card class="grid-card prediction-card" shadow="always">
        <template #header>
          <div class="card-header">
            <h3><el-icon><Opportunity /></el-icon> 最新预测结果</h3>
            <el-button type="text" size="small" @click="goToPredict">查看详情</el-button>
          </div>
        </template>
        <div class="prediction-container">
          <div v-if="latestPrediction">
            <div class="prediction-metrics">
              <div class="metric-item" v-for="metric in predictionMetrics" :key="metric.name">
                <div class="metric-name">{{ metric.name }}</div>
                <div class="metric-value" :class="metric.status">{{ metric.value }}</div>
                <div class="metric-label">{{ metric.label }}</div>
              </div>
            </div>
            <div class="prediction-chart">
              <v-chart class="chart-small" :option="predictionChartOption" autoresize />
            </div>
          </div>
          <div v-else class="no-prediction">
            <el-icon><DataAnalysis /></el-icon>
            <p>暂无预测数据</p>
            <el-button type="primary" size="small" @click="runQuickPrediction">执行预测</el-button>
          </div>
        </div>
      </el-card>

      <!-- 最新调度计划 -->
      <el-card class="grid-card dispatch-card" shadow="always">
        <template #header>
          <div class="card-header">
            <h3><el-icon><SetUp /></el-icon> 最新调度计划</h3>
            <el-button type="text" size="small" @click="goToDispatch">查看详情</el-button>
          </div>
        </template>
        <div class="dispatch-container">
          <div v-if="latestDispatch">
            <div class="dispatch-summary">
              <div class="summary-item">
                <span class="summary-label">总成本</span>
                <span class="summary-value">{{ formatCurrency(latestDispatch.cost) }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">弃电率</span>
                <span class="summary-value">{{ (latestDispatch.abandon_rate * 100).toFixed(2) }}%</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">充电总量</span>
                <span class="summary-value">{{ totalCharge }} MWh</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">放电总量</span>
                <span class="summary-value">{{ totalDischarge }} MWh</span>
              </div>
            </div>
            <div class="dispatch-chart">
              <v-chart class="chart-small" :option="dispatchChartOption" autoresize />
            </div>
          </div>
          <div v-else class="no-dispatch">
            <el-icon><SetUp /></el-icon>
            <p>暂无调度计划</p>
            <el-button type="success" size="small" @click="goToDispatch">执行调度</el-button>
          </div>
        </div>
      </el-card>

      <!-- 系统告警与通知 -->
      <el-card class="grid-card alerts-card" shadow="always">
        <template #header>
          <div class="card-header">
            <h3><el-icon><Bell /></el-icon> 系统告警</h3>
            <el-badge :value="alerts.length" :max="99" class="badge">
              <el-icon><Bell /></el-icon>
            </el-badge>
          </div>
        </template>
        <div class="alerts-container">
          <div v-if="alerts.length > 0">
            <div class="alert-item" v-for="alert in alerts.slice(0, 5)" :key="alert.id" 
                 :class="`alert-${alert.level}`" @click="handleAlertClick(alert)">
              <el-icon :class="`alert-icon-${alert.level}`">
                <component :is="alert.level === 'critical' ? 'WarningFilled' : 
                  alert.level === 'warning' ? 'Warning' : 'InfoFilled'" />
              </el-icon>
              <div class="alert-content">
                <div class="alert-title">{{ alert.title }}</div>
                <div class="alert-time">{{ formatTime(alert.timestamp) }}</div>
              </div>
              <el-icon class="alert-arrow"><ArrowRight /></el-icon>
            </div>
            <div class="alerts-footer" v-if="alerts.length > 5">
              <el-button type="text" size="small" @click="viewAllAlerts">查看全部 {{ alerts.length }} 条告警</el-button>
            </div>
          </div>
          <div v-else class="no-alerts">
            <el-icon><CircleCheck /></el-icon>
            <p>系统运行正常，暂无告警</p>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 底部状态栏 -->
    <div class="dashboard-footer">
      <div class="footer-left">
        <span>数据更新时间: {{ lastUpdateTime }}</span>
        <span class="footer-separator">|</span>
        <span>自动刷新: 
          <el-select v-model="refreshInterval" size="mini" style="width: 100px; margin-left: 5px;">
            <el-option label="关闭" :value="0"></el-option>
            <el-option label="30秒" :value="30000"></el-option>
            <el-option label="1分钟" :value="60000"></el-option>
            <el-option label="5分钟" :value="300000"></el-option>
          </el-select>
        </span>
      </div>
      <div class="footer-right">
        <span>系统版本: v1.0.0</span>
        <span class="footer-separator">|</span>
        <span>在线用户: {{ onlineUsers }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onUnmounted, getCurrentInstance, watch } from 'vue'
import { useRouter } from 'vue-router'
import { 
  DataAnalysis, Refresh, VideoPlay, Cpu, TrendCharts, DataLine, Battery,
  Top, Bottom, Loading, Opportunity, SetUp, Bell, WarningFilled, Warning,
  InfoFilled, ArrowRight, CircleCheck, WindPower, Sunny, Lightning, 
  Money, Timer, UserFilled, Histogram, MapLocation, Setting
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'

export default {
  name: 'IntegratedDashboard',
  components: { 
    VChart,
    DataAnalysis,
    Refresh,
    VideoPlay,
    Cpu,
    TrendCharts,
    DataLine,
    Battery,
    Top,
    Bottom,
    Loading,
    Opportunity,
    SetUp,
    Bell,
    WarningFilled,
    Warning,
    InfoFilled,
    ArrowRight,
    CircleCheck,
    WindPower,
    Sunny,
    Lightning,
    Money,
    Timer,
    UserFilled,
    Histogram,
    MapLocation,
    Setting
  },
  setup() {
    const router = useRouter()
    const { proxy } = getCurrentInstance()
    const $http = proxy.$http

    // 响应式数据
    const currentTime = ref('')
    const loading = ref(false)
    const loadingData = ref(false)
    const refreshInterval = ref(60000) // 默认1分钟刷新
    const lastUpdateTime = ref('')
    const onlineUsers = ref(3)

    // 实时数据
    const realtimeStats = reactive([
      { name: 'wind', label: '风电功率', value: '0 MW', icon: 'WindPower', color: '#409EFF', bgColor: '#409EFF20', trend: 'up', change: 2.5 },
      { name: 'pv', label: '光伏功率', value: '0 MW', icon: 'Sunny', color: '#E6A23C', bgColor: '#E6A22320', trend: 'up', change: 1.8 },
      { name: 'load', label: '系统负荷', value: '0 MW', icon: 'Lightning', color: '#F56C6C', bgColor: '#F56C6C20', trend: 'down', change: 1.2 },
      { name: 'net', label: '净负荷', value: '0 MW', icon: 'TrendCharts', color: '#67C23A', bgColor: '#67C23A20', trend: 'stable', change: 0 }
    ])

    // 储能状态
    const socValue = ref(65.5)
    const chargePower = ref(8.2)
    const dischargePower = ref(12.5)
    const sohValue = ref(98.5)
    const cycleCount = ref(124)

    // 预测数据
    const latestPrediction = ref(null)
    const predictionMetrics = ref([
      { name: 'MAPE', value: '8.2%', label: '平均绝对百分比误差', status: 'good' },
      { name: 'RMSE', value: '15.3', label: '均方根误差', status: 'medium' },
      { name: 'R²', value: '0.94', label: '决定系数', status: 'good' }
    ])

    // 调度数据
    const latestDispatch = ref(null)
    const totalCharge = ref(0)
    const totalDischarge = ref(0)

    // 告警数据
    const alerts = ref([
      { id: 1, level: 'warning', title: '光伏功率预测偏差超过10%', timestamp: new Date(Date.now() - 300000) },
      { id: 2, level: 'info', title: '储能SOC达到80%，建议调整充放电策略', timestamp: new Date(Date.now() - 600000) },
      { id: 3, level: 'warning', title: '风电功率实际值超出预测范围', timestamp: new Date(Date.now() - 1200000) },
      { id: 4, level: 'warning', title: '负荷预测模型需要重新训练', timestamp: new Date(Date.now() - 1800000) }
    ])

    // 快速导航
    const quickNavItems = ref([
      { name: '数据管理', icon: 'Histogram', route: '/data', color: '#409EFF' },
      { name: '预测分析', icon: 'DataAnalysis', route: '/predict', color: '#E6A23C' },
      { name: '优化调度', icon: 'SetUp', route: '/dispatch', color: '#67C23A' },
      { name: '算法对比', icon: 'Opportunity', route: '/analysis', color: '#F56C6C' },
      { name: '地理态势', icon: 'MapLocation', route: '/map', color: '#9C27B0' },
      { name: '系统设置', icon: 'Setting', route: '/settings', color: '#607D8B' }
    ])

    // 计算属性
    const systemStatus = computed(() => {
      const criticalAlerts = alerts.value.filter(a => a.level === 'critical').length
      if (criticalAlerts > 0) return { type: 'danger', text: '异常' }
      const warningAlerts = alerts.value.filter(a => a.level === 'warning').length
      if (warningAlerts > 0) return { type: 'warning', text: '警告' }
      return { type: 'success', text: '正常' }
    })

    const socStatus = computed(() => {
      if (socValue.value < 20) return { type: 'danger', text: '低电量' }
      if (socValue.value < 40) return { type: 'warning', text: '正常' }
      if (socValue.value < 80) return { type: 'success', text: '良好' }
      return { type: 'warning', text: '高电量' }
    })

    const socColor = computed(() => {
      if (socValue.value < 20) return '#F56C6C'
      if (socValue.value < 40) return '#E6A23C'
      if (socValue.value < 80) return '#67C23A'
      return '#E6A23C'
    })

    // 图表配置
    const powerChartOption = ref({})
    const predictionChartOption = ref({})
    const dispatchChartOption = ref({})

    // 定时器
    let timeTimer = null
    let refreshTimer = null

    // 方法
    const updateCurrentTime = () => {
      const now = new Date()
      currentTime.value = now.toLocaleString('zh-CN', { 
        year: 'numeric', 
        month: '2-digit', 
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false 
      })
    }

    const formatTime = (date) => {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }

    const formatCurrency = (value) => {
      if (!value) return '¥0'
      return `¥${Number(value).toLocaleString('zh-CN')}`
    }

    const loadRealtimeData = async () => {
      try {
        loadingData.value = true
        console.log('开始加载实时数据...')
        
        // 1. 加载实时功率数据
        const response = await $http.get('/api/data/latest', { params: { limit: 24 } })
        console.log('实时数据API响应:', response.data)
        
        let data = null
        if (response.data && response.data.code === 200 && Array.isArray(response.data.data)) {
          data = response.data.data
        } else if (Array.isArray(response.data)) {
          data = response.data
        }
        
        if (data && data.length > 0) {
          // 获取当前小时
          const currentHour = new Date().getHours()
          console.log('当前小时:', currentHour)
          
          // 找到当前小时的数据
          let currentData = data.find(item => {
            const hour = new Date(item.timestamp).getHours()
            return hour === currentHour
          })
          
          // 如果找不到当前小时的数据，使用最新的数据
          if (!currentData) {
            currentData = data[data.length - 1]
            console.log('找不到当前小时的数据，使用最新数据:', currentData)
          } else {
            console.log('当前小时的数据:', currentData)
          }
          
          // 更新实时统计
          realtimeStats[0].value = `${(currentData.wind_power || 0).toFixed(1)} MW`
          realtimeStats[1].value = `${(currentData.pv_power || 0).toFixed(1)} MW`
          realtimeStats[2].value = `${(currentData.load || 0).toFixed(1)} MW`
          const netLoad = (currentData.load || 0) - (currentData.wind_power || 0) - (currentData.pv_power || 0)
          realtimeStats[3].value = `${netLoad.toFixed(1)} MW`
          
          // 更新功率图表
          updatePowerChart(data)
        }
        
        // 2. 加载最新预测
        await loadLatestPrediction()
        
        // 3. 加载最新调度
        await loadLatestDispatch()
        
        // 4. 更新储能状态（可以从调度数据中获取）
        if (latestDispatch.value && latestDispatch.value.soc_curve) {
          const socCurve = latestDispatch.value.soc_curve
          const currentHour = new Date().getHours()
          if (socCurve.length > currentHour) {
            // 确保SOC值在0-100%之间
            let rawSoc = socCurve[currentHour]
            // 如果值小于1，认为是小数形式，需要乘以100
            if (rawSoc < 1) {
              rawSoc = rawSoc * 100
            }
            // 限制在0-100之间
            socValue.value = Math.max(0, Math.min(100, Number(rawSoc.toFixed(1))))
          }
        }
        
        lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        console.log('数据加载完成')
      } catch (error) {
        console.error('加载实时数据失败:', error)
      } finally {
        loadingData.value = false
        loading.value = false
      }
    }

    const updatePowerChart = (data) => {
      if (!data || !Array.isArray(data) || data.length === 0) {
        powerChartOption.value = {
          title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#999' } },
          xAxis: { type: 'category', data: Array.from({length: 24}, (_, i) => `${i}:00`) },
          yAxis: { type: 'value', name: '功率(MW)' },
          series: []
        }
        return
      }

      const labels = data.map(item => {
        const d = new Date(item.timestamp)
        const hh = String(d.getHours()).padStart(2, '0')
        const mi = String(d.getMinutes()).padStart(2, '0')
        return `${hh}:${mi}`
      })

      const windData = data.map(item => item.wind_power || 0)
      const pvData = data.map(item => item.pv_power || 0)
      const loadData = data.map(item => item.load || 0)

      const currentDate = new Date().toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      })

      powerChartOption.value = {
        title: {
          text: '实时功率曲线',
          subtext: currentDate,
          left: 'center',
          top: 10,
          textStyle: { color: '#333', fontSize: 14 },
          subtextStyle: { color: '#666', fontSize: 12 }
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(13,27,42,0.95)',
          borderColor: '#2a4a6b',
          textStyle: { color: '#e8f4fd' }
        },
        legend: {
          data: ['风电', '光伏', '负荷'],
          textStyle: { color: '#666' },
          top: 40
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '10%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: labels,
          axisLine: { lineStyle: { color: '#ddd' } },
          axisLabel: { color: '#666', fontSize: 11 }
        },
        yAxis: {
          type: 'value',
          name: '功率(MW)',
          nameTextStyle: { color: '#666' },
          splitLine: { lineStyle: { color: '#f0f0f0' } },
          axisLine: { lineStyle: { color: '#ddd' } },
          axisLabel: { color: '#666' }
        },
        series: [
          {
            name: '风电',
            type: 'line',
            smooth: true,
            data: windData,
            lineStyle: { width: 2, color: '#409EFF' },
            itemStyle: { color: '#409EFF' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
                { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
              ])
            }
          },
          {
            name: '光伏',
            type: 'line',
            smooth: true,
            data: pvData,
            lineStyle: { width: 2, color: '#E6A23C' },
            itemStyle: { color: '#E6A23C' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(230, 162, 60, 0.3)' },
                { offset: 1, color: 'rgba(230, 162, 60, 0.05)' }
              ])
            }
          },
          {
            name: '负荷',
            type: 'line',
            smooth: true,
            data: loadData,
            lineStyle: { width: 2, color: '#F56C6C' },
            itemStyle: { color: '#F56C6C' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(245, 108, 108, 0.3)' },
                { offset: 1, color: 'rgba(245, 108, 108, 0.05)' }
              ])
            }
          }
        ]
      }
    }

    const loadLatestPrediction = async () => {
      try {
        const response = await $http.get('/api/predict/history', { params: { limit: 1 } })
        console.log('预测历史API响应:', response.data)
        
        let predictData = null
        if (response.data && response.data.code === 200 && Array.isArray(response.data.data)) {
          predictData = response.data.data
        } else if (Array.isArray(response.data)) {
          predictData = response.data
        }
        
        if (predictData && predictData.length > 0) {
          latestPrediction.value = predictData[0]
          updatePredictionChart(predictData[0])
        } else {
          latestPrediction.value = null
          updatePredictionChart(null)
        }
      } catch (error) {
        console.error('加载预测数据失败:', error)
        latestPrediction.value = null
        updatePredictionChart(null)
      }
    }

    const updatePredictionChart = (prediction) => {
      if (!prediction || !prediction.data) {
        predictionChartOption.value = {
          title: { text: '暂无预测数据', left: 'center', top: 'center', textStyle: { color: '#999' } },
          xAxis: { type: 'category', data: Array.from({length: 24}, (_, i) => `${i}:00`) },
          yAxis: { type: 'value', name: '功率(MW)' },
          series: []
        }
        return
      }

      const predData = prediction.data
      const windPred = predData.wind_power || Array.from({length: 24}, () => 0)
      const pvPred = predData.pv_power || Array.from({length: 24}, () => 0)

      predictionChartOption.value = {
        tooltip: { trigger: 'axis', backgroundColor: 'rgba(13,27,42,0.95)', borderColor: '#2a4a6b', textStyle: { color: '#e8f4fd' } },
        legend: { data: ['风电预测', '光伏预测'], textStyle: { color: '#666' }, top: 10 },
        grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
        xAxis: {
          type: 'category',
          data: Array.from({length: 24}, (_, i) => `${i}:00`),
          axisLine: { lineStyle: { color: '#ddd' } },
          axisLabel: { color: '#666', fontSize: 10 }
        },
        yAxis: {
          type: 'value',
          name: '功率(MW)',
          nameTextStyle: { color: '#666' },
          splitLine: { lineStyle: { color: '#f0f0f0' } },
          axisLine: { lineStyle: { color: '#ddd' } },
          axisLabel: { color: '#666' }
        },
        series: [
          {
            name: '风电预测',
            type: 'line',
            smooth: true,
            data: windPred,
            lineStyle: { width: 2, color: '#409EFF' },
            itemStyle: { color: '#409EFF' }
          },
          {
            name: '光伏预测',
            type: 'line',
            smooth: true,
            data: pvPred,
            lineStyle: { width: 2, color: '#E6A23C' },
            itemStyle: { color: '#E6A23C' }
          }
        ]
      }
    }

    const loadLatestDispatch = async () => {
      try {
        const response = await $http.get('/api/dispatch/history', { params: { limit: 1 } })
        console.log('调度历史API响应:', response.data)
        
        let dispatchData = null
        if (response.data && response.data.code === 200 && Array.isArray(response.data.data)) {
          dispatchData = response.data.data
        } else if (Array.isArray(response.data)) {
          dispatchData = response.data
        }
        
        if (dispatchData && dispatchData.length > 0) {
          latestDispatch.value = dispatchData[0]
          totalCharge.value = dispatchData[0].charge_plan 
            ? dispatchData[0].charge_plan.reduce((sum, val) => sum + val, 0).toFixed(1)
            : 0
          totalDischarge.value = dispatchData[0].discharge_plan 
            ? dispatchData[0].discharge_plan.reduce((sum, val) => sum + val, 0).toFixed(1)
            : 0
          updateDispatchChart(dispatchData[0])
        }
      } catch (error) {
        console.error('加载调度数据失败:', error)
      }
    }

    const updateDispatchChart = (dispatch) => {
      if (!dispatch) {
        dispatchChartOption.value = {
          title: { text: '暂无调度数据', left: 'center', top: 'center', textStyle: { color: '#999' } },
          xAxis: { type: 'category', data: Array.from({length: 24}, (_, i) => `${i}:00`) },
          yAxis: { type: 'value', name: '功率(MW)' },
          series: []
        }
        return
      }

      const chargePlan = dispatch.charge_plan || Array.from({length: 24}, () => 0)
      const dischargePlan = dispatch.discharge_plan || Array.from({length: 24}, () => 0)
      const socCurve = dispatch.soc_curve ? dispatch.soc_curve.map(soc => {
        // 确保SOC值在0-100%之间
        let rawSoc = soc
        if (rawSoc < 1) {
          rawSoc = rawSoc * 100
        }
        return Math.max(0, Math.min(100, Number(rawSoc.toFixed(1))))
      }) : Array.from({length: 24}, () => 50)

      dispatchChartOption.value = {
        tooltip: { trigger: 'axis', backgroundColor: 'rgba(13,27,42,0.95)', borderColor: '#2a4a6b', textStyle: { color: '#e8f4fd' } },
        legend: { data: ['充电', '放电', 'SOC'], textStyle: { color: '#666' }, top: 10 },
        grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
        xAxis: {
          type: 'category',
          data: Array.from({length: 24}, (_, i) => `${i}:00`),
          axisLine: { lineStyle: { color: '#ddd' } },
          axisLabel: { color: '#666', fontSize: 10 }
        },
        yAxis: [
          {
            type: 'value',
            name: '功率(MW)',
            nameTextStyle: { color: '#666' },
            splitLine: { lineStyle: { color: '#f0f0f0' } },
            axisLine: { lineStyle: { color: '#ddd' } },
            axisLabel: { color: '#666' }
          },
          {
            type: 'value',
            name: 'SOC(%)',
            nameTextStyle: { color: '#666' },
            splitLine: { show: false },
            axisLine: { lineStyle: { color: '#ddd' } },
            axisLabel: { color: '#666', formatter: '{value}%' }
          }
        ],
        series: [
          {
            name: '充电',
            type: 'bar',
            data: chargePlan,
            itemStyle: { color: '#67C23A' },
            barWidth: '40%'
          },
          {
            name: '放电',
            type: 'bar',
            data: dischargePlan,
            itemStyle: { color: '#F56C6C' },
            barWidth: '40%'
          },
          {
            name: 'SOC',
            type: 'line',
            yAxisIndex: 1,
            smooth: true,
            data: socCurve,
            lineStyle: { width: 2, color: '#409EFF' },
            itemStyle: { color: '#409EFF' }
          }
        ]
      }
    }

    const refreshAllData = async () => {
      loading.value = true
      await loadRealtimeData()
    }

    const runQuickPrediction = async () => {
      try {
        loading.value = true
        const response = await $http.post('/api/predict/batch', {})
        if (response.data && response.data.code === 200) {
          proxy.$message.success('预测执行成功')
          await loadLatestPrediction()
        } else {
          proxy.$message.error(response.data?.message || '预测执行失败')
        }
      } catch (error) {
        console.error('执行预测失败:', error)
        proxy.$message.error('执行预测失败')
      } finally {
        loading.value = false
      }
    }

    const goToPredict = () => {
      router.push('/predict')
    }

    const goToDispatch = () => {
      router.push('/dispatch')
    }

    const handleNavClick = (route) => {
      router.push(route)
    }

    const handleAlertClick = (alert) => {
      console.log('处理告警:', alert)
      // 可以根据告警类型跳转到不同页面
      if (alert.title.includes('预测')) {
        router.push('/predict')
      } else if (alert.title.includes('调度')) {
        router.push('/dispatch')
      } else if (alert.title.includes('风电') || alert.title.includes('光伏')) {
        router.push('/analysis')
      }
    }

    const viewAllAlerts = () => {
      console.log('查看全部告警')
    }

    // 生命周期
    onMounted(() => {
      updateCurrentTime()
      timeTimer = setInterval(updateCurrentTime, 1000)
      
      // 初始加载数据
      loadRealtimeData()
      
      // 设置自动刷新
      setupAutoRefresh()
    })

    onUnmounted(() => {
      if (timeTimer) clearInterval(timeTimer)
      if (refreshTimer) clearInterval(refreshTimer)
    })

    // 自动刷新设置
    const setupAutoRefresh = () => {
      if (refreshTimer) clearInterval(refreshTimer)
      
      if (refreshInterval.value > 0) {
        refreshTimer = setInterval(() => {
          if (!loading.value) {
            loadRealtimeData()
          }
        }, refreshInterval.value)
      }
    }

    // 监听刷新间隔变化
    watch(refreshInterval, () => {
      setupAutoRefresh()
    })

    return {
      currentTime,
      loading,
      loadingData,
      refreshInterval,
      lastUpdateTime,
      onlineUsers,
      realtimeStats,
      socValue,
      chargePower,
      dischargePower,
      sohValue,
      cycleCount,
      latestPrediction,
      predictionMetrics,
      latestDispatch,
      totalCharge,
      totalDischarge,
      alerts,
      quickNavItems,
      systemStatus,
      socStatus,
      socColor,
      powerChartOption,
      predictionChartOption,
      dispatchChartOption,
      formatTime,
      formatCurrency,
      refreshAllData,
      runQuickPrediction,
      goToPredict,
      goToDispatch,
      handleNavClick,
      handleAlertClick,
      viewAllAlerts
    }
  }
}
</script>

<style scoped>
.integrated-dashboard {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  padding: 20px;
  overflow: auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.header-left {
  flex: 1;
}

.dashboard-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 12px;
}

.dashboard-title .el-icon {
  color: #409EFF;
  font-size: 28px;
}

.dashboard-subtitle {
  margin: 8px 0 0 0;
  color: #606266;
  font-size: 14px;
}

.header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.time-display {
  font-family: monospace;
  font-size: 16px;
  color: #409EFF;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.quick-nav {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.nav-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
  border-radius: 8px;
}

.nav-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1) !important;
}

.nav-card-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px 10px;
  gap: 8px;
}

.nav-card-content .el-icon {
  font-size: 28px;
}

.nav-card-content span {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  flex: 1;
  margin-bottom: 20px;
}

.grid-card {
  border: none;
  border-radius: 12px;
  overflow: hidden;
}

.grid-card :deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  background: linear-gradient(90deg, #fafafa 0%, #ffffff 100%);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-header .el-icon {
  color: #409EFF;
}

.stats-card {
  grid-column: span 1;
}

.stats-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.stat-item:hover {
  background: #f0f0f0;
  transform: translateX(4px);
}

.stat-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #606266;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 4px;
}

.stat-trend.up {
  color: #67C23A;
  background-color: rgba(103, 194, 58, 0.1);
}

.stat-trend.down {
  color: #F56C6C;
  background-color: rgba(245, 108, 108, 0.1);
}

.stat-trend.stable {
  color: #909399;
  background-color: rgba(144, 147, 153, 0.1);
}

.chart-card {
  grid-column: span 2;
}

.chart-container {
  height: 280px;
  padding: 10px;
}

.chart {
  width: 100%;
  height: 100%;
}

.chart-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  gap: 10px;
}

.loading-icon {
  font-size: 32px;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.soc-card {
  grid-column: span 1;
}

.soc-container {
  display: flex;
  align-items: center;
  padding: 20px;
  gap: 30px;
}

.soc-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.soc-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.soc-details {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.soc-detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  color: #909399;
}

.detail-value {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.prediction-card, .dispatch-card, .alerts-card {
  grid-column: span 1;
}

.prediction-container, .dispatch-container, .alerts-container {
  padding: 16px;
}

.prediction-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
  gap: 6px;
}

.metric-name {
  font-size: 12px;
  color: #909399;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
}

.metric-value.good {
  color: #67C23A;
}

.metric-value.medium {
  color: #E6A23C;
}

.metric-value.poor {
  color: #F56C6C;
}

.metric-label {
  font-size: 11px;
  color: #909399;
  text-align: center;
}

.prediction-chart, .dispatch-chart {
  height: 120px;
}

.chart-small {
  width: 100%;
  height: 100%;
}

.no-prediction, .no-dispatch, .no-alerts {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 180px;
  color: #909399;
  gap: 12px;
  text-align: center;
}

.no-prediction .el-icon, .no-dispatch .el-icon, .no-alerts .el-icon {
  font-size: 48px;
  color: #c0c4cc;
}

.dispatch-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
  gap: 6px;
}

.summary-label {
  font-size: 12px;
  color: #909399;
}

.summary-value {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.alert-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: #fafafa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  gap: 12px;
}

.alert-item:hover {
  background: #f0f0f0;
  transform: translateX(4px);
}

.alert-item.alert-critical {
  border-left: 4px solid #F56C6C;
}

.alert-item.alert-warning {
  border-left: 4px solid #E6A23C;
}

.alert-item.alert-info {
  border-left: 4px solid #409EFF;
}

.alert-icon-critical {
  color: #F56C6C;
  font-size: 18px;
}

.alert-icon-warning {
  color: #E6A23C;
  font-size: 18px;
}

.alert-icon-info {
  color: #409EFF;
  font-size: 18px;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.alert-time {
  font-size: 11px;
  color: #909399;
}

.alert-arrow {
  color: #c0c4cc;
  font-size: 14px;
}

.alerts-footer {
  text-align: center;
  padding-top: 10px;
  border-top: 1px solid #f0f0f0;
}

.dashboard-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: white;
  border-radius: 8px;
  font-size: 12px;
  color: #606266;
  margin-top: auto;
}

.footer-left, .footer-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.footer-separator {
  color: #c0c4cc;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .chart-card {
    grid-column: span 2;
  }
}

@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  
  .chart-card, .stats-card, .soc-card, 
  .prediction-card, .dispatch-card, .alerts-card {
    grid-column: span 1;
  }
  
  .quick-nav {
    grid-template-columns: repeat(3, 1fr);
  }
  
  .dashboard-header {
    flex-direction: column;
    gap: 15px;
    align-items: flex-start;
  }
  
  .header-right {
    align-items: flex-start;
  }
}
</style>