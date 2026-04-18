<template>
  <div class="dispatch-optimization">
    <el-row :gutter="20">
      <!-- 调度控制面板 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>调度控制</span>
              <div class="header-actions">
                <el-button type="primary" @click="runDispatch" :loading="dispatchLoading">
                  执行优化调度
                </el-button>
                <el-button type="success" @click="runMultiObjective" :loading="multiLoading">
                  多目标优化
                </el-button>
              </div>
            </div>
          </template>

          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="调度日期">
                <el-date-picker
                  v-model="dispatchDate"
                  type="date"
                  placeholder="选择调度日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="优化算法">
                <el-select v-model="algorithm" placeholder="选择优化算法">
                  <el-option label="AWPSO (推荐)" value="awpso" />
                  <el-option label="PSO" value="pso" />
                  <el-option label="GA" value="ga" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="目标权重">
                <el-button @click="showWeightDialog">设置权重</el-button>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 储能参数设置 -->
          <el-divider content-position="left">储能系统参数</el-divider>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-form-item label="容量(MWh)">
                <el-input-number v-model="essParams.capacity" :min="1" :max="100" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="功率(MW)">
                <el-input-number v-model="essParams.power" :min="1" :max="50" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="充电效率">
                <el-input-number v-model="essParams.eta_c" :min="0.8" :max="1" :step="0.01" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="放电效率">
                <el-input-number v-model="essParams.eta_d" :min="0.8" :max="1" :step="0.01" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 调度结果图表 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>调度结果</span>
              <el-button-group>
                <el-button :type="resultChartType === 'power' ? 'primary' : ''" @click="resultChartType = 'power'">
                  功率曲线
                </el-button>
                <el-button :type="resultChartType === 'soc' ? 'primary' : ''" @click="resultChartType = 'soc'">
                  SOC曲线
                </el-button>
              </el-button-group>
            </div>
          </template>
          <v-chart class="chart" :option="dispatchChartOption" />
        </el-card>
      </el-col>

      <!-- 优化指标 -->
      <el-col :span="8">
        <el-card title="优化指标">
          <div class="optimization-metrics">
            <div class="metric-item">
              <h4>总成本</h4>
              <div class="metric-value">
                <span class="value">{{ totalCost }}</span>
                <span class="unit">元</span>
              </div>
              <el-tag :type="costStatus.type">{{ costStatus.text }}</el-tag>
            </div>
            
            <div class="metric-item">
              <h4>弃风弃光率</h4>
              <div class="metric-value">
                <span class="value">{{ (abandonRate * 100).toFixed(2) }}</span>
                <span class="unit">%</span>
              </div>
              <el-progress :percentage="abandonRate * 100" :color="abandonColor" />
            </div>

            <div class="metric-item">
              <h4>寿命损耗</h4>
              <div class="metric-value">
                <span class="value">{{ lifeLoss.toFixed(4) }}</span>
                <span class="unit">次⁻¹</span>
              </div>
              <el-progress :percentage="lifeLoss * 10000" color="#E6A23C" />
            </div>

           
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 调度计划表格 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>24小时调度计划</span>
              <el-button @click="exportDispatchPlan">
                <el-icon><Download /></el-icon>
                导出计划
              </el-button>
            </div>
          </template>

          <el-table :data="dispatchPlan" height="400">
            <el-table-column prop="hour" label="时段" />
            <el-table-column prop="wind_power" label="风电(MW)" />
            <el-table-column prop="pv_power" label="光伏(MW)" />
            <el-table-column prop="load" label="负荷(MW)" />
            <el-table-column prop="charge_power" label="充电(MW)">
              <template #default="scope">
                <span :class="{ 'positive': scope.row.charge_power > 0 }">
                  {{ scope.row.charge_power.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="discharge_power" label="放电(MW)">
              <template #default="scope">
                <span :class="{ 'positive': scope.row.discharge_power > 0 }">
                  {{ scope.row.discharge_power.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="soc" label="SOC(%)">
              <template #default="scope">
                <el-progress
                  :percentage="scope.row.soc"
                  :color="getSocColor(scope.row.soc)"
                  :show-text="false"
                  style="width: 60px;"
                />
                <span style="margin-left: 10px;">{{ scope.row.soc.toFixed(1) }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="grid_power" label="电网(MW)">
              <template #default="scope">
                <span :class="scope.row.grid_power >= 0 ? 'positive' : 'negative'">
                  {{ scope.row.grid_power >= 0 ? '+' : '' }}{{ scope.row.grid_power.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="abandon" label="弃电(MW)">
              <template #default="scope">
                <span class="negative">{{ scope.row.abandon.toFixed(2) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 权重设置对话框 -->
    <el-dialog v-model="weightDialogVisible" title="目标权重设置" width="420px">
      <el-form :model="weights" label-width="120px">
        <el-form-item label="运行成本">
          <el-slider v-model="weights.cost" :min="0" :max="1" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="弃风弃光率">
          <el-slider v-model="weights.abandon" :min="0" :max="1" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="寿命损耗">
          <el-slider v-model="weights.life" :min="0" :max="1" :step="0.1" show-input />
        </el-form-item>
        <el-form-item>
          <el-alert
            title="权重总和应为1.0"
            type="info"
            :closable="false"
            v-if="Math.abs(weights.cost + weights.abandon + weights.life - 1.0) > 0.01"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="weightDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveWeights">保存</el-button>
      </template>
    </el-dialog>

    <!-- 多目标优化结果对话框 -->
    <el-dialog v-model="moDialogVisible" title="多目标优化 — 帕累托前沿" width="860px" top="5vh">
      <div v-if="moResult">
        <!-- 解选择 -->
        <el-row :gutter="16" style="margin-bottom:16px">
          <el-col :span="16">
            <el-select v-model="selectedSolutionIdx" style="width:100%" @change="onSolutionChange">
              <el-option
                v-for="(s, i) in moResult.all_solutions"
                :key="i"
                :value="i"
                :label="`${s.label}：成本 ${Math.round(s.objectives.cost)} 元 | 弃电率 ${(s.objectives.abandon_rate*100).toFixed(2)}% | 寿命损耗 ${s.objectives.life_loss.toFixed(5)}`"
              />
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-button type="primary" @click="applySelectedSolution">应用此方案</el-button>
          </el-col>
        </el-row>

        <!-- 帕累托散点图（成本 vs 弃电率） -->
        <el-row :gutter="16">
          <el-col :span="12">
            <div style="font-weight:600;margin-bottom:8px">成本 vs 弃电率</div>
            <v-chart class="mo-chart" :option="paretoChartCostAbandon" />
          </el-col>
          <el-col :span="12">
            <div style="font-weight:600;margin-bottom:8px">成本 vs 寿命损耗</div>
            <v-chart class="mo-chart" :option="paretoChartCostLife" />
          </el-col>
        </el-row>

        <!-- 各解指标对比表 -->
        <el-table :data="moResult.all_solutions" style="margin-top:16px" size="small">
          <el-table-column label="方案" prop="label" width="100" />
          <el-table-column label="运行成本(元)">
            <template #default="scope">{{ Math.round(scope.row.objectives.cost) }}</template>
          </el-table-column>
          <el-table-column label="弃电率(%)">
            <template #default="scope">{{ (scope.row.objectives.abandon_rate*100).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="寿命损耗(次⁻¹)">
            <template #default="scope">{{ scope.row.objectives.life_loss.toFixed(6) }}</template>
          </el-table-column>
          <el-table-column label="帕累托前沿" width="100">
            <template #default="scope">
              <el-tag :type="isParetoSolution(scope.row) ? 'success' : 'info'" size="small">
                {{ isParetoSolution(scope.row) ? '非支配' : '支配' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else style="text-align:center;padding:40px;color:#909399">暂无多目标优化结果</div>

      <template #footer>
        <el-button @click="moDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, ScatterChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, BarChart, ScatterChart,
     TitleComponent, TooltipComponent, LegendComponent, GridComponent])

export default {
  name: 'Dispatch',
  components: { VChart },
  data() {
    return {
      dispatchDate: new Date().toISOString().split('T')[0],
      algorithm: 'awpso',
      dispatchLoading: false,
      multiLoading: false,
      resultChartType: 'power',
      totalCost: 0,
      abandonRate: 0.025,
      lifeLoss: 0.0002,
      constraintViolation: 0,
      weightDialogVisible: false,
      moDialogVisible: false,
      moResult: null,
      selectedSolutionIdx: 3,   // 默认选均衡方案（索引3）
      weights: {
        cost: 0.4,
        abandon: 0.3,
        life: 0.3
      },
      essParams: {
        capacity: 40,
        power: 20,
        eta_c: 0.95,
        eta_d: 0.95
      },
      latestDispatchResult: null,
      dispatchPlan: [],
      dispatchChartOption: {
        tooltip: { trigger: 'axis' },
        legend: { data: ['风电', '光伏', '负荷', '充电', '放电'] },
        xAxis: { 
          type: 'category', 
          data: Array.from({length: 24}, (_, i) => `${i}:00`)
        },
        yAxis: { type: 'value', name: '功率(MW)' },
        series: []
      }
    }
  },
  computed: {
    costStatus() {
      if (this.totalCost < 10000) return { type: 'success', text: '优秀' }
      if (this.totalCost < 15000) return { type: 'warning', text: '良好' }
      return { type: 'danger', text: '偏高' }
    },
    abandonColor() {
      if (this.abandonRate < 0.02) return '#67C23A'
      if (this.abandonRate < 0.05) return '#E6A23C'
      return '#F56C6C'
    },
    // 帕累托散点图：成本 vs 弃电率
    paretoChartCostAbandon() {
      if (!this.moResult) return {}
      const all = this.moResult.all_solutions || []
      const paretoSet = new Set((this.moResult.solutions || []).map(s => s.label))
      const scatterData = all.map(s => ({
        value: [
          Math.round(s.objectives.cost),
          parseFloat((s.objectives.abandon_rate * 100).toFixed(3))
        ],
        name: s.label,
        itemStyle: { color: paretoSet.has(s.label) ? '#409EFF' : '#C0C4CC' },
        symbolSize: paretoSet.has(s.label) ? 14 : 10
      }))
      return {
        tooltip: {
          formatter: p => `${p.name}<br/>成本: ${p.value[0]} 元<br/>弃电率: ${p.value[1]}%`
        },
        xAxis: { type: 'value', name: '成本(元)', nameLocation: 'end' },
        yAxis: { type: 'value', name: '弃电率(%)', nameLocation: 'end' },
        series: [{
          type: 'scatter',
          data: scatterData,
          label: { show: true, formatter: p => p.name, position: 'top', fontSize: 11 }
        }]
      }
    },
    // 帕累托散点图：成本 vs 寿命损耗
    paretoChartCostLife() {
      if (!this.moResult) return {}
      const all = this.moResult.all_solutions || []
      const paretoSet = new Set((this.moResult.solutions || []).map(s => s.label))
      const scatterData = all.map(s => ({
        value: [
          Math.round(s.objectives.cost),
          parseFloat(s.objectives.life_loss.toFixed(6))
        ],
        name: s.label,
        itemStyle: { color: paretoSet.has(s.label) ? '#67C23A' : '#C0C4CC' },
        symbolSize: paretoSet.has(s.label) ? 14 : 10
      }))
      return {
        tooltip: {
          formatter: p => `${p.name}<br/>成本: ${p.value[0]} 元<br/>寿命损耗: ${p.value[1]}`
        },
        xAxis: { type: 'value', name: '成本(元)', nameLocation: 'end' },
        yAxis: { type: 'value', name: '寿命损耗(次⁻¹)', nameLocation: 'end' },
        series: [{
          type: 'scatter',
          data: scatterData,
          label: { show: true, formatter: p => p.name, position: 'top', fontSize: 11 }
        }]
      }
    }
  },
  watch: {
    resultChartType() {
      this.updateDispatchChart(this.latestDispatchResult || {})
    }
  },
  mounted() {
    // 初始状态为空，等待执行优化调度
  },
  methods: {
    async runDispatch() {
      this.dispatchLoading = true
      try {
        // 获取预测数据
        const forecasts = await this.getForecasts()
        
        const response = await this.$http.post('/api/dispatch/exec', {
          start_date: this.dispatchDate,
          forecasts: forecasts,
          price_buy: Array.from({length: 24}, () => 0.5),
          price_sell: Array.from({length: 24}, () => 0.3),
          ess_params: this.essParams,
          algorithm: this.algorithm,
          weights: [this.weights.cost, this.weights.abandon, this.weights.life]
        })
        
        // 检查响应格式
        let responseData = null
        if (response && response.data && response.data.code === 200) {
          responseData = response.data.data
        } else if (Array.isArray(response.data)) {
          // 直接返回数组格式
          responseData = response.data
        } else {
          console.error('优化调度API响应格式错误:', response)
          this.$message.error('优化调度失败：API响应格式错误')
          return
        }
        
        if (responseData) {
          this.$message.success('优化调度完成')
          this.updateDispatchResults(responseData)
        } else {
          this.$message.error('优化调度失败：无数据返回')
          this.$message.error('请检查数据是否正确')
        }
      } catch (error) {
        this.$message.error('调度执行失败')
      } finally {
        this.dispatchLoading = false
      }
    },
    async runMultiObjective() {
      this.multiLoading = true
      try {
        const forecasts = await this.getForecasts()
        
        const response = await this.$http.post('/api/dispatch/multi_objective', {
          start_date: this.dispatchDate,
          forecasts: forecasts,
          price_buy: Array.from({length: 24}, () => 0.5),
          price_sell: Array.from({length: 24}, () => 0.3),
          ess_params: this.essParams,
          algorithm: this.algorithm
        })

        if (response && response.data && response.data.code === 200) {
          const d = response.data.data
          this.moResult = d
          this.selectedSolutionIdx = 3   // 默认选均衡方案
          this.moDialogVisible = true
          // 将综合最优解更新到主视图
          this.updateDispatchResults(d.best_solution)
          this.$message.success(`多目标优化完成，帕累托前沿共 ${(d.solutions || []).length} 个非支配解`)
        } else {
          this.$message.error(response?.data?.message || '多目标优化失败')
        }
      } catch (error) {
        this.$message.error('多目标优化失败')
      } finally {
        this.multiLoading = false
      }
    },
    async getForecasts() {
      try {
        // 获取最新的24小时预测数据
        const response = await this.$http.get('/api/predict/history', {
          params: { limit: 1, horizon: 24 }
        })
        
        if (response && response.data && response.data.code === 200 && Array.isArray(response.data.data) && response.data.data.length > 0) {
          const prediction = response.data.data[0]
          return {
            wind_power: prediction.data.wind_power || Array.from({length: 24}, () => 0),
            pv_power: prediction.data.pv_power || Array.from({length: 24}, () => 0),
            load: prediction.data.load || Array.from({length: 24}, () => 0)
          }
        } else {
          // 如果没有预测数据，返回零值
          return {
            wind_power: Array.from({length: 24}, () => 0),
            pv_power: Array.from({length: 24}, () => 0),
            load: Array.from({length: 24}, () => 0)
          }
        }
      } catch (error) {
        console.error('获取预测数据失败:', error)
        // 返回零值作为fallback
        return {
          wind_power: Array.from({length: 24}, () => 0),
          pv_power: Array.from({length: 24}, () => 0),
          load: Array.from({length: 24}, () => 0)
        }
      }
    },
    updateDispatchResults(data) {
      this.latestDispatchResult = data
      this.totalCost = data.total_cost
      this.abandonRate = data.abandon_rate
      this.constraintViolation = data.constraint_violation
      
      if (data.objectives) {
        this.lifeLoss = data.objectives.life_loss
      }
      
      this.generateDispatchPlan(data)
      this.updateDispatchChart(data)
    },
    async generateDispatchPlan(data) {
      // 获取实际的历史数据用于显示
      try {
        const response = await this.$http.get('/api/data/latest')
        let latestData = null
        if (response && response.data && response.data.code === 200 && Array.isArray(response.data.data)) {
          latestData = response.data.data
        } else if (Array.isArray(response.data)) {
          latestData = response.data
        }

        if (Array.isArray(latestData) && latestData.length > 0) {
          const recentData = latestData.slice(-24)
          const wind_power = recentData.map(item => item.wind_power || 0)
          const pv_power = recentData.map(item => item.pv_power || 0)
          const load = recentData.map(item => item.load || 0)

          this.dispatchPlan = Array.from({length: 24}, (_, i) => ({
            hour: `${i}:00`,
            wind_power: (wind_power[i] || 0).toFixed(2),
            pv_power: (pv_power[i] || 0).toFixed(2),
            load: (load[i] || 0).toFixed(2),
            charge_power: data.charge_plan ? data.charge_plan[i] : 0,
            discharge_power: data.discharge_plan ? data.discharge_plan[i] : 0,
            soc: data.soc_curve ? data.soc_curve[i] * 100 : 50,
            grid_power: (load[i] || 0) - (wind_power[i] || 0) - (pv_power[i] || 0) + (data.discharge_plan?.[i] || 0) - (data.charge_plan?.[i] || 0),
            abandon: data.abandon_plan ? data.abandon_plan[i] : 0
          }))
        }
      } catch (error) {
        console.error('获取历史数据失败:', error)
      }
    },
    async updateDispatchChart(data) {
      if (this.resultChartType === 'power') {
        // 获取历史数据用于显示风电、光伏、负荷
        try {
          const response = await this.$http.get('/api/data/latest')
          console.log('最新数据API响应:', response)
          
          // 检查响应格式
          let latestData = null
          if (response && response.data && response.data.code === 200 && Array.isArray(response.data.data)) {
            latestData = response.data.data
          } else if (Array.isArray(response.data)) {
            // 直接返回数组格式
            latestData = response.data
          } else {
            console.error('最新数据API响应格式错误:', response)
            return
          }
          
          if (latestData && latestData.length > 0) {
            const recentData = latestData.slice(-24)
            const windData = recentData.map(item => item.wind_power || 0)
            const pvData = recentData.map(item => item.pv_power || 0)
            const loadData = recentData.map(item => item.load || 0)
            
            this.dispatchChartOption.series = [
              { name: '风电', type: 'line', data: windData },
              { name: '光伏', type: 'line', data: pvData },
              { name: '负荷', type: 'line', data: loadData },
              { name: '充电', type: 'line', data: data.charge_plan || [] },
              { name: '放电', type: 'line', data: data.discharge_plan || [] }
            ]
          }
        } catch (error) {
          console.error('获取历史数据失败:', error)
        }
      } else {
        this.dispatchChartOption.series = [
          { name: 'SOC', type: 'line', data: data.soc_curve?.map(soc => soc * 100) || [] }
        ]
      }
    },
    showWeightDialog() {
      this.weightDialogVisible = true
    },
    saveWeights() {
      if (Math.abs(this.weights.cost + this.weights.abandon + this.weights.life - 1.0) > 0.01) {
        this.$message.error('权重总和必须为1.0')
        return
      }
      this.weightDialogVisible = false
      this.$message.success('权重设置成功')
    },
    // 多目标优化对话框：切换方案时更新图表预览
    onSolutionChange(idx) {
      if (!this.moResult || !this.moResult.all_solutions) return
      const sol = this.moResult.all_solutions[idx]
      if (sol) this.updateDispatchChart(sol)
    },
    // 将选中的方案应用到主视图
    applySelectedSolution() {
      if (!this.moResult || !this.moResult.all_solutions) return
      const sol = this.moResult.all_solutions[this.selectedSolutionIdx]
      if (!sol) return
      this.updateDispatchResults(sol)
      this.moDialogVisible = false
      this.$message.success(`已应用方案：${sol.label}`)
    },
    // 判断某个解是否在帕累托前沿
    isParetoSolution(sol) {
      if (!this.moResult || !this.moResult.solutions) return false
      return this.moResult.solutions.some(s => s.label === sol.label)
    },
    exportDispatchPlan() {
      if (!this.dispatchPlan || this.dispatchPlan.length === 0) {
        this.$message.warning('请先执行优化调度生成计划')
        return
      }

      // 生成CSV内容
      const headers = ['时段', '风电(MW)', '光伏(MW)', '负荷(MW)', '充电(MW)', '放电(MW)', 'SOC(%)', '电网(MW)', '弃电(MW)']
      const csvContent = [
        headers.join(','),
        ...this.dispatchPlan.map(row => [
          row.hour,
          row.wind_power,
          row.pv_power,
          row.load,
          row.charge_power.toFixed(2),
          row.discharge_power.toFixed(2),
          row.soc.toFixed(1),
          row.grid_power.toFixed(2),
          row.abandon.toFixed(2)
        ].join(','))
      ].join('\n')

      // 添加BOM以支持中文
      const bom = '\uFEFF'
      const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' })
      
      // 创建下载链接
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `调度计划_${this.dispatchDate}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      this.$message.success('调度计划导出成功')
    },
    getSocColor(soc) {
      if (soc < 20) return '#F56C6C'
      if (soc < 40) return '#E6A23C'
      if (soc < 80) return '#67C23A'
      return '#E6A23C'
    },
    generateMockData() {
      // 生成合理的模拟数据
      const chargePlan = Array.from({length: 24}, (_, i) => {
        if (i >= 0 && i < 6) return Math.random() * 15 + 5
        if (i >= 6 && i < 18) return Math.random() * 5
        return Math.random() * 10 + 5
      })
      
      const dischargePlan = Array.from({length: 24}, (_, i) => {
        if (i >= 7 && i < 10) return Math.random() * 15 + 5
        if (i >= 18 && i < 21) return Math.random() * 20 + 5
        return Math.random() * 3
      })
      
      const socCurve = Array.from({length: 24}, (_, i) => {
        let soc = 0.5
        for (let t = 0; t <= i; t++) {
          if (chargePlan[t] > 0) {
            soc += chargePlan[t] * 0.95 / 40
          } else if (dischargePlan[t] > 0) {
            soc -= dischargePlan[t] / (0.95 * 40)
          }
          soc = Math.max(0.1, Math.min(0.9, soc))
        }
        return soc
      })
      
      const mockData = {
        charge_plan: chargePlan,
        discharge_plan: dischargePlan,
        soc_curve: socCurve,
        abandon_plan: Array.from({length: 24}, () => Math.random() * 2),
        total_cost: 15000 + Math.random() * 5000,
        abandon_rate: 0.02 + Math.random() * 0.03,
        objectives: {
          cost: 15000 + Math.random() * 5000,
          abandon_rate: 0.02 + Math.random() * 0.03,
          life_loss: 0.0002 + Math.random() * 0.0001
        },
        constraint_violation: 0
      }
      
      this.totalCost = mockData.total_cost
      this.abandonRate = mockData.abandon_rate
      this.lifeLoss = mockData.objectives.life_loss
      this.constraintViolation = mockData.constraint_violation
      
      this.generateDispatchPlan(mockData)
      this.updateDispatchChart(mockData)
    }
  }
}
</script>

<style scoped>
.dispatch-optimization {
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
}

.chart {
  height: 400px;
}

.mo-chart {
  height: 280px;
}

.optimization-metrics {
  padding: 20px 0;
}

.metric-item {
  margin-bottom: 25px;
  padding: 15px;
  background-color: #fafafa;
  border-radius: 4px;
}

.metric-item h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.metric-value {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin-bottom: 10px;
}

.metric-value .value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
}

.metric-value .unit {
  font-size: 14px;
  color: #909399;
}

.positive {
  color: #67C23A;
  font-weight: bold;
}

.negative {
  color: #F56C6C;
  font-weight: bold;
}
</style>
