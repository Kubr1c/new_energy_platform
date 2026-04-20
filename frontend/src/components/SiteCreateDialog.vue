<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="500px"
    :before-close="handleClose"
    destroy-on-close
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      label-position="left"
      status-icon
    >
      <el-form-item label="站点名称" prop="name">
        <el-input
          v-model="form.name"
          placeholder="请输入储能站点名称"
          maxlength="100"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="容量 (MWh)" prop="capacity">
        <el-input-number
          v-model="form.capacity"
          :min="0.1"
          :max="1000"
          :step="0.1"
          placeholder="请输入额定容量"
          style="width: 100%"
        />
        <span class="unit">MWh</span>
      </el-form-item>

      <el-form-item label="功率 (MW)" prop="power">
        <el-input-number
          v-model="form.power"
          :min="0.1"
          :max="500"
          :step="0.1"
          placeholder="请输入最高功率"
          style="width: 100%"
        />
        <span class="unit">MW</span>
      </el-form-item>

      <el-form-item label="健康度 (SOH)" prop="soh">
        <el-slider
          v-model="form.soh"
          :min="0.1"
          :max="1"
          :step="0.01"
          show-input
          input-size="small"
          :format-tooltip="formatSoh"
        />
        <span class="unit">{{ (form.soh * 100).toFixed(1) }}%</span>
      </el-form-item>

      <el-form-item label="经纬度" required>
        <div class="coordinate-inputs">
          <el-input-number
            v-model="form.longitude"
            :min="73"
            :max="135"
            :step="0.0001"
            placeholder="经度"
            style="width: 48%; margin-right: 4%"
            controls-position="right"
          />
          <el-input-number
            v-model="form.latitude"
            :min="3"
            :max="54"
            :step="0.0001"
            placeholder="纬度"
            style="width: 48%"
            controls-position="right"
          />
        </div>
        <div class="coordinate-hint">
          <span v-if="form.longitude && form.latitude">
            坐标: {{ form.longitude.toFixed(4) }}, {{ form.latitude.toFixed(4) }}
          </span>
          <span v-else style="color: #909399">
            请在地图上点击选择位置或手动输入坐标
          </span>
        </div>
      </el-form-item>

      <el-form-item label="详细地址" prop="address">
        <el-input
          v-model="form.address"
          type="textarea"
          :rows="2"
          placeholder="请输入详细地址"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="备注" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="2"
          placeholder="请输入备注信息"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="form.status">
          <el-radio label="active">运行中</el-radio>
          <el-radio label="maintenance">维护中</el-radio>
          <el-radio label="planned">规划中</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          创建站点
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script>
import { createSite } from '@/utils/api'

export default {
  name: 'SiteCreateDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    coordinates: {
      type: Array,
      default: () => [null, null]
    },
    adcode: {
      type: String,
      default: '100000'
    }
  },
  emits: ['update:modelValue', 'created'],
  data() {
    return {
      submitting: false,
      form: {
        name: '',
        capacity: 40.0,
        power: 20.0,
        soh: 0.985,
        longitude: null,
        latitude: null,
        address: '',
        description: '',
        status: 'active'
      },
      rules: {
        name: [
          { required: true, message: '请输入站点名称', trigger: 'blur' },
          { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
        ],
        capacity: [
          { required: true, message: '请输入额定容量', trigger: 'blur' },
          { type: 'number', min: 0.1, max: 1000, message: '容量范围 0.1-1000 MWh', trigger: 'blur' }
        ],
        power: [
          { required: true, message: '请输入最高功率', trigger: 'blur' },
          { type: 'number', min: 0.1, max: 500, message: '功率范围 0.1-500 MW', trigger: 'blur' }
        ],
        soh: [
          { required: true, message: '请输入健康度', trigger: 'blur' },
          { type: 'number', min: 0.1, max: 1, message: '健康度范围 0.1-1', trigger: 'blur' }
        ],
        address: [
          { required: false, message: '请输入地址', trigger: 'blur' }
        ]
      }
    }
  },
  computed: {
    visible: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      }
    },
    dialogTitle() {
      return this.form.longitude && this.form.latitude 
        ? `创建储能站点 (${this.form.longitude.toFixed(4)}, ${this.form.latitude.toFixed(4)})`
        : '创建储能站点'
    }
  },
  watch: {
    coordinates: {
      immediate: true,
      handler(newVal) {
        if (newVal && newVal.length >= 2) {
          this.form.longitude = newVal[0]
          this.form.latitude = newVal[1]
        }
      }
    }
  },
  methods: {
    formatSoh(value) {
      return `${(value * 100).toFixed(1)}%`
    },
    handleClose() {
      this.visible = false
      this.resetForm()
    },
    resetForm() {
      this.form = {
        name: '',
        capacity: 40.0,
        power: 20.0,
        soh: 0.985,
        longitude: null,
        latitude: null,
        address: '',
        description: '',
        status: 'active'
      }
      if (this.$refs.formRef) {
        this.$refs.formRef.resetFields()
      }
    },
    async handleSubmit() {
      try {
        const valid = await this.$refs.formRef.validate()
        if (!valid) return
        
        // 验证坐标
        if (!this.form.longitude || !this.form.latitude) {
          this.$message.error('请选择或输入坐标位置')
          return
        }

        this.submitting = true

        // 准备提交数据
        const siteData = {
          name: this.form.name,
          adcode: this.adcode,
          capacity_mwh: this.form.capacity,
          power_mw: this.form.power,
          soh_percent: this.form.soh * 100, // 转换为百分比
          longitude: this.form.longitude,
          latitude: this.form.latitude,
          address: this.form.address,
          status: this.form.status
        }

        const result = await createSite(siteData)

        if (result.success) {
          this.$message.success('站点创建成功')
          this.$emit('created', result.data)
          this.handleClose()
        } else {
          this.$message.error(`创建失败: ${result.message}`)
        }
      } catch (error) {
        console.error('创建站点失败:', error)
        this.$message.error(`创建失败: ${error.message}`)
      } finally {
        this.submitting = false
      }
    }
  }
}
</script>

<style scoped>
.unit {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}

.coordinate-inputs {
  display: flex;
  justify-content: space-between;
}

.coordinate-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #67c23a;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>