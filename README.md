# 新能源储能电池寿命预测算法平台

OpenCode 初始化与运行
- 项目已包含一个 Windows 友好的初始化与运行脚本集合，方便在本地快速启动开发环境。
- 主要文件：
  - tools/opencode_init.bat — 创建/激活虚拟环境、安装依赖、初始化数据库
  - tools/opencode_run.bat — 启动后端服务（需要已初始化的虚拟环境）
- 使用步骤（Windows）
  1) 使用 OpenCode 进行环境初始化
     - 运行：`tools\opencode_init.bat`
  2) 启动后端服务
     - 运行：`tools\opencode_run.bat`
  3) 前端通常在 https://localhost:8080  需要单独在前端目录执行 `npm install` 与 `npm run serve`。

注：后端的配置（数据库连接等）可通过 backend/.env.example 参考，实际部署请复制为 backend/.env 并填入真实信息，确保配置与本地数据库匹配。

该项目是一个基于深度学习的新能源储能电池管理与优化调度系统。

## 项目结构
- `backend/`: 基于 Flask 的后端 API 接口
- `frontend/`: 基于 Vue.js 的前端展示界面
- `energy_db.sql`: 数据库初始化脚本

## 快速部署指南

### 1. 环境准备
- Python 3.8+
- Node.js 16+
- MySQL 8.0+

### 2. 数据库配置
1. 在 MySQL 中创建一个名为 `energy_storage_db` 的数据库。
2. 导入项目根目录下的 `energy_db.sql` 文件。
3. 修改 `backend/config.py` 中的数据库连接配置（用户名、密码、地址）。

### 3. 后端启动
1. 进入 `backend` 目录。
2. 创建并激活虚拟环境（推荐）：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 启动服务：
   ```bash
   python start.py
   ```
   后端服务将运行在 `http://localhost:5000`。

### 4. 前端启动
1. 进入 `frontend` 目录。
2. 安装依赖：
   ```bash
   npm install
   ```
3. 启动开发服务器：
   ```bash
   npm run serve
   ```
   前端服务将运行在 `http://localhost:8080`。

## 技术栈
- **后端**: Flask, SQLAlchemy, Scikit-learn, PyTorch
- **前端**: Vue.js, Vuex, Vue-router, ECharts
- **数据库**: MySQL

## 主要功能
- 电池剩余寿命 (SOH) 预测
- 实时能量调度优化
- 5阶段分时电价配置
- 系统状态仪表盘展示
