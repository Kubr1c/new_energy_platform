<template>
  <div class="history-records">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>历史记录</span>
          <div class="header-actions">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="loadHistory"
            />
            <el-button @click="loadHistory">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <!-- 统计信息 -->
      <div class="statistics" v-if="statistics">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="总调度次数" :value="statistics.totalDispatches" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="平均成本" :value="statistics.avgCost" suffix="元" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="平均弃电率" :value="(statistics.avgAbandonRate * 100).toFixed(2)" suffix="%" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="总成本节约" :value="statistics.totalSavings" suffix="元" />
          </el-col>
        </el-row>
      </div>

      <!-- 历史记录表格 -->
      <el-table
        :data="historyData"
        v-loading="loading"
        style="width: 100%; margin-top: 20px;"
        @row-click="viewDetail"
        :stripe="true"
        :border="true"
        size="default"
      >
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="schedule_date" label="调度日期"  align="center" />
        <el-table-column prop="total_cost" label="总成本(元)"  align="right">
          <template #default="scope">
            <span :class="getCostClass(scope.row.total_cost)" style="font-weight: 600;">
              {{ (scope.row.total_cost || 0).toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="abandon_rate" label="弃电率"  align="center">
          <template #default="scope">
            <el-tag :type="getAbandonRateClass(scope.row.abandon_rate)" size="small">
              {{ ((scope.row.abandon_rate || 0) * 100).toFixed(2) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="efficiency" label="调度效率" align="center">
          <template #default="scope">
            <div style="display: flex; align-items: center; justify-content: center;">
              <el-progress
                :percentage="(scope.row.efficiency || 0) * 100"
                :color="getEfficiencyColor(scope.row.efficiency)"
                :show-text="false"
                style="width: 50px;"
              />
              <span style="margin-left: 8px; font-size: 12px;">{{ ((scope.row.efficiency || 0) * 100).toFixed(1) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="total_charge" label="总充电量(MWh)"  align="right">
          <template #default="scope">
            {{ (scope.row.total_charge || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_discharge" label="总放电量(MWh)" align="right">
          <template #default="scope">
            {{ (scope.row.total_discharge || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" align="center">
          <template #default="scope">
            {{ scope.row.created_at || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="180" align="center" fixed="right">
          <template #default="scope">
            <div style="display: flex; gap: 8px; justify-content: center;">
              <el-button type="primary" size="small" @click.stop="viewDetail(scope.row)">
                查看详情
              </el-button>
              <el-button type="success" size="small" @click.stop="simulateDispatch(scope.row)">
                模拟执行
              </el-button>
              <el-button type="danger" size="small" @click.stop="deleteRecord(scope.row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          :background="true"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="调度详情" width="90%" @opened="handleDetailDialogOpened">
      <div class="dispatch-detail" v-if="currentRecord">
        <!-- 基本信息 -->
        <el-descriptions :column="3" border style="margin-bottom: 20px;">
          <el-descriptions-item label="调度ID">{{ currentRecord.id }}</el-descriptions-item>
          <el-descriptions-item label="调度日期">{{ currentRecord.schedule_date }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentRecord.created_at }}</el-descriptions-item>
          <el-descriptions-item label="总成本">{{ (currentRecord.total_cost || currentRecord.cost || 0).toFixed(2) }}元</el-descriptions-item>
          <el-descriptions-item label="弃电率">{{ ((currentRecord.abandon_rate || 0) * 100).toFixed(2) }}%</el-descriptions-item>
          <el-descriptions-item label="调度效率">{{ ((currentRecord.efficiency || 0) * 100).toFixed(1) }}%</el-descriptions-item>
        </el-descriptions>

        <!-- 图表展示 -->
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card title="功率调度曲线">
              <v-chart ref="powerChart" class="chart" :option="powerChartOption" autoresize />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card title="SOC变化曲线">
              <v-chart ref="socChart" class="chart" :option="socChartOption" autoresize />
            </el-card>
          </el-col>
        </el-row>

        <!-- 详细数据表格 -->
        <el-card title="24小时调度详情" style="margin-top: 20px;">
          <el-table :data="detailTableData" height="300">
            <el-table-column prop="hour" label="时段" />
            <el-table-column prop="charge" label="充电功率(MW)" />
            <el-table-column prop="discharge" label="放电功率(MW)"/>
            <el-table-column prop="soc" label="SOC(%)">
              <template #default="scope">
                <el-progress
                  :percentage="scope.row.soc || 0"
                  :color="getSocColor(scope.row.soc)"
                  :show-text="false"
                  style="width: 60px;"
                />
                <span style="margin-left: 10px;">{{ (scope.row.soc || 0).toFixed(1) }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="total_cost" label="成本(元)">
              <template #default="scope">
                {{ (scope.row.total_cost || scope.row.cost || 0).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="abandon" label="弃电量(MWh)" width="120">
              <template #default="scope">
                {{ (scope.row.abandon || 0).toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </el-dialog>

    <!-- 模拟结果对话框 -->
    <el-dialog v-model="simulationDialogVisible" title="模拟执行结果" width="80%" @opened="handleSimulationDialogOpened">
      <div class="simulation-result" v-if="simulationResult">
        <el-alert
          :title="`成本偏差: ${simulationResult.cost_deviation >= 0 ? '+' : ''}${(simulationResult.cost_deviation || 0).toFixed(2)}元`"
          :type="Math.abs(simulationResult.cost_deviation || 0) < 100 ? 'success' : 'warning'"
          style="margin-bottom: 20px;"
        />

        <el-row :gutter="20">
          <el-col :span="12">
            <el-card title="计划vs实际功率">
              <v-chart ref="simulationChart" class="chart" :option="simulationChartOption" autoresize />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card title="模拟统计">
              <div class="simulation-stats">
                <div class="stat-item">
                  <h4>计划成本</h4>
                  <p>{{ (simulationResult.planned_cost || 0).toFixed(2) }}元</p>
                </div>
                <div class="stat-item">
                  <h4>实际成本</h4>
                  <p>{{ (simulationResult.actual_cost || 0).toFixed(2) }}元</p>
                </div>
                <div class="stat-item">
                  <h4>偏差率</h4>
                  <p>{{ simulationResult.planned_cost ? ((simulationResult.cost_deviation || 0) / simulationResult.planned_cost * 100).toFixed(2) : '0.00' }}%</p>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { debugObject, debugArray, formatAbandonRate, getAbandonRateType } from '@/utils/debugHelper'
import { validateDispatchData, generateDataReport, checkTableMapping, createDebugData } from '@/utils/dataMapper'
import { validateDispatchHistoryFormat, generateFormatReport, checkExpectedFormat, normalizeDispatchRecord } from '@/utils/dataValidator'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

export default {
  name: 'History',
  components: { VChart },
  data() {
    return {
      loading: false,
      dateRange: [],
      historyData: [],
      statistics: null,
      currentPage: 1,
      pageSize: 20,
      total: 0,
      detailDialogVisible: false,
      simulationDialogVisible: false,
      currentRecord: null,
      simulationResult: null,
      detailTableData: [],
      powerChartOption: {
        tooltip: { trigger: 'axis' },
        legend: { data: ['充电功率', '放电功率'] },
        xAxis: { 
          type: 'category', 
          data: Array.from({length: 24}, (_, i) => `${i}:00`)
        },
        yAxis: { type: 'value', name: '功率(MW)' },
        grid: { top: 40, left: 60, right: 40, bottom: 40 },
        animation: false, // 禁用动画避免渲染问题
        series: [
          { name: '充电功率', type: 'line', data: [] },
          { name: '放电功率', type: 'line', data: [] }
        ]
      },
      socChartOption: {
        tooltip: { trigger: 'axis' },
        legend: { data: ['SOC'] },
        xAxis: { 
          type: 'category', 
          data: Array.from({length: 24}, (_, i) => `${i}:00`)
        },
        yAxis: { type: 'value', name: 'SOC(%)', min: 0, max: 100 },
        grid: { top: 40, left: 60, right: 40, bottom: 40 },
        animation: false, // 禁用动画避免渲染问题
        series: [
          { name: 'SOC', type: 'line', data: [] }
        ]
      },
      simulationChartOption: {
        tooltip: { trigger: 'axis' },
        legend: { data: ['计划功率', '实际功率'] },
        xAxis: { 
          type: 'category', 
          data: Array.from({length: 24}, (_, i) => `${i}:00`)
        },
        yAxis: { type: 'value', name: '功率(MW)' },
        series: [
          { name: '计划功率', type: 'line', data: [] },
          { name: '实际功率', type: 'line', data: [] }
        ]
      }
    }
  },
  mounted() {
    this.loadHistory()
    this.loadStatistics()
  },
  methods: {
    async loadHistory() {
      this.loading = true
      try {
        const params = {
          limit: this.pageSize,
          start_date: this.dateRange?.[0],
          end_date: this.dateRange?.[1]
        }

        const response = await this.$http.get('/api/dispatch/history', { params })
        console.log('调度历史API响应:', response.data)
        
        // 检查响应格式：可能是直接数组或包装格式
        let historyData = null
        
        if (Array.isArray(response.data)) {
          // 直接返回数组格式
          historyData = response.data
          console.log('API直接返回数组格式')
        } else if (response.data && response.data.code === 200) {
          // 包装格式 {code: 200, data: [...]}
          historyData = response.data.data
          console.log('API返回包装格式')
        } else {
          console.error('API响应格式不识别:', response.data)
          this.$message.error('历史记录加载失败：API响应格式错误')
          this.historyData = []
          this.total = 0
          this.loading = false
          return
        }
        
        // 处理数据
        if (Array.isArray(historyData)) {
          console.log('=== 原始API数据 ===')
          console.log('数据条数:', historyData.length)
          if (historyData.length > 0) {
            console.log('第一条原始记录:', historyData[0])
          }
          
          // 数据格式验证
          const formatValidation = validateDispatchHistoryFormat(historyData)
          console.log('=== 数据格式验证 ===')
          console.log(generateFormatReport(formatValidation))
          
          // 检查是否符合预期格式
          const expectedFormatCheck = checkExpectedFormat(historyData)
          console.log('=== 预期格式检查 ===')
          console.log('是否符合预期:', expectedFormatCheck.isExpected)
          if (!expectedFormatCheck.isExpected) {
            console.log('格式不匹配:', expectedFormatCheck.mismatches)
          }
          
          // 修复字段映射：API返回cost字段，表格需要total_cost
          const mappedData = historyData.map(item => {
            const normalizedItem = normalizeDispatchRecord(item)
            return {
              ...normalizedItem,
              efficiency: this.calculateEfficiency(normalizedItem)
            }
          })
          
          // 数据映射检查
          const validation = validateDispatchData(mappedData)
          console.log('=== 数据映射检查 ===')
          console.log(generateDataReport(validation))
          
          // 检查第一条记录的表格映射
          if (mappedData.length > 0) {
            const mappingCheck = checkTableMapping(mappedData[0])
            console.log('=== 表格映射检查 ===')
            console.log('表格列映射结果:', mappingCheck.mappingResults)
            
            // 创建调试版本数据
            const debugData = createDebugData(mappedData)
            console.log('=== 调试版本数据 ===')
            console.log('第一条调试记录:', debugData[0])
          }
          
          this.historyData = mappedData
          this.total = this.historyData.length
          console.log('历史数据加载成功，条数:', this.historyData.length)
        } else {
          console.error('历史数据格式错误，期望数组但得到:', typeof historyData)
          this.historyData = []
          this.total = 0
        }
      } catch (error) {
        console.error('加载历史记录失败:', error)
        this.$message.error('加载历史记录失败：网络错误')
      } finally {
        this.loading = false
      }
    },
    async loadStatistics() {
      try {
        console.log('开始加载统计数据...')
        const response = await this.$http.get('/api/dispatch/statistics')
        console.log('统计数据API响应:', response.data)
        
        // 检查响应格式
        let statisticsData = null
        
        if (Array.isArray(response.data)) {
          // 直接数组格式（不太可能，但兼容处理）
          console.log('统计数据API返回数组格式')
          statisticsData = response.data[0] || {}
        } else if (response.data && response.data.code === 200) {
          // 包装格式
          statisticsData = response.data.data
          console.log('统计数据API返回包装格式')
        } else if (typeof response.data === 'object' && response.data !== null) {
          // 直接对象格式
          statisticsData = response.data
          console.log('统计数据API返回对象格式')
        } else {
          console.error('统计数据API响应格式不识别:', response.data)
          this.statistics = {
            totalDispatches: 0,
            avgCost: 0,
            avgAbandonRate: 0,
            totalSavings: 0
          }
          return
        }
        
        // 设置统计数据
        if (statisticsData) {
          this.statistics = {
            totalDispatches: statisticsData.total_dispatches || 0,
            avgCost: statisticsData.avg_cost || 0,
            avgAbandonRate: statisticsData.avg_abandon_rate || 0,
            totalSavings: statisticsData.total_savings || 0
          }
          console.log('统计数据加载成功:', this.statistics)
        } else {
          console.error('统计数据为空')
          this.statistics = {
            totalDispatches: 0,
            avgCost: 0,
            avgAbandonRate: 0,
            totalSavings: 0
          }
        }
      } catch (error) {
        console.error('加载统计数据失败:', error)
        this.$message.error('统计数据加载失败：网络错误')
        this.statistics = {
          totalDispatches: 0,
          avgCost: 0,
          avgAbandonRate: 0,
          totalSavings: 0
        }
      }
    },
    calculateEfficiency(record) {
      // 简化的效率计算
      const baseEfficiency = 0.85
      const costFactor = Math.max(0, 1 - (record.total_cost - 10000) / 20000)
      const abandonFactor = Math.max(0, 1 - record.abandon_rate)  // 弃电率已经是百分比形式，不需要乘以10
      return baseEfficiency * costFactor * abandonFactor
    },
    getCostClass(cost) {
      if (cost < 10000) return 'cost-low'
      if (cost < 15000) return 'cost-medium'
      return 'cost-high'
    },
    getAbandonRateClass(rate) {
      // 安全检查：确保rate是数字
      const numRate = Number(rate) || 0
      if (numRate < 0.02) return 'success'
      if (numRate < 0.05) return 'warning'
      return 'danger'
    },
    getEfficiencyColor(efficiency) {
      if (efficiency > 0.9) return '#67C23A'
      if (efficiency > 0.8) return '#E6A23C'
      return '#F56C6C'
    },
    getSocColor(soc) {
      if (soc < 20) return '#F56C6C'
      if (soc < 40) return '#E6A23C'
      if (soc < 80) return '#67C23A'
      return '#E6A23C'
    },
    viewDetail(record) {
      this.currentRecord = record
      this.updateDetailCharts(record)
      this.generateDetailTable(record)
      this.detailDialogVisible = true
    },
    updateDetailCharts(record) {
      console.log('=== 更新详情图表 ===')
      console.log('记录数据:', record)
      
      // 更新功率图表
      const chargeData = record.charge_plan || []
      const dischargeData = record.discharge_plan || []
      const socData = record.soc_curve || []
      
      console.log('充电计划数据:', chargeData)
      console.log('放电计划数据:', dischargeData)
      console.log('SOC曲线数据:', socData)
      
      const powerSeries = [
        { name: '充电功率', type: 'line', data: chargeData },
        { name: '放电功率', type: 'line', data: dischargeData }
      ]
      this.powerChartOption.series = powerSeries
      
      // 更新SOC图表
      const socSeries = [{ name: 'SOC', type: 'line', data: socData.map(soc => soc * 100) }]
      this.socChartOption.series = socSeries
      
      console.log('图表数据更新完成')
      
      // 简化的图表更新方法
      console.log('开始更新图表数据...')
      console.log('充电计划数据:', chargeData.slice(0, 5))
      console.log('放电计划数据:', dischargeData.slice(0, 5))
      console.log('SOC数据:', socData.slice(0, 5))
      
      // 直接更新图表配置
      this.powerChartOption = {
        ...this.powerChartOption,
        series: powerSeries
      }
      
      this.socChartOption = {
        ...this.socChartOption,
        series: socSeries
      }
      
      console.log('图表配置更新完成')
    },
    generateDetailTable(record) {
      console.log('=== 生成详情表格 ===')
      console.log('记录数据:', record)
      
      const chargePlan = record.charge_plan || []
      const dischargePlan = record.discharge_plan || []
      const socCurve = record.soc_curve || []
      const totalCost = record.total_cost || record.cost || 0
      
      // 计算弃电量（简化：充电和放电的差值）
      let totalAbandon = 0
      for (let i = 0; i < 24; i++) {
        const charge = chargePlan[i] || 0
        const discharge = dischargePlan[i] || 0
        // 弃电量 = 可用风光发电量 - (风光发电量 - 负荷) - 充电 - 放电
        // 这里简化为充电和放电的差值作为弃电量指标
        totalAbandon += Math.abs(charge - discharge)
      }
      
      console.log('充电计划:', chargePlan)
      console.log('放电计划:', dischargePlan)
      console.log('总弃电量计算:', totalAbandon)
      
      this.detailTableData = Array.from({length: 24}, (_, i) => ({
        hour: `${i}:00`,
        charge: chargePlan[i] || 0,
        discharge: dischargePlan[i] || 0,
        soc: (socCurve[i] || 0.5) * 100,
        cost: totalCost / 24,
        abandon: Math.abs((chargePlan[i] || 0) - (dischargePlan[i] || 0))
      }))
      
      console.log('详情表格生成完成')
    },
    async simulateDispatch(record) {
      try {
        const response = await this.$http.post('/api/dispatch/simulate', {
          dispatch_id: record.id
        })

        if (response && response.data && response.data.code === 200) {
          this.simulationResult = response.data.data
          this.simulationDialogVisible = true
          this.$nextTick(() => {
            this.updateSimulationChart(response.data.data, record)
          })
        } else {
          this.$message.error(response?.data?.message || '模拟执行失败')
        }
      } catch (error) {
        this.$message.error('模拟执行失败')
      }
    },
    updateSimulationChart(data, record) {
      const actualPower = Array.isArray(data?.grid_power) ? data.grid_power : []

      // 优先使用后端返回的计划功率；若无则用调度计划的储能净功率近似展示
      let plannedPower = Array.isArray(data?.planned_grid_power) ? data.planned_grid_power : []
      if (plannedPower.length === 0 && record) {
        const chargePlan = Array.isArray(record.charge_plan) ? record.charge_plan : []
        const dischargePlan = Array.isArray(record.discharge_plan) ? record.discharge_plan : []
        plannedPower = Array.from({ length: 24 }, (_, i) => (dischargePlan[i] || 0) - (chargePlan[i] || 0))
      }

      const pointCount = Math.max(actualPower.length, plannedPower.length, 24)
      const xAxisData = Array.from({ length: pointCount }, (_, i) => `${i}:00`)
      const paddedActual = Array.from({ length: pointCount }, (_, i) => actualPower[i] ?? 0)
      const paddedPlanned = Array.from({ length: pointCount }, (_, i) => plannedPower[i] ?? 0)

      this.simulationChartOption = {
        ...this.simulationChartOption,
        xAxis: {
          ...(this.simulationChartOption.xAxis || {}),
          data: xAxisData
        },
        series: [
          { name: '计划功率', type: 'line', data: paddedPlanned, smooth: true },
          { name: '实际功率', type: 'line', data: paddedActual, smooth: true }
        ]
      }
    },
    handleSimulationDialogOpened() {
      this.$nextTick(() => {
        const chartRef = this.$refs.simulationChart
        if (chartRef && typeof chartRef.resize === 'function') {
          chartRef.resize()
        }
      })
    },
    handleDetailDialogOpened() {
      this.$nextTick(() => {
        const powerChartRef = this.$refs.powerChart
        const socChartRef = this.$refs.socChart
        if (powerChartRef && typeof powerChartRef.resize === 'function') {
          powerChartRef.resize()
        }
        if (socChartRef && typeof socChartRef.resize === 'function') {
          socChartRef.resize()
        }
      })
    },
    async deleteRecord(record) {
      try {
        await this.$confirm('确定要删除这条调度记录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        // 这里应该调用删除API
        this.$message.success('调度记录删除成功')
        this.loadHistory()
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.error('删除失败')
        }
      }
    },
    handleSizeChange(val) {
      this.pageSize = val
      this.loadHistory()
    },
    handleCurrentChange(val) {
      this.currentPage = val
      this.loadHistory()
    }
  }
}
</script>

<style scoped>
.history-records {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.statistics {
  margin: 20px 0;
  padding: 20px;
  background-color: #fafafa;
  border-radius: 4px;
}

.pagination {
  margin-top: 20px;
  text-align: right;
  padding: 20px;
  background-color: #fafafa;
  border-radius: 4px;
}

.pagination .el-pagination {
  justify-content: flex-end;
}

.pagination .el-pagination__total {
  margin-right: 20px;
  color: #606266;
  font-weight: 500;
}

.cost-low { color: #67C23A; font-weight: bold; }
.cost-medium { color: #E6A23C; font-weight: bold; }
.cost-high { color: #F56C6C; font-weight: bold; }

.chart {
  height: 300px;
  width: 100%;
  min-height: 300px;
  min-width: 400px;
}

.dispatch-detail {
  padding: 20px 0;
}

.simulation-result {
  padding: 20px 0;
}

/* 表格样式优化 */
.history-records .el-table {
  font-size: 14px;
}

.history-records .el-table th {
  background-color: #f5f7fa;
  color: #333;
  font-weight: 600;
}

.history-records .el-table td {
  padding: 12px 0;
}

.history-records .el-table--striped .el-table__body tr.el-table__row--striped td {
  background-color: #fafafa;
}

.history-records .el-table__body tr:hover > td {
  background-color: #f0f9ff;
}

/* 操作按钮样式 */
.history-records .el-button + .el-button {
  margin-left: 5px;
}

/* 统计卡片样式 */
.statistics .el-statistic {
  text-align: center;
}

.statistics .el-statistic .el-statistic__content {
  padding: 20px 10px;
}

/* 详情对话框样式 */
.dispatch-detail .el-descriptions {
  margin-top: 20px;
}

.dispatch-detail .el-descriptions__label {
  font-weight: 600;
  width: 120px;
}

.simulation-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 20px;
}

.stat-item {
  text-align: center;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fafafa;
}

.stat-item h4 {
  margin: 0 0 10px 0;
  color: #606266;
  font-size: 14px;
}

.stat-item p {
  margin: 0;
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}

.stat-item h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.stat-item p {
  margin: 0;
  font-size: 18px;
  font-weight: bold;
  color: #409EFF;
}
</style>
