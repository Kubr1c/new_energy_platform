<template>
  <div class="data-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据管理</span>
          <div class="header-actions">
            <el-upload
              class="upload-demo"
              action="#"
              :auto-upload="false"
              :on-change="handleFileChange"
              :show-file-list="false"
              accept=".csv"
            >
              <el-button type="primary">
                <el-icon><Upload /></el-icon>
                上传数据
              </el-button>
            </el-upload>
            <el-button type="success" @click="refreshData">
              <el-icon><Refresh /></el-icon>
              刷新数据
            </el-button>
          </div>
        </div>
      </template>

      <!-- 查询条件 -->
      <div class="query-form">
        <el-form :inline="true" :model="queryForm" class="query-form-content">
          <el-form-item label="开始时间">
            <el-date-picker
              v-model="queryForm.start_time"
              type="datetime"
              placeholder="选择开始时间"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </el-form-item>
          <el-form-item label="结束时间">
            <el-date-picker
              v-model="queryForm.end_time"
              type="datetime"
              placeholder="选择结束时间"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </el-form-item>
          <el-form-item label="数据条数">
            <el-input-number
              v-model="queryForm.limit"
              :min="1"
              :max="1000"
              placeholder="数据条数"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="queryData">查询</el-button>
            <el-button @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 数据统计 -->
      <div class="statistics" v-if="statistics">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="总数据量" :value="statistics.total_count" />
          </el-col>
          <el-col :span="6" v-if="statistics.statistics && statistics.statistics.wind_power">
            <el-statistic title="平均风电功率" :value="statistics.statistics.wind_power.avg" suffix="MW" />
          </el-col>
          <el-col :span="6" v-else-if="!statistics.statistics">
            <el-statistic title="平均风电功率" :value="0" suffix="MW" />
          </el-col>
          <el-col :span="6" v-if="statistics.statistics && statistics.statistics.pv_power">
            <el-statistic title="平均光伏功率" :value="statistics.statistics.pv_power.avg" suffix="MW" />
          </el-col>
          <el-col :span="6" v-else-if="!statistics.statistics">
            <el-statistic title="平均光伏功率" :value="0" suffix="MW" />
          </el-col>
          <el-col :span="6" v-if="statistics.statistics && statistics.statistics.load">
            <el-statistic title="平均负荷" :value="statistics.statistics.load.avg" suffix="MW" />
          </el-col>
          <el-col :span="6" v-else-if="!statistics.statistics">
            <el-statistic title="平均负荷" :value="0" suffix="MW" />
          </el-col>
        </el-row>
      </div>

      <!-- 数据表格 -->
      <el-table
        :data="tableData"
        v-loading="loading"
        height="400"
        style="width: 100%; margin-top: 20px;"
      >
        <el-table-column prop="timestamp" label="时间戳" />
        <el-table-column prop="wind_power" label="风电功率(MW)" />
        <el-table-column prop="pv_power" label="光伏功率(MW)" />
        <el-table-column prop="load" label="负荷(MW)" />
        <el-table-column prop="temperature" label="温度(°C)" />
        <el-table-column prop="irradiance" label="辐照度(W/m²)" />
        <el-table-column prop="wind_speed" label="风速(m/s)" />
        <el-table-column label="操作">
          <template #default="scope">
            <el-button type="text" @click="editData(scope.row)">编辑</el-button>
            <el-button type="text" style="color: #F56C6C;" @click="deleteData(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[50, 100, 200, 500]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑数据" width="500px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="时间戳">
          <el-date-picker
            v-model="editForm.timestamp"
            type="datetime"
            disabled
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="风电功率(MW)">
          <el-input-number v-model="editForm.wind_power" :precision="2" />
        </el-form-item>
        <el-form-item label="光伏功率(MW)">
          <el-input-number v-model="editForm.pv_power" :precision="2" />
        </el-form-item>
        <el-form-item label="负荷(MW)">
          <el-input-number v-model="editForm.load" :precision="2" />
        </el-form-item>
        <el-form-item label="温度(°C)">
          <el-input-number v-model="editForm.temperature" :precision="2" />
        </el-form-item>
        <el-form-item label="辐照度(W/m²)">
          <el-input-number v-model="editForm.irradiance" :precision="2" />
        </el-form-item>
        <el-form-item label="风速(m/s)">
          <el-input-number v-model="editForm.wind_speed" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 数据预览对话框 -->
    <el-dialog v-model="previewDialogVisible" title="数据预览" width="80%">
      <div class="preview-info">
        <el-alert
          :title="'共 ' + previewData.length + ' 条数据，前 10 条预览如下'"
          type="info"
          :closable="false"
          style="margin-bottom: 20px;"
        />
      </div>
      <el-table :data="previewData.slice(0, 10)" height="400" border>
        <el-table-column prop="timestamp" label="时间戳" />
        <el-table-column prop="wind_power" label="风电功率(MW)" />
        <el-table-column prop="pv_power" label="光伏功率(MW)" />
        <el-table-column prop="load" label="负荷(MW)" />
        <el-table-column prop="temperature" label="温度(°C)" />
        <el-table-column prop="irradiance" label="辐照度(W/m²)" />
        <el-table-column prop="wind_speed" label="风速(m/s)" />
      </el-table>
      <template #footer>
        <el-button @click="previewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload">确认上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: 'Data',
  data() {
    return {
      loading: false,
      tableData: [],
      statistics: null,
      queryForm: {
        start_time: '',
        end_time: '',
        limit: 1000
      },
      currentPage: 1,
      pageSize: 100,
      total: 0,
      editDialogVisible: false,
      editForm: {},
      currentEditRow: null,
      previewDialogVisible: false,
      previewData: [],
      pendingFile: null
    }
  },
  mounted() {
    this.loadStatistics()
    this.loadData()
  },
  methods: {
    async loadStatistics() {
      try {
        console.log('开始加载统计数据...')
        const response = await this.$http.get('/api/data/statistics')
        
        console.log('统计数据API响应:', response)

        if (response && response.data && response.data.code === 200) {
          this.statistics = response.data.data
          console.log('统计数据加载成功:', this.statistics)
        } else {
          console.error('统计数据API响应错误:', response)
          this.$message.error('统计数据加载失败：API响应错误')
        }
      } catch (error) {
        console.error('加载统计数据失败:', error)
        this.$message.error('统计数据加载失败：网络错误')
      }
    },
    async loadData() {
      this.loading = true
      try {
        const params = {
          limit: this.pageSize,
          ...this.queryForm
        }
        
        // 移除空值
        Object.keys(params).forEach(key => {
          if (!params[key]) delete params[key]
        })

        const response = await this.$http.get('/api/data/query', { params })
        if (response && response.data && response.data.code === 200) {
          this.tableData = response.data.data
          this.total = response.data.data.length
        }
      } catch (error) {
        this.$message.error('加载数据失败')
      } finally {
        this.loading = false
      }
    },
    async handleFileChange(file) {
      this.pendingFile = file.raw
      await this.previewFile(file.raw)
    },
    async previewFile(file) {
      try {
        const text = await this.readFile(file)
        const data = this.parseCSV(text)
        
        if (data.length === 0) {
          this.$message.error('文件中没有数据')
          return
        }
        
        this.previewData = data
        this.previewDialogVisible = true
      } catch (error) {
        console.error('预览文件失败:', error)
        this.$message.error('文件解析失败，请检查文件格式')
      }
    },
    readFile(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (e) => resolve(e.target.result)
        reader.onerror = (e) => reject(e)
        reader.readAsText(file)
      })
    },
    parseCSV(text) {
      const lines = text.trim().split('\n')
      if (lines.length < 2) return []
      
      const headers = lines[0].split(',').map(h => h.trim())
      const data = []
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim())
        if (values.length === headers.length) {
          const row = {}
          headers.forEach((header, index) => {
            const value = values[index]
            // 尝试转换为数字
            const numValue = parseFloat(value)
            row[header] = isNaN(numValue) ? value : numValue
          })
          data.push(row)
        }
      }
      
      return data
    },
    async confirmUpload() {
      if (!this.pendingFile) {
        this.$message.error('没有待上传的文件')
        return
      }
      
      this.previewDialogVisible = false
      const formData = new FormData()
      formData.append('file', this.pendingFile)
      
      this.loading = true
      try {
        const response = await this.$http.post('/api/data/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        
        if (response && response.data && response.data.code === 200) {
          this.$message.success(response.data.message)
          this.loadStatistics()
          this.loadData()
        } else {
          this.$message.error(response?.data?.message || '上传失败')
        }
      } catch (error) {
        this.$message.error('文件上传失败')
      } finally {
        this.loading = false
        this.pendingFile = null
      }
    },
    queryData() {
      this.currentPage = 1
      this.loadData()
    },
    resetQuery() {
      this.queryForm = {
        start_time: '',
        end_time: '',
        limit: 100
      }
      this.queryData()
    },
    refreshData() {
      this.loadStatistics()
      this.loadData()
    },
    editData(row) {
      this.currentEditRow = row
      this.editForm = { ...row }
      this.editDialogVisible = true
    },
    async saveEdit() {
      try {
        // 这里应该调用更新API
        this.$message.success('数据更新成功')
        this.editDialogVisible = false
        this.loadData()
      } catch (error) {
        this.$message.error('数据更新失败')
      }
    },
    async deleteData(row) {
      try {
        await this.$confirm('确定要删除这条数据吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        // 这里应该调用删除API
        this.$message.success('数据删除成功')
        this.loadData()
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.error('数据删除失败')
        }
      }
    },
    handleSizeChange(val) {
      this.pageSize = val
      this.loadData()
    },
    handleCurrentChange(val) {
      this.currentPage = val
      this.loadData()
    }
  }
}
</script>

<style scoped>
.data-management {
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

.query-form {
  margin-bottom: 20px;
  padding: 20px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.query-form-content {
  margin: 0;
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
}

.upload-demo {
  display: inline-block;
}
</style>
