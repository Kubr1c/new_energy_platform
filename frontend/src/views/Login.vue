<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <h2>新能源储能调度系统</h2>
        <p>智能优化调度平台</p>
      </div>
      
      <el-form
        ref="loginForm"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            size="large"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            class="login-button"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <p>默认管理员账号: admin / admin123</p>
        <p>默认操作员账号: operator / operator123</p>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'

export default {
  name: 'Login',
  data() {
    return {
      loginForm: {
        username: '',
        password: ''
      },
      loginRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
        ]
      }
    }
  },
  computed: {
    ...mapGetters(['loading', 'isAuthenticated'])
  },
  methods: {
    ...mapActions(['login']),
    async handleLogin() {
      try {
        await this.$refs.loginForm.validate()
        
        const result = await this.login(this.loginForm)
        
        if (result.success) {
          this.$message.success('登录成功')
          this.$router.push('/dashboard')
        } else {
          this.$message.error(result.message || '登录失败')
        }
      } catch (error) {
        console.error('登录验证失败:', error)
      }
    }
  },
  watch: {
    isAuthenticated(newVal) {
      if (newVal) {
        this.$router.push('/dashboard')
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #e0f2fe 0%, #dbeafe 50%, #e9d5ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-box {
  background: white;
  border-radius: 10px;
  padding: 40px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  color: #303133;
  margin-bottom: 10px;
  font-size: 24px;
}

.login-header p {
  color: #909399;
  font-size: 14px;
}

.login-form {
  margin-bottom: 20px;
}

.login-button {
  width: 100%;
}

.login-footer {
  text-align: center;
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}

.login-footer p {
  margin: 5px 0;
}
</style>
