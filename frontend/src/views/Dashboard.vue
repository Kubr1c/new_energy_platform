<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 实时数据卡片 -->
      <el-col :span="6" v-for="card in dataCards" :key="card.title">
        <el-card class="data-card" :class="card.type">
          <div class="card-content">
            <div class="card-icon">
              <el-icon :size="32"><component :is="card.icon" /></el-icon>
            </div>
            <div class="card-info">
              <h3>{{ card.value }}</h3>
              <p>{{ card.title }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 实时功率曲线 -->
      <el-col :span="12">
        <el-card title="实时功率曲线">
          <template #header>
            <div class="card-header">
              <span>实时功率曲线</span>
              <el-button type="text" @click="refreshPowerData">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>
          <v-chart class="chart" :option="powerChartOption" />
        </el-card>
      </el-col>

      <!-- SOC状态 -->
      <el-col :span="12">
        <el-card title="储能SOC状态">
          <template #header>
            <div class="card-header">
              <span>储能SOC状态</span>
              <el-tag :type="socStatus.type">{{ socStatus.text }}</el-tag>
            </div>
          </template>
          <div class="soc-display">
            <el-progress
              type="circle"
              :percentage="socValue"
              :color="socColor"
              :width="150"
            />
            <div class="soc-info">
              <p>当前SOC: {{ socValue }}%</p>
              <p>充电功率: {{ chargePower }} MW</p>
              <p>放电功率: {{ dischargePower }} MW</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 今日预测 -->
      <el-col :span="12">
        <el-card title="今日预测">
          <template #header>
            <div class="card-header">
              <span>今日预测</span>
              <el-button type="primary" size="small" @click="runPrediction">
                执行预测
              </el-button>
            </div>
          </template>
          <v-chart class="chart" :option="predictionChartOption" />
        </el-card>
      </el-col>

      <!-- 系统状态 -->
      <el-col :span="12">
        <el-card title="系统状态">
          <div class="system-status">
            <el-row :gutter="10">
              <el-col :span="12" v-for="status in systemStatus" :key="status.name">
                <div class="status-item">
                  <el-icon :color="status.color"><component :is="status.icon" /></el-icon>
                  <span>{{ status.name }}</span>
                  <el-tag :type="status.tagType">{{ status.value }}</el-tag>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最新调度记录 -->
    <el-card title="最新调度记录" style="margin-top: 20px;">
      <el-table :data="recentDispatches" style="width: 100%">
        <el-table-column prop="schedule_date" label="调度日期" width="120" />
        <el-table-column prop="cost" label="总成本(元)" width="120" />
        <el-table-column prop="abandon_rate" label="弃电率" width="100">
          <template #default="scope">
            {{ (scope.row.abandon_rate * 100).toFixed(2) }}%
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button type="text" @click="viewDispatchDetail(scope.row.id)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

export default {
  name: 'Dashboard',
  components: { VChart },
  data() {
    return {
      dataCards: [
        { title: '风电功率', value: '0 MW', icon: 'WindPower', type: 'wind' },
        { title: '光伏功率', value: '0 MW', icon: 'Sunny', type: 'solar' },
        { title: '负荷功率', value: '0 MW', icon: 'Lightning', type: 'load' },
        { title: '净负荷', value: '0 MW', icon: 'TrendCharts', type: 'net' }
      ],
      socValue: 0,
      chargePower: 0,
      dischargePower: 0,
      powerChartOption: {
        tooltip: { trigger: 'axis' },
        legend: { data: ['风电', '光伏', '负荷'] },
        xAxis: { type: 'category', data: Array.from({length: 24}, (_, i) => `${i}:00`) },
        yAxis: { type: 'value', name: '功率(MW)' },
        series: [
          { name: '风电', type: 'line', data: [] },
          { name: '光伏', type: 'line', data: [] },
          { name: '负荷', type: 'line', data: [] }
        ]
      },
      predictionChartOption: {
        tooltip: { trigger: 'axis' },
        legend: { data: ['实际', '预测'] },
        xAxis: { type: 'category', data: Array.from({length: 24}, (_, i) => `${i}:00`) },
        yAxis: { type: 'value', name: '功率(MW)' },
        series: [
          { name: '实际', type: 'line', data: [] },
          { name: '预测', type: 'line', data: [] }
        ]
      },
      systemStatus: [
        { name: '预测模型', value: '正常', icon: 'Check', color: '#67C23A', tagType: 'success' },
        { name: '优化算法', value: '运行中', icon: 'VideoPlay', color: '#409EFF', tagType: 'primary' },
        { name: '数据库', value: '正常', icon: 'Coin', color: '#67C23A', tagType: 'success' },
        { name: 'API服务', value: '正常', icon: 'Connection', color: '#67C23A', tagType: 'success' }
      ],
      recentDispatches: []
    }
  },
  mounted() {
    this.loadLatestData()
    this.loadRecentDispatches()
    this.loadPredictions()
  },
  computed: {
    socStatus() {
      if (this.socValue < 20) return { type: 'danger', text: '低电量' }
      if (this.socValue < 40) return { type: 'warning', text: '正常' }
      if (this.socValue < 80) return { type: 'success', text: '良好' }
      return { type: 'warning', text: '高电量' }
    },
    socColor() {
      if (this.socValue < 20) return '#F56C6C'
      if (this.socValue < 40) return '#E6A23C'
      if (this.socValue < 80) return '#67C23A'
      return '#E6A23C'
    }
  },
  methods: {
    normalizeChartData(values) {
      if (Array.isArray(values)) return values
      if (values === null || values === undefined) return []
      return [values]
    },
    toNumber(value, fallback = 0) {
      const num = Number(value)
      return Number.isFinite(num) ? num : fallback
    },
    normalizeSocPercent(rawSoc) {
      const soc = this.toNumber(rawSoc, 0)
      const percent = soc <= 1 ? soc * 100 : soc
      return Math.max(0, Math.min(100, percent))
    },
    updateSocFromLatestData(latest) {
      if (!latest || typeof latest !== 'object') return

      const socRaw = latest.soc ?? latest.soc_value ?? latest.battery_soc
      const chargeRaw = latest.charge_power ?? latest.storage_charge_power
      const dischargeRaw = latest.discharge_power ?? latest.storage_discharge_power

      if (socRaw !== undefined && socRaw !== null) {
        this.socValue = Number(this.normalizeSocPercent(socRaw).toFixed(1))
      }
      if (chargeRaw !== undefined && chargeRaw !== null) {
        this.chargePower = Number(this.toNumber(chargeRaw, 0).toFixed(2))
      }
      if (dischargeRaw !== undefined && dischargeRaw !== null) {
        this.dischargePower = Number(this.toNumber(dischargeRaw, 0).toFixed(2))
      }
    },
    updateSocFromDispatchRecord(record) {
      if (!record || typeof record !== 'object') return

      const socCurve = Array.isArray(record.soc_curve) ? record.soc_curve : []
      const chargePlan = Array.isArray(record.charge_plan) ? record.charge_plan : []
      const dischargePlan = Array.isArray(record.discharge_plan) ? record.discharge_plan : []
      const currentHour = new Date().getHours()

      if (socCurve.length > 0) {
        const socRaw = socCurve[currentHour] ?? socCurve[socCurve.length - 1]
        this.socValue = Number(this.normalizeSocPercent(socRaw).toFixed(1))
      }
      if (chargePlan.length > 0) {
        const chargeRaw = chargePlan[currentHour] ?? chargePlan[chargePlan.length - 1]
        this.chargePower = Number(this.toNumber(chargeRaw, 0).toFixed(2))
      }
      if (dischargePlan.length > 0) {
        const dischargeRaw = dischargePlan[currentHour] ?? dischargePlan[dischargePlan.length - 1]
        this.dischargePower = Number(this.toNumber(dischargeRaw, 0).toFixed(2))
      }
    },
    async loadLatestData() {
      try {
        console.log('开始加载最新数据...')
        const response = await this.$http.get('/api/data/latest')
        
        console.log('最新数据API响应:', response.data)

        // 兼容两种格式：
        // 1) 直接数组 [...]
        // 2) 包装对象 { code: 200, data: [...] }
        let data = null
        if (Array.isArray(response.data)) {
          data = response.data
          console.log('最新数据API直接返回数组格式')
        } else if (response.data && response.data.code === 200) {
          data = response.data.data
          console.log('最新数据API返回包装格式')
        } else {
          console.error('API响应格式错误:', response.data)
          this.$message.error('数据加载失败：响应格式错误')
          return
        }

        console.log('获取到的数据条数:', data ? data.length : 0)

        if (Array.isArray(data) && data.length > 0) {
          // 更新数据卡片
          const latest = data[data.length - 1]
          console.log('最新数据:', latest)
          
          this.dataCards[0].value = `${(latest.wind_power || 0).toFixed(1)} MW`
          this.dataCards[1].value = `${(latest.pv_power || 0).toFixed(1)} MW`
          this.dataCards[2].value = `${(latest.load || 0).toFixed(1)} MW`
          const netLoad = (latest.load || 0) - (latest.wind_power || 0) - (latest.pv_power || 0)
          this.dataCards[3].value = `${netLoad.toFixed(1)} MW`
          this.updateSocFromLatestData(latest)

          // 更新功率图表
          this.updatePowerChart(data)
          console.log('数据卡片更新完成')
        } else {
          console.warn('没有获取到最新数据')
          // 设置默认值
          this.dataCards.forEach(card => {
            card.value = '0 MW'
          })
          // 使用空数据更新图表
          this.updatePowerChart([])
        }
      } catch (error) {
        console.error('加载最新数据失败:', error)
        this.$message.error('数据加载失败：网络错误')
        // 出错时使用空数据更新图表
        this.updatePowerChart([])
      }
    },
    async loadRecentDispatches() {
      try {
        const response = await this.$http.get('/api/dispatch/history', {
          params: { limit: 5 }
        })
        console.log('调度历史API响应:', response.data)
        
        // 检查响应格式：可能是直接数组或包装格式
        let dispatchData = null
        
        if (Array.isArray(response.data)) {
          // 直接返回数组格式
          dispatchData = response.data
          console.log('API直接返回数组格式')
        } else if (response.data && response.data.code === 200) {
          // 包装格式 {code: 200, data: [...]}
          dispatchData = response.data.data
          console.log('API返回包装格式')
        } else {
          console.error('调度历史API响应格式不识别:', response.data)
          this.recentDispatches = []
          return
        }
        
        // 处理数据
        if (Array.isArray(dispatchData)) {
          this.recentDispatches = dispatchData
          if (this.recentDispatches.length > 0) {
            this.updateSocFromDispatchRecord(this.recentDispatches[0])
          }
          console.log('调度历史加载成功，条数:', this.recentDispatches.length)
        } else {
          console.error('调度历史数据格式错误，期望数组但得到:', typeof dispatchData)
          this.recentDispatches = []
        }
      } catch (error) {
        console.error('加载调度历史失败:', error)
        this.recentDispatches = []
      }
    },
    async loadPredictions() {
      try {
        const response = await this.$http.get('/api/predict/history', {
          params: { limit: 1, horizon: 24 }
        })
        console.log('预测历史API响应:', response.data)
        
        // 检查响应格式：可能是直接数组或包装格式
        let predictData = null
        
        if (Array.isArray(response.data)) {
          // 直接返回数组格式
          predictData = response.data
          console.log('API直接返回数组格式')
        } else if (response.data && response.data.code === 200) {
          // 包装格式 {code: 200, data: [...]}
          predictData = response.data.data
          console.log('API返回包装格式')
        } else {
          console.error('预测历史API响应格式不识别:', response.data)
          return
        }
        
        // 处理数据
        if (Array.isArray(predictData) && predictData.length > 0) {
          const prediction = predictData[0]
          this.updatePredictionChart(prediction.data)
          console.log('预测数据加载成功')
        } else {
          console.error('预测数据格式错误或为空')
          this.updatePredictionChart(null)
        }
      } catch (error) {
        console.error('加载预测数据失败:', error)
        this.updatePredictionChart(null)
      }
    },
    updatePowerChart(data) {
      if (!data || !Array.isArray(data) || data.length === 0) {
        // 设置空图表数据
        this.powerChartOption.series = [
          { name: '风电', type: 'line', data: [] },
          { name: '光伏', type: 'line', data: [] },
          { name: '负荷', type: 'line', data: [] }
        ]
        return
      }
      
      const windData = data.map(item => this.toNumber(item.wind_power, 0))
      const pvData = data.map(item => this.toNumber(item.pv_power, 0))
      const loadData = data.map(item => this.toNumber(item.load, 0))
      
      this.powerChartOption.series = [
        { name: '风电', type: 'line', data: windData },
        { name: '光伏', type: 'line', data: pvData },
        { name: '负荷', type: 'line', data: loadData }
      ]
    },
    updatePredictionChart(predictionData) {
      if (!predictionData || typeof predictionData !== 'object') {
        // 设置空图表数据
        this.predictionChartOption.series = [
          { name: '实际', type: 'line', data: [] },
          { name: '预测', type: 'line', data: [] }
        ]
        return
      }
      
      const sourceData = predictionData.wind_power ?? predictionData.pv_power ?? predictionData.load ?? []
      const normalizedData = this.normalizeChartData(sourceData).map(item => this.toNumber(item, 0))
      
      this.predictionChartOption.series = [
        { name: '实际', type: 'line', data: normalizedData },
        { name: '预测', type: 'line', data: normalizedData }
      ]
    },
    refreshPowerData() {
      this.loadLatestData()
      this.$message.success('功率数据已刷新')
    },
    async runPrediction() {
      try {
        const response = await this.$http.post('/api/predict/batch', {}, {
          headers: {
            'Content-Type': 'application/json'
          }
        })
        if (response && response.code === 200) {
          this.$message.success('预测执行成功')
          this.loadPredictions()
        } else {
          this.$message.error(response?.message || '预测失败')
        }
      } catch (error) {
        console.error('预测执行失败:', error)
        this.$message.error('预测执行失败')
      }
    },
    viewDispatchDetail(id) {
      this.$router.push(`/history?id=${id}`)
    }
  }
}
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.data-card {
  margin-bottom: 20px;
}

.data-card.wind { border-left: 4px solid #409EFF; }
.data-card.solar { border-left: 4px solid #E6A23C; }
.data-card.load { border-left: 4px solid #F56C6C; }
.data-card.net { border-left: 4px solid #67C23A; }

.card-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.card-icon {
  color: #409EFF;
}

.card-info h3 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.card-info p {
  margin: 5px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart {
  height: 300px;
}

.soc-display {
  display: flex;
  align-items: center;
  gap: 30px;
  padding: 20px;
}

.soc-info p {
  margin: 8px 0;
  color: #606266;
}

.system-status {
  padding: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
  margin-bottom: 10px;
}

.status-item span {
  flex: 1;
  color: #606266;
}
</style>
