<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarWidth" class="sidebar" v-if="$route.meta.requiresAuth">
      <div class="logo">
        <h3>新能源储能调度系统</h3>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="sidebarCollapsed"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/map">
          <el-icon><Location /></el-icon>
          <span>全局态势(大屏)</span>
        </el-menu-item>
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/data">
          <el-icon><DataLine /></el-icon>
          <span>数据管理</span>
        </el-menu-item>
        <el-menu-item index="/predict">
          <el-icon><TrendCharts /></el-icon>
          <span>预测分析</span>
        </el-menu-item>
        <el-menu-item index="/dispatch">
          <el-icon><Setting /></el-icon>
          <span>优化调度</span>
        </el-menu-item>
        <el-menu-item index="/analysis">
          <el-icon><DataAnalysis /></el-icon>
          <span>对比分析</span>
        </el-menu-item>
        <el-menu-item index="/strategy">
          <el-icon><Operation /></el-icon>
          <span>电价与需求响应策略</span>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <span>历史记录</span>
        </el-menu-item>
        <el-menu-item index="/users" v-if="isAdmin">
          <el-icon><User /></el-icon>
          <span> 用户管理</span>
        </el-menu-item>
        <!-- <el-menu-item index="/settings" v-if="isAdmin">
          <el-icon><Tools /></el-icon>
          <span> 系统设置 </span>
        </el-menu-item> -->
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header" v-if="$route.meta.requiresAuth">
        <div class="header-left">
          <el-button
            type="text"
            @click="toggleSidebar"
            class="sidebar-toggle"
          >
            <el-icon><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleUserCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              {{ user?.username }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="changePassword">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主要内容 -->
      <el-main class="main-content" :style="{ padding: $route.path === '/map' ? '0' : '20px' }">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'

export default {
  name: 'App',
  computed: {
    ...mapGetters(['user', 'isAdmin', 'sidebarCollapsed']),
    sidebarWidth() {
      return this.sidebarCollapsed ? '64px' : '200px'
    },
    currentPageTitle() {
      const titles = {
        '/map': '全局态势大屏',
        '/dashboard': '数据仪表盘',
        '/data': '预测元数据管理',
        '/predict': '多维度预测',
        '/dispatch': '协同优化调度',
        '/analysis': '算法机制全景对比实验',
        '/strategy': '电价与策略配置(鸭子曲线)',
        '/history': '历史调度记录',
        '/users': '用户空间',
      }
      return titles[this.$route.path] || '首页'
    }
  },
  methods: {
    ...mapActions(['toggleSidebar', 'logout']),
    handleUserCommand(command) {
      switch (command) {
        case 'profile':
          this.$message.info('个人信息功能待开发')
          break
        case 'changePassword':
          this.showChangePasswordDialog()
          break
        case 'logout':
          this.logout()
          this.$router.push('/login')
          break
      }
    },
    showChangePasswordDialog() {
      this.$prompt('请输入新密码', '修改密码', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputType: 'password'
      }).then(({ value }) => {
        this.changePassword({ new_password: value })
      }).catch(() => {
        this.$message.info('取消修改')
      })
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  transition: width 0.3s;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid #434a50;
}

.logo h3 {
  font-size: 16px;
  margin: 0;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.sidebar-toggle {
  font-size: 18px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #606266;
}

.main-content {
  background-color: #f5f5f5;
  padding: 20px;
}

.el-menu {
  border-right: none;
}
</style>
