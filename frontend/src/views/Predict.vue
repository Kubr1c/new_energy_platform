<template>
  <div class="predict-analysis">
    <el-row :gutter="20">
      <!-- 预测控制面板 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>预测控制</span>
              <div class="header-actions">
                <el-button type="primary" @click="runSinglePrediction" :loading="singleLoading">
                  单步预测
                </el-button>
                <el-button type="success" @click="runBatchPrediction" :loading="batchLoading">
                  批量预测(24h)
                </el-button>
              </div>
            </div>
          </template>

          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="预测模型">
                <el-select v-model="modelType" placeholder="选择预测模型" style="width: 100%;">
                  <el-option
                    v-for="m in availableModels"
                    :key="m.model_type"
                    :label="m.name"
                    :value="m.model_type"
                  >
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <span>{{ m.name }}</span>
                      <span style="color: #909399; font-size: 12px; margin-left: 12px;">{{ m.params }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="预测类型">
                <el-select v-model="predictType" placeholder="选择预测类型">
                  <el-option label="风电功率" value="wind" />
                  <el-option label="光伏功率" value="pv" />
                  <el-option label="负荷" value="load" />
                  <el-option label="综合预测" value="multi" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="预测时长">
                <el-select v-model="predictHorizon" placeholder="选择预测时长">
                  <el-option label="1小时" :value="1" />
                  <el-option label="24小时" :value="24" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 模型描述提示 -->
          <div class="model-hint" v-if="currentModelInfo">
            <el-icon><InfoFilled /></el-icon>
            <span>{{ currentModelInfo.description }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 预测结果图表 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>预测结果</span>
              <el-button-group>
                <el-button :type="chartType === 'line' ? 'primary' : ''" @click="chartType = 'line'">
                  折线图
                </el-button>
                <el-button :type="chartType === 'bar' ? 'primary' : ''" @click="chartType = 'bar'">
                  柱状图
                </el-button>
              </el-button-group>
            </div>
          </template>
          <v-chart class="chart" :option="predictionChartOption" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 预测历史 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>预测历史</span>
              <div class="header-actions">
                <el-button @click="loadPredictionHistory">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
                <el-button type="danger" @click="batchDeletePredictions" :disabled="!selectedPredictions.length">
                  批量删除
                </el-button>
              </div>
            </div>
          </template>

          <el-table :data="predictionHistory" v-loading="historyLoading" @selection-change="handleSelectionChange">
            <el-table-column type="selection" width="55" />
            <el-table-column prop="id" label="ID"  />
            <el-table-column prop="model_type" label="预测模型" width="150">
              <template #default="scope">
                <el-tag :type="getModelTagType(scope.row.model_type)" effect="plain" size="small">
                  {{ getModelLabel(scope.row.model_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="predict_type" label="预测类型">
              <template #default="scope">
                <el-tag>{{ getTypeLabel(scope.row.predict_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="开始时间"  />
            <el-table-column prop="horizon" label="预测时长" >
              <template #default="scope">
                {{ scope.row.horizon }}小时
              </template>
            </el-table-column>
            <el-table-column prop="mape" label="MAPE">
              <template #default="scope">
                {{ scope.row.mape ? scope.row.mape.toFixed(2) + '%' : 'N/A' }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间"  />
            <el-table-column label="操作" >
              <template #default="scope">
                <el-button type="text" @click="viewPredictionDetail(scope.row)">
                  查看详情
                </el-button>
                <el-button type="text" @click="evaluatePrediction(scope.row)" v-if="!scope.row.mape">
                  评估准确度
                </el-button>
                <el-button type="text" style="color: #F56C6C;" @click="deletePrediction(scope.row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 预测详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="预测详情" width="80%">
      <div class="prediction-detail">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="预测ID">{{ currentPrediction.id }}</el-descriptions-item>
          <el-descriptions-item label="预测模型">
            <el-tag :type="getModelTagType(currentPrediction.model_type)" effect="plain" size="small">
              {{ getModelLabel(currentPrediction.model_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预测类型">{{ getTypeLabel(currentPrediction.predict_type) }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ currentPrediction.start_time }}</el-descriptions-item>
          <el-descriptions-item label="预测时长">{{ currentPrediction.horizon }}小时</el-descriptions-item>
          <el-descriptions-item label="MAPE">{{ currentPrediction.mape ? currentPrediction.mape.toFixed(2) + '%' : 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentPrediction.created_at }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-chart" v-if="currentPrediction.data">
          <h4>预测数据</h4>
          <v-chart ref="detailChart" class="chart" :option="detailChartOption" autoresize />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

export default {
  name: 'Predict',
  components: { VChart },
  data() {
    return {
      modelType: 'cnn_lstm',
      predictType: 'multi',
      predictHorizon: 24,
      modelVersion: 'v1.0',
      chartType: 'line',
      singleLoading: false,
      batchLoading: false,
      historyLoading: false,
      predictionHistory: [],
      selectedPredictions: [],
      detailDialogVisible: false,
      currentPrediction: {},
      lastPredictionData: null,
      availableModels: [
        // 默认模型列表（会被后端 API 覆盖）
        { model_type: 'attention_lstm', name: 'Attention-LSTM', description: '双层LSTM+注意力机制', params: '~25K' },
      ],
      predictionChartOption: {
        tooltip: { trigger: 'axis' },
        legend: { data: ['风电预测', '光伏预测', '负荷预测'] },
        xAxis: {
          type: 'category',
          data: Array.from({length: 24}, (_, i) => `${i}:00`)
        },
        yAxis: { type: 'value', name: '功率(MW)' },
        series: [
          { name: '风电预测', type: 'line', data: [] },
          { name: '光伏预测', type: 'line', data: [] },
          { name: '负荷预测', type: 'line', data: [] }
        ]
      }
    }
  },
  computed: {
    currentModelInfo() {
      return this.availableModels.find(m => m.model_type === this.modelType) || null
    },
    detailChartOption() {
      if (!this.currentPrediction.data) return {}
      const normalizeSeriesData = (values) => {
        if (Array.isArray(values)) return values
        if (values === null || values === undefined) return []
        return [values]
      }

      return {
        tooltip: { trigger: 'axis' },
        legend: { data: Object.keys(this.currentPrediction.data) },
        xAxis: {
          type: 'category',
          data: Array.from(
            { length: Math.max(1, this.currentPrediction.horizon || 1) },
            (_, i) => `${i}:00`
          )
        },
        yAxis: { type: 'value', name: '功率(MW)' },
        series: Object.entries(this.currentPrediction.data).map(([key, values]) => ({
          name: this.getTypeLabel(key),
          type: 'line',
          data: normalizeSeriesData(values)
        }))
      }
    }
  },
  watch: {
    chartType() {
      if (this.lastPredictionData) {
        this.updatePredictionChart(this.lastPredictionData)
      }
    }
  },
  mounted() {
    this.loadAvailableModels()
    this.loadPredictionHistory()
  },
  methods: {
    async loadAvailableModels() {
      try {
        const response = await this.$http.get('/api/predict/models')
        if (response && response.data && response.data.code === 200 && Array.isArray(response.data.data)) {
          this.availableModels = response.data.data
        }
      } catch (error) {
        console.warn('加载模型列表失败，使用默认列表', error)
        // 保持使用默认模型列表
      }
    },
    normalizeChartData(values) {
      if (Array.isArray(values)) return values
      if (values === null || values === undefined) return []
      return [values]
    },
    async runSinglePrediction() {
      this.singleLoading = true
      try {
        const response = await this.$http.post('/api/predict/single', {
          type: this.predictType,
          model_type: this.modelType
        })

        if (response && response.data && response.data.code === 200) {
          this.$message.success(`[${this.getModelLabel(this.modelType)}] 单步预测完成`)
          const predictionData = response.data.data?.prediction || null
          if (predictionData) {
            this.updatePredictionChart(predictionData)
          }
          this.loadPredictionHistory()
        } else {
          this.$message.error(response?.data?.message || '单步预测失败')
        }
      } catch (error) {
        this.$message.error('预测执行失败')
      } finally {
        this.singleLoading = false
      }
    },
    async runBatchPrediction() {
      this.batchLoading = true
      try {
        const response = await this.$http.post('/api/predict/batch', {
          model_type: this.modelType
        })

        if (response && response.data && response.data.code === 200) {
          this.$message.success(`[${this.getModelLabel(this.modelType)}] 批量预测完成`)
          const predictionData = response.data.data?.predictions || null
          if (predictionData) {
            this.updatePredictionChart(predictionData)
          }
          // 更新预测指标
          if (response.data.data?.metrics) {
            this.modelAccuracy = response.data.data.metrics.model_accuracy
            this.confidence = response.data.data.metrics.confidence
            this.dataQuality = response.data.data.metrics.data_quality
            const statusMap = {
              'normal': { type: 'success', text: '运行正常' },
              'warning': { type: 'warning', text: '需要注意' },
              'error': { type: 'danger', text: '运行异常' }
            }
            this.modelStatus = statusMap[response.data.data.metrics.model_status] || statusMap['normal']
          }
          this.loadPredictionHistory()
        } else {
          this.$message.error(response?.data?.message || '批量预测失败')
        }
      } catch (error) {
        this.$message.error('批量预测执行失败')
      } finally {
        this.batchLoading = false
      }
    },
    updatePredictionChart(data) {
      if (!data || typeof data !== 'object') return
      this.lastPredictionData = data
      const series = []
      if (data.wind_power) {
        series.push({ name: '风电预测', type: this.chartType, data: this.normalizeChartData(data.wind_power) })
      }
      if (data.pv_power) {
        series.push({ name: '光伏预测', type: this.chartType, data: this.normalizeChartData(data.pv_power) })
      }
      if (data.load) {
        series.push({ name: '负荷预测', type: this.chartType, data: this.normalizeChartData(data.load) })
      }

      const firstSeries = series[0]?.data || []
      const pointCount = Array.isArray(firstSeries) ? firstSeries.length : 24
      this.predictionChartOption = {
        ...this.predictionChartOption,
        xAxis: {
          ...this.predictionChartOption.xAxis,
          data: Array.from({ length: pointCount || 24 }, (_, i) => `${i}:00`)
        },
        series
      }
    },
    async loadPredictionHistory() {
      this.historyLoading = true
      try {
        const response = await this.$http.get('/api/predict/history', {
          params: { limit: 20, type: 'multi' }
        })

        if (response && response.data && response.data.code === 200) {
          this.predictionHistory = response.data.data || []
          if (this.predictionHistory.length > 0 && this.predictionHistory[0].data) {
            this.updatePredictionChart(this.predictionHistory[0].data)
          }
        }
      } catch (error) {
        console.warn('加载预测历史失败，使用空数据', error)
        this.predictionHistory = []
      } finally {
        this.historyLoading = false
      }
    },
    viewPredictionDetail(row) {
      this.currentPrediction = row
      this.detailDialogVisible = true
    },
    async evaluatePrediction(row) {
      try {
        const response = await this.$http.post('/api/predict/evaluate', {
          predict_id: row.id
        })

        if (response && response.data && response.data.code === 200) {
          this.$message.success('预测评估完成')
          if (response.data.data?.overall_mape !== undefined) {
            this.mapeValue = Number(response.data.data.overall_mape.toFixed(2))
            this.modelAccuracy = Number((100 - this.mapeValue).toFixed(2))
          }
          this.loadPredictionHistory()
        } else {
          this.$message.error(response?.data?.message || '预测评估失败')
        }
      } catch (error) {
        this.$message.error('预测评估失败')
      }
    },
    async deletePrediction(row) {
      try {
        await this.$confirm('确定要删除这条预测记录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })

        const response = await this.$http.delete(`/api/predict/${row.id}`)

        if (response && response.data && response.data.code === 200) {
          this.$message.success('预测记录删除成功')
          this.loadPredictionHistory()
        } else {
          this.$message.error(response?.data?.message || '删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.error('删除失败')
        }
      }
    },
    handleSelectionChange(selection) {
      this.selectedPredictions = selection
    },
    async batchDeletePredictions() {
      try {
        await this.$confirm(`确定要删除 ${this.selectedPredictions.length} 条预测记录吗？`, '批量删除', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })

        const predictIds = this.selectedPredictions.map(item => item.id)
        const response = await this.$http.post('/api/predict/batch_delete', {
          predict_ids: predictIds
        })

        if (response && response.data && response.data.code === 200) {
          this.$message.success('批量删除成功')
          this.loadPredictionHistory()
        } else {
          this.$message.error(response?.data?.message || '批量删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.error('批量删除失败')
        }
      }
    },
    getTypeLabel(type) {
      const labels = {
        'wind': '风电',
        'pv': '光伏',
        'load': '负荷',
        'multi': '综合'
      }
      return labels[type] || type
    },
    getModelLabel(modelType) {
      const model = this.availableModels.find(m => m.model_type === modelType)
      if (model) return model.name
      // 降级映射
      const fallback = {
        'attention_lstm': 'Attention-LSTM',
        'standard_lstm': '标准 LSTM',
        'gru': 'GRU',
        'cnn_lstm': 'CNN-LSTM',
        'transformer': 'Transformer'
      }
      return fallback[modelType] || modelType
    },
    getModelTagType(modelType) {
      const tagTypes = {
        'attention_lstm': 'warning',
        'standard_lstm': '',
        'gru': 'success',
        'cnn_lstm': 'danger',
        'transformer': 'primary'
      }
      return tagTypes[modelType] || 'info'
    },
    handleDetailDialogOpened() {
      this.$nextTick(() => {
        const detailChartRef = this.$refs.detailChart
        if (detailChartRef && typeof detailChartRef.resize === 'function') {
          detailChartRef.resize()
        }
      })
    }
  }
}
</script>

<style scoped>
.predict-analysis {
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

.model-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f0f9ff;
  border-radius: 6px;
  color: #409eff;
  font-size: 13px;
  margin-top: 4px;
}

.chart {
  height: 400px;
}

.prediction-detail {
  padding: 20px 0;
}

.detail-chart {
  margin-top: 30px;
}

.detail-chart h4 {
  margin-bottom: 20px;
  color: #303133;
}
</style>
