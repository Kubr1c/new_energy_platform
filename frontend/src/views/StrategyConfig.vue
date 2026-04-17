<template>
  <div class="strategy-config">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span class="header-title"><el-icon><Setting /></el-icon> 现货市场电价与协同响应(DR)策略配置</span>
          <el-button type="primary" :loading="saving" @click="saveStrategy">
            保存并立即生效
          </el-button>
        </div>
      </template>

      <!-- 需求响应比例 -->
      <div class="config-section">
        <h3>1. 需求响应 (Demand Response) 弹性比例</h3>
        <p class="section-desc">设定调度区域内能够响应平台指令，进行时间平移的“活体负荷”占比（如非紧急生产线、可调温空调等）。</p>
        <div class="slider-container">
          <el-slider 
            v-model="form.dr_ratio_percent" 
            :step="1" 
            :min="0" 
            :max="100" 
            show-input 
            :format-tooltip="val => val + '%'">
          </el-slider>
        </div>
      </div>

      <el-divider />

      <!-- 分时单价设定 -->
      <div class="config-section">
        <h3>2. 鸭子曲线五阶单价设定 (元/MWh)</h3>
        <p class="section-desc">请根据当前现货市场行情或当地电网企业代理购电价格，拟定未来24小时可能的绝对价格梯度。</p>
        
        <el-row :gutter="20" class="price-row">
          <el-col :span="4" v-for="tier in tiers" :key="tier.key">
            <div class="price-card" :style="{ borderTopColor: tier.color }">
              <div class="tier-name" :style="{ color: tier.color }">{{ tier.label }}</div>
              <el-input-number 
                v-model="form[tier.key]" 
                :min="0" :max="5000" :step="10" 
                controls-position="right"
                style="width: 100%" />
            </div>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 24小时时段分布 -->
      <div class="config-section">
        <h3>3. 24小时分段映射 (Time-of-Use Mapping)</h3>
        <p class="section-desc">将一天中的 24 个小时划分入 5 种价格梯度区间。系统会自动按照此分布计算经济最优解。</p>
        
        <div class="hours-grid">
          <div v-for="hour in 24" :key="hour-1" class="hour-item">
            <div class="hour-label">{{ formatHour(hour-1) }}</div>
            <el-select v-model="form.tou_config[hour-1]" size="small" :style="{ backgroundColor: getTierColor(form.tou_config[hour-1]) + '20' }">
              <el-option 
                v-for="tier in tiers" 
                :key="tier.id" 
                :label="tier.label" 
                :value="tier.id">
                <span :style="{ color: tier.color, fontWeight: 'bold' }">{{ tier.label }}</span>
              </el-option>
            </el-select>
          </div>
        </div>
      </div>

    </el-card>
  </div>
</template>

<script>
export default {
  name: 'StrategyConfig',
  data() {
    return {
      saving: false,
      tiers: [
        { id: 'extreme_peak', key: 'extreme_peak_price', label: '尖峰 (Extreme Peak)', color: '#F56C6C' },
        { id: 'peak', key: 'peak_price', label: '高峰 (Peak)', color: '#E6A23C' },
        { id: 'flat', key: 'flat_price', label: '平时 (Flat)', color: '#909399' },
        { id: 'valley', key: 'valley_price', label: '低谷 (Valley)', color: '#67C23A' },
        { id: 'deep_valley', key: 'deep_valley_price', label: '深谷 (Deep Valley)', color: '#409EFF' }
      ],
      form: {
        extreme_peak_price: 1200,
        peak_price: 1020,
        flat_price: 600,
        valley_price: 180,
        deep_valley_price: 60,
        dr_ratio_percent: 20,
        tou_config: {}
      }
    }
  },
  created() {
    // 初始化默认全为平时
    for (let i = 0; i < 24; i++) {
      this.form.tou_config[i] = 'flat'
    }
  },
  mounted() {
    this.fetchStrategy()
  },
  methods: {
    formatHour(h) {
      return `${h.toString().padStart(2, '0')}:00`
    },
    getTierColor(tierId) {
      const tier = this.tiers.find(t => t.id === tierId)
      return tier ? tier.color : '#909399'
    },
    async fetchStrategy() {
      try {
        const response = await this.$http.get('/api/config/strategy')
        if (response.data && response.data.code === 200) {
          const data = response.data.data
          this.form.extreme_peak_price = data.extreme_peak_price
          this.form.peak_price = data.peak_price
          this.form.flat_price = data.flat_price
          this.form.valley_price = data.valley_price
          this.form.deep_valley_price = data.deep_valley_price
          this.form.dr_ratio_percent = Math.round((data.dr_ratio || 0) * 100)
          
          // 处理tou_config
          if (data.tou_config) {
            for (let i = 0; i < 24; i++) {
              if (data.tou_config[String(i)]) {
                this.form.tou_config[i] = data.tou_config[String(i)]
              }
            }
          }
        }
      } catch (error) {
        console.error('获取策略出错:', error)
        this.$message.error('无法读取策略配置，请检查后端运行状态。')
      }
    },
    async saveStrategy() {
      this.saving = true;
      try {
        const payload = {
          extreme_peak_price: this.form.extreme_peak_price,
          peak_price: this.form.peak_price,
          flat_price: this.form.flat_price,
          valley_price: this.form.valley_price,
          deep_valley_price: this.form.deep_valley_price,
          dr_ratio: this.form.dr_ratio_percent / 100.0,
          tou_config: {}
        }
        
        for (let i = 0; i < 24; i++) {
          payload.tou_config[String(i)] = this.form.tou_config[i]
        }

        const response = await this.$http.post('/api/config/strategy', payload)
        if (response.data && response.data.code === 200) {
          this.$message.success('配置已保存并全网生效！下一次执行调度将应用此策略。')
        } else {
          this.$message.error('保存失败: ' + (response.data.message || '未知错误'))
        }
      } catch (error) {
        console.error('保存策略出错:', error)
        this.$message.error('保存失败，网络或服务器发生错误。')
      } finally {
        this.saving = false;
      }
    }
  }
}
</script>

<style scoped>
.strategy-config {
  padding: 10px;
}
.box-card {
  min-height: calc(100vh - 120px);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-title {
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 8px;
}
.config-section {
  margin-bottom: 30px;
}
.config-section h3 {
  margin-bottom: 10px;
  color: #303133;
}
.section-desc {
  font-size: 14px;
  color: #909399;
  margin-bottom: 20px;
}
.slider-container {
  padding: 0 20px;
}
.price-row {
  display: flex;
  justify-content: space-between;
}
.price-card {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  border-top: 4px solid #ddd;
  text-align: center;
}
.tier-name {
  font-weight: bold;
  margin-bottom: 15px;
  font-size: 14px;
}
.hours-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}
.hour-item {
  width: calc(16.666% - 15px); /* 6 items per row */
  background: white;
  border: 1px solid #EBEEF5;
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.hour-label {
  font-weight: bold;
  color: #606266;
  margin-bottom: 8px;
  text-align: center;
}
/* 使选择器的背景色也有一点透明指示 */
:deep(.el-select .el-input__wrapper) {
  background-color: transparent !important;
}
</style>
