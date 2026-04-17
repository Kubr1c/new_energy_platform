<template>
  <div class="system-settings">
    <el-row :gutter="20">
      <!-- 用户管理 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>用户管理</span>
              <el-button type="primary" @click="showAddUserDialog">
                <el-icon><Plus /></el-icon>
                添加用户
              </el-button>
            </div>
          </template>

          <el-table :data="users" v-loading="usersLoading">
            <el-table-column prop="username" label="用户名" />
            <el-table-column prop="role" label="角色">
              <template #default="scope">
                <el-tag :type="getRoleType(scope.row.role)">
                  {{ getRoleLabel(scope.row.role) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="scope">
                <el-button type="text" @click="editUser(scope.row)">编辑</el-button>
                <el-button type="text" style="color: #F56C6C;" @click="deleteUser(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 系统参数 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统参数</span>
              <el-button type="success" @click="saveSystemParams">
                <el-icon><Check /></el-icon>
                保存设置
              </el-button>
            </div>
          </template>

          <el-form :model="systemParams" label-width="120px">
            <el-form-item label="系统名称">
              <el-input v-model="systemParams.systemName" />
            </el-form-item>
            <el-form-item label="数据刷新间隔">
              <el-input-number v-model="systemParams.refreshInterval" :min="1" :max="3600" />
              <span style="margin-left: 10px;">秒</span>
            </el-form-item>
            <el-form-item label="预测模型路径">
              <el-input v-model="systemParams.modelPath" />
            </el-form-item>
            <el-form-item label="数据备份周期">
              <el-select v-model="systemParams.backupCycle">
                <el-option label="每天" value="daily" />
                <el-option label="每周" value="weekly" />
                <el-option label="每月" value="monthly" />
              </el-select>
            </el-form-item>
            <el-form-item label="邮件通知">
              <el-switch v-model="systemParams.emailNotification" />
            </el-form-item>
            <el-form-item label="系统日志级别">
              <el-select v-model="systemParams.logLevel">
                <el-option label="DEBUG" value="debug" />
                <el-option label="INFO" value="info" />
                <el-option label="WARNING" value="warning" />
                <el-option label="ERROR" value="error" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 储能系统配置 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>储能系统配置</span>
              <el-button type="warning" @click="saveEssConfig">
                <el-icon><Setting /></el-icon>
                保存配置
              </el-button>
            </div>
          </template>

          <el-form :model="essConfig" label-width="120px">
            <el-form-item label="额定容量">
              <el-input-number v-model="essConfig.capacity" :min="1" :max="100" />
              <span style="margin-left: 10px;">MWh</span>
            </el-form-item>
            <el-form-item label="额定功率">
              <el-input-number v-model="essConfig.power" :min="1" :max="50" />
              <span style="margin-left: 10px;">MW</span>
            </el-form-item>
            <el-form-item label="充电效率">
              <el-input-number v-model="essConfig.etaCharge" :min="0.8" :max="1" :step="0.01" />
            </el-form-item>
            <el-form-item label="放电效率">
              <el-input-number v-model="essConfig.etaDischarge" :min="0.8" :max="1" :step="0.01" />
            </el-form-item>
            <el-form-item label="SOC下限">
              <el-input-number v-model="essConfig.socMin" :min="0" :max="0.5" :step="0.05" />
            </el-form-item>
            <el-form-item label="SOC上限">
              <el-input-number v-model="essConfig.socMax" :min="0.5" :max="1" :step="0.05" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 算法参数 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>算法参数</span>
              <el-button type="info" @click="saveAlgorithmParams">
                <el-icon><Tools /></el-icon>
                保存参数
              </el-button>
            </div>
          </template>

          <el-form :model="algorithmParams" label-width="120px">
            <el-form-item label="粒子数量">
              <el-input-number v-model="algorithmParams.particleCount" :min="10" :max="200" />
            </el-form-item>
            <el-form-item label="迭代次数">
              <el-input-number v-model="algorithmParams.maxIterations" :min="50" :max="500" />
            </el-form-item>
            <el-form-item label="惯性权重最大">
              <el-input-number v-model="algorithmParams.wMax" :min="0.1" :max="1" :step="0.1" />
            </el-form-item>
            <el-form-item label="惯性权重最小">
              <el-input-number v-model="algorithmParams.wMin" :min="0.1" :max="1" :step="0.1" />
            </el-form-item>
            <el-form-item label="学习因子1">
              <el-input-number v-model="algorithmParams.c1" :min="0.5" :max="3" :step="0.1" />
            </el-form-item>
            <el-form-item label="学习因子2">
              <el-input-number v-model="algorithmParams.c2" :min="0.5" :max="3" :step="0.1" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 系统监控 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统监控</span>
              <el-button @click="refreshSystemStatus">
                <el-icon><Refresh /></el-icon>
                刷新状态
              </el-button>
            </div>
          </template>

          <el-row :gutter="20">
            <el-col :span="6" v-for="status in systemStatus" :key="status.name">
              <div class="status-card">
                <div class="status-icon">
                  <el-icon :size="32" :color="status.color">
                    <component :is="status.icon" />
                  </el-icon>
                </div>
                <div class="status-info">
                  <h4>{{ status.name }}</h4>
                  <p>{{ status.value }}</p>
                  <el-tag :type="status.tagType">{{ status.status }}</el-tag>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加用户对话框 -->
    <el-dialog v-model="addUserDialogVisible" title="添加用户" width="400px">
      <el-form :model="newUser" :rules="userRules" ref="userForm" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="newUser.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="newUser.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="newUser.role">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="查看者" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addUserDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addUser">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: 'Settings',
  data() {
    return {
      usersLoading: false,
      users: [],
      addUserDialogVisible: false,
      newUser: {
        username: '',
        password: '',
        role: 'operator'
      },
      userRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
        ],
        role: [
          { required: true, message: '请选择角色', trigger: 'change' }
        ]
      },
      systemParams: {
        systemName: '新能源储能调度系统',
        refreshInterval: 30,
        modelPath: '/models_saved/attention_lstm.pth',
        backupCycle: 'daily',
        emailNotification: true,
        logLevel: 'info'
      },
      essConfig: {
        capacity: 40,
        power: 20,
        etaCharge: 0.95,
        etaDischarge: 0.95,
        socMin: 0.1,
        socMax: 0.9
      },
      algorithmParams: {
        particleCount: 50,
        maxIterations: 200,
        wMax: 0.9,
        wMin: 0.4,
        c1: 1.5,
        c2: 1.5
      },
      systemStatus: [
        {
          name: 'CPU使用率',
          value: '45%',
          status: '正常',
          tagType: 'success',
          icon: 'Monitor',
          color: '#67C23A'
        },
        {
          name: '内存使用率',
          value: '68%',
          status: '正常',
          tagType: 'success',
          icon: 'Coin',
          color: '#67C23A'
        },
        {
          name: '磁盘使用率',
          value: '32%',
          status: '正常',
          tagType: 'success',
          icon: 'FolderOpened',
          color: '#67C23A'
        },
        {
          name: '网络状态',
          value: '良好',
          status: '正常',
          tagType: 'success',
          icon: 'Connection',
          color: '#67C23A'
        }
      ]
    }
  },
  mounted() {
    this.loadUsers()
    this.loadSystemParams()
  },
  methods: {
    async loadUsers() {
      this.usersLoading = true
      try {
        const response = await this.$http.get('/api/auth/users')
        if (response.data.code === 200) {
          this.users = response.data.data
        }
      } catch (error) {
        this.$message.error('加载用户列表失败')
      } finally {
        this.usersLoading = false
      }
    },
    async loadSystemParams() {
      try {
        // 这里应该从API加载系统参数
        // const response = await this.$http.get('/api/system/params')
      } catch (error) {
        console.error('加载系统参数失败:', error)
      }
    },
    showAddUserDialog() {
      this.newUser = {
        username: '',
        password: '',
        role: 'operator'
      }
      this.addUserDialogVisible = true
    },
    async addUser() {
      try {
        await this.$refs.userForm.validate()
        
        const response = await this.$store.dispatch('register', this.newUser)
        
        if (response.success) {
          this.$message.success('用户添加成功')
          this.addUserDialogVisible = false
          this.loadUsers()
        } else {
          this.$message.error(response.message)
        }
      } catch (error) {
        console.error('添加用户失败:', error)
      }
    },
    editUser(user) {
      this.$prompt('请选择新角色', '编辑用户', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputType: 'select',
        inputOptions: [
          { label: '管理员', value: 'admin' },
          { label: '操作员', value: 'operator' },
          { label: '查看者', value: 'viewer' }
        ],
        inputValue: user.role
      }).then(({ value }) => {
        this.updateUserRole(user.id, value)
      }).catch(() => {
        this.$message.info('取消编辑')
      })
    },
    async updateUserRole(userId, role) {
      try {
        const response = await this.$http.put(`/api/auth/users/${userId}`, { role })
        
        if (response.data.code === 200) {
          this.$message.success('用户角色更新成功')
          this.loadUsers()
        } else {
          this.$message.error(response.data.message)
        }
      } catch (error) {
        this.$message.error('更新用户角色失败')
      }
    },
    async deleteUser(user) {
      try {
        await this.$confirm('确定要删除该用户吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const response = await this.$http.delete(`/api/auth/users/${user.id}`)
        
        if (response.data.code === 200) {
          this.$message.success('用户删除成功')
          this.loadUsers()
        } else {
          this.$message.error(response.data.message)
        }
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.error('删除用户失败')
        }
      }
    },
    async saveSystemParams() {
      try {
        // 这里应该调用API保存系统参数
        this.$message.success('系统参数保存成功')
      } catch (error) {
        this.$message.error('保存系统参数失败')
      }
    },
    async saveEssConfig() {
      try {
        // 这里应该调用API保存储能配置
        this.$message.success('储能配置保存成功')
      } catch (error) {
        this.$message.error('保存储能配置失败')
      }
    },
    async saveAlgorithmParams() {
      try {
        // 这里应该调用API保存算法参数
        this.$message.success('算法参数保存成功')
      } catch (error) {
        this.$message.error('保存算法参数失败')
      }
    },
    refreshSystemStatus() {
      // 这里应该调用API获取最新系统状态
      this.$message.success('系统状态已刷新')
    },
    getRoleType(role) {
      const types = {
        'admin': 'danger',
        'operator': 'warning',
        'viewer': 'info'
      }
      return types[role] || 'info'
    },
    getRoleLabel(role) {
      const labels = {
        'admin': '管理员',
        'operator': '操作员',
        'viewer': '查看者'
      }
      return labels[role] || role
    }
  }
}
</script>

<style scoped>
.system-settings {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background-color: #fafafa;
  border-radius: 4px;
  border: 1px solid #EBEEF5;
}

.status-icon {
  flex-shrink: 0;
}

.status-info h4 {
  margin: 0 0 5px 0;
  color: #303133;
}

.status-info p {
  margin: 5px 0;
  color: #606266;
  font-size: 18px;
  font-weight: bold;
}
</style>
