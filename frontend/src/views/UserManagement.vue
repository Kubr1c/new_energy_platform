<template>
  <div class="user-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="showAddUserDialog">
            <el-icon><Plus /></el-icon>
            新增用户
          </el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="搜索用户名"
              @input="handleSearch"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="6">
            <el-select v-model="roleFilter" placeholder="选择角色" @change="handleSearch" clearable>
              <el-option label="全部角色" value="" />
              <el-option label="管理员" value="admin" />
              <el-option label="操作员" value="operator" />
              <el-option label="查看者" value="viewer" />
            </el-select>
          </el-col>
          <el-col :span="10">
            <el-button @click="loadUsers">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 用户表格 -->
      <el-table 
        :data="filteredUsers" 
        v-loading="usersLoading" 
        style="margin-top: 20px;"
        stripe
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="scope">
            <el-tag :type="getRoleType(scope.row.role)">
              {{ getRoleLabel(scope.row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <!-- <el-table-column prop="last_login" label="最近登录" width="180">
          <template #default="scope">
            {{ scope.row.last_login ? formatDateTime(scope.row.last_login) : '从未登录' }}
          </template>
        </el-table-column> -->
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button type="text" @click="editUser(scope.row)">编辑</el-button>
            <el-button type="text" @click="resetPassword(scope.row)">重置密码</el-button>
            <el-button 
              type="text" 
              style="color: #F56C6C;" 
              @click="deleteUser(scope.row)"
              :disabled="scope.row.id === currentUserId"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalUsers"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增用户弹窗 -->
    <el-dialog v-model="addUserDialogVisible" title="新增用户" width="500px">
      <el-form :model="newUser" :rules="userRules" ref="userForm" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="newUser.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="newUser.password" 
            type="password" 
            show-password 
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input 
            v-model="newUser.confirmPassword" 
            type="password" 
            show-password 
            placeholder="请再次输入密码"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="newUser.role" placeholder="请选择角色">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="查看者" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="newUser.email" placeholder="请输入邮箱（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addUserDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addUser" :loading="addUserLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户弹窗 -->
    <el-dialog v-model="editUserDialogVisible" title="编辑用户" width="500px">
      <el-form :model="editUserForm" :rules="editUserRules" ref="editUserFormRef" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="editUserForm.username" disabled />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="editUserForm.role" placeholder="请选择角色">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="查看者" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="editUserForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="editUserForm.status" placeholder="请选择状态">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
            <el-option label="锁定" value="locked" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editUserDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="updateUser" :loading="updateUserLoading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="resetPasswordDialogVisible" title="重置密码" width="400px">
      <el-form :model="resetPasswordForm" :rules="resetPasswordRules" ref="resetPasswordFormRef" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="resetPasswordForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input 
            v-model="resetPasswordForm.newPassword" 
            type="password" 
            show-password 
            placeholder="请输入新密码"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input 
            v-model="resetPasswordForm.confirmPassword" 
            type="password" 
            show-password 
            placeholder="请再次输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPasswordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmResetPassword" :loading="resetPasswordLoading">重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: 'UserManagement',
  data() {
    return {
      usersLoading: false,
      users: [],
      searchQuery: '',
      roleFilter: '',
      currentPage: 1,
      pageSize: 20,
      totalUsers: 0,
      
      // 新增用户弹窗
      addUserDialogVisible: false,
      addUserLoading: false,
      newUser: {
        username: '',
        password: '',
        confirmPassword: '',
        role: 'operator',
        email: ''
      },
      
      // 编辑用户弹窗
      editUserDialogVisible: false,
      updateUserLoading: false,
      editUserForm: {
        id: null,
        username: '',
        role: 'operator',
        email: '',
        status: 'active'
      },
      
      // 重置密码弹窗
      resetPasswordDialogVisible: false,
      resetPasswordLoading: false,
      resetPasswordForm: {
        id: null,
        username: '',
        newPassword: '',
        confirmPassword: ''
      },
      
      // 表单校验规则
      userRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '用户名长度应为 3-20 个字符', trigger: 'blur' },
          { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, max: 20, message: '密码长度应为 6-20 个字符', trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, message: '请确认密码', trigger: 'blur' },
          { validator: this.validateConfirmPassword, trigger: 'blur' }
        ],
        role: [
          { required: true, message: '请选择角色', trigger: 'change' }
        ],
        email: [
          { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
        ]
      },
      
      editUserRules: {
        role: [
          { required: true, message: '请选择角色', trigger: 'change' }
        ],
        email: [
          { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
        ],
        status: [
          { required: true, message: '请选择状态', trigger: 'change' }
        ]
      },
      
      resetPasswordRules: {
        newPassword: [
          { required: true, message: '请输入新密码', trigger: 'blur' },
          { min: 6, max: 20, message: '密码长度应为 6-20 个字符', trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, message: '请确认新密码', trigger: 'blur' },
          { validator: this.validateResetConfirmPassword, trigger: 'blur' }
        ]
      }
    }
  },
  computed: {
    filteredUsers() {
      let filtered = this.users
      
      // 按用户名搜索
      if (this.searchQuery) {
        filtered = filtered.filter(user => 
          user.username.toLowerCase().includes(this.searchQuery.toLowerCase())
        )
      }
      
      // 按角色过滤
      if (this.roleFilter) {
        filtered = filtered.filter(user => user.role === this.roleFilter)
      }
      
      return filtered
    },
    currentUserId() {
      return this.$store.getters.user?.id
    }
  },
  mounted() {
    this.loadUsers()
  },
  methods: {
    async loadUsers() {
      this.usersLoading = true
      try {
        const response = await this.$http.get('/api/auth/users')
        if (response && response.code === 200) {
          const userList = Array.isArray(response.data) ? response.data : []
          this.users = userList.map(user => ({
            ...user,
            email: user.email || '',
            status: user.status || 'active',
            last_login: user.last_login || null
          }))
          this.totalUsers = this.users.length
        } else {
          this.$message.error(response?.message || '加载用户列表失败')
        }
      } catch (error) {
        console.error('加载用户列表失败:', error)
        this.$message.error('加载用户列表失败')
      } finally {
        this.usersLoading = false
      }
    },
    
    handleSearch() {
      this.currentPage = 1
    },
    
    handleSizeChange(newSize) {
      this.pageSize = newSize
      this.currentPage = 1
    },
    
    handleCurrentChange(newPage) {
      this.currentPage = newPage
    },
    
    showAddUserDialog() {
      this.newUser = {
        username: '',
        password: '',
        confirmPassword: '',
        role: 'operator',
        email: ''
      }
      this.addUserDialogVisible = true
    },
    
    async addUser() {
      try {
        await this.$refs.userForm.validate()
        this.addUserLoading = true
        
        const response = await this.$store.dispatch('register', {
          username: this.newUser.username,
          password: this.newUser.password,
          role: this.newUser.role
        })
        
        if (response.success) {
          this.$message.success('新增用户成功')
          this.addUserDialogVisible = false
          this.loadUsers()
        } else {
          this.$message.error(response.message || '新增用户失败')
        }
      } catch (error) {
        console.error('新增用户失败:', error)
        this.$message.error('新增用户失败')
      } finally {
        this.addUserLoading = false
      }
    },
    
    editUser(user) {
      this.editUserForm = {
        id: user.id,
        username: user.username,
        role: user.role,
        email: user.email || '',
        status: user.status || 'active'
      }
      this.editUserDialogVisible = true
    },
    
    async updateUser() {
      try {
        await this.$refs.editUserFormRef.validate()
        this.updateUserLoading = true
        
        const response = await this.$http.put(`/api/auth/users/${this.editUserForm.id}`, {
          role: this.editUserForm.role,
          email: this.editUserForm.email,
          status: this.editUserForm.status
        })
        
        if (response && response.code === 200) {
          this.$message.success('用户信息更新成功')
          this.editUserDialogVisible = false
          this.loadUsers()
        } else {
          this.$message.error(response?.message || '更新用户失败')
        }
      } catch (error) {
        console.error('更新用户失败:', error)
        this.$message.error('更新用户失败')
      } finally {
        this.updateUserLoading = false
      }
    },
    
    resetPassword(user) {
      this.resetPasswordForm = {
        id: user.id,
        username: user.username,
        newPassword: '',
        confirmPassword: ''
      }
      this.resetPasswordDialogVisible = true
    },
    
    async confirmResetPassword() {
      try {
        await this.$refs.resetPasswordFormRef.validate()
        this.resetPasswordLoading = true
        
        const response = await this.$http.post(`/api/auth/users/${this.resetPasswordForm.id}/reset_password`, {
          new_password: this.resetPasswordForm.newPassword
        })
        
        if (response && response.code === 200) {
          this.$message.success('密码重置成功')
          this.resetPasswordDialogVisible = false
        } else {
          this.$message.error(response?.message || '重置密码失败')
        }
      } catch (error) {
        console.error('重置密码失败:', error)
        this.$message.error('重置密码失败')
      } finally {
        this.resetPasswordLoading = false
      }
    },
    
    async deleteUser(user) {
      try {
        await this.$confirm('确定要删除该用户吗？', '警告', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const response = await this.$http.delete(`/api/auth/users/${user.id}`)
        
        if (response && response.code === 200) {
          this.$message.success('删除用户成功')
          this.loadUsers()
        } else {
          this.$message.error(response?.message || '删除用户失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除用户失败:', error)
          this.$message.error('删除用户失败')
        }
      }
    },
    
    validateConfirmPassword(rule, value, callback) {
      if (value !== this.newUser.password) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    },
    
    validateResetConfirmPassword(rule, value, callback) {
      if (value !== this.resetPasswordForm.newPassword) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
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
    },
    
    getStatusType(status) {
      const types = {
        'active': 'success',
        'inactive': 'warning',
        'locked': 'danger'
      }
      return types[status] || 'info'
    },
    
    getStatusLabel(status) {
      const labels = {
        'active': '启用',
        'inactive': '停用',
        'locked': '锁定'
      }
      return labels[status] || status
    },
    
    formatDateTime(dateString) {
      if (!dateString) return '-'
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }
  }
}
</script>

<style scoped>
.user-management {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-bar {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  text-align: right;
}

.el-table {
  margin-top: 20px;
}
</style>
