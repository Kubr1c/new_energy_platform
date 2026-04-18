# 新能源储能系统 - 项目启动指南

## 项目概览

**项目名称**: 新能源储能电池寿命预测算法平台

**技术栈**:
- 后端: Flask + SQLAlchemy + PyTorch
- 前端: Vue.js 3 + Vuex + ECharts
- 数据库: MySQL 8.0+
- Python: 3.8+

**主要功能**:
- 电池剩余寿命 (SOH) 预测
- 实时能量调度优化
- 5阶段分时电价配置
- 系统状态仪表盘展示

---

## 快速启动指南

### 1. 环境检查

在启动前，确保以下环境已就绪：

```bash
# 检查 Python 版本（需要 3.8+）
python --version

# 检查 MySQL 服务状态
# Windows: 确保 MySQL 服务正在运行
# 可以通过 services.msc 检查 MySQL80 服务状态
```

### 2. 后端启动

#### 方式一：使用简化启动脚本（推荐）

```bash
# 在项目根目录运行
python run_server.py
```

输出应该包含：
```
==================================================
新能源储能系统启动中...
==================================================

初始化数据库表...
✓ 数据库表创建/检查完成

启动Flask应用服务器...
--------------------------------------------------
后端服务地址: http://localhost:5000
...
 * Running on http://127.0.0.1:5000
```

#### 方式二：使用原始启动脚本

```bash
cd backend
python start.py
```

### 3. 前端启动（可选）

如需前端开发服务器：

```bash
cd frontend
npm install
npm run serve
```

前端将在 `http://localhost:8080` 启动

### 4. 验证服务状态

启动后端后，在另一个终端运行：

```bash
# 运行健康检查脚本
python test_api.py
```

这将测试以下端点：
- GET / (主页)
- GET /data (数据接口)
- GET /config (配置接口)

---

## 数据库配置

### 默认配置

```
Host: localhost
User: root
Password: 123456
Database: energy_db
Port: 3306
```

### 修改数据库配置

编辑 `backend/config.py`:

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://用户:密码@主机/数据库名'
```

或使用环境变量：

```bash
# Windows PowerShell
$env:DATABASE_URL = "mysql+pymysql://root:password@localhost/energy_db"
python run_server.py

# Windows 命令提示符
set DATABASE_URL=mysql+pymysql://root:password@localhost/energy_db
python run_server.py
```

### 初始账户信息

启动时会自动创建以下默认账户（仅第一次）：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| operator | operator123 | 操作员 |
| viewer | viewer123 | 查看者 |

**安全提示**: 生产环境中请立即修改这些密码！

---

## 常见问题排查

### 问题 1: 无法连接到数据库

**错误信息**:
```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server on 'localhost'")
```

**解决方案**:
1. 确保 MySQL 服务已启动
2. 检查数据库用户名和密码是否正确
3. 确保 `energy_db` 数据库已存在
4. 修改 `backend/config.py` 中的数据库连接字符串

### 问题 2: 缺少依赖包

**错误信息**:
```
ModuleNotFoundError: No module named 'flask'
```

**解决方案**:
```bash
pip install -r backend/requirements.txt
```

### 问题 3: 端口被占用

**错误信息**:
```
OSError: [Errno 48] Address already in use
```

**解决方案**:
```bash
# 查看占用 5000 端口的进程
netstat -an | findstr 5000

# 杀死占用端口的进程或修改 run_server.py 中的端口号
```

### 问题 4: 编码问题（Windows）

如果出现中文乱码，确保：
1. Python 文件已保存为 UTF-8 编码
2. 使用 `run_server.py` 而不是 `start.py`（已修复编码问题）

---

## 项目结构

```
new_energy/
├── backend/                    # 后端代码
│   ├── app.py                 # Flask 应用入口
│   ├── config.py              # 配置文件
│   ├── init_db.py             # 数据库初始化脚本
│   ├── start.py               # 启动脚本
│   ├── models/                # 数据模型
│   │   ├── database.py        # 数据库模型定义
│   │   ├── train.py           # 模型训练
│   │   ├── predict.py         # 模型预测
│   │   ├── standard_lstm.py   # LSTM 模型
│   │   ├── gru_model.py       # GRU 模型
│   │   ├── cnn_lstm.py        # CNN-LSTM 模型
│   │   ├── attention_lstm.py  # Attention-LSTM 模型
│   │   └── transformer_model.py # Transformer 模型
│   ├── routes/                # API 路由
│   │   ├── auth.py            # 认证相关
│   │   ├── data.py            # 数据接口
│   │   ├── predict.py         # 预测接口
│   │   ├── dispatch.py        # 调度接口
│   │   ├── analysis.py        # 分析接口
│   │   └── config.py          # 配置接口
│   ├── optimization/          # 优化算法
│   │   ├── pso.py             # 粒子群优化
│   │   ├── ga.py              # 遗传算法
│   │   ├── awpso.py           # 自适应加权 PSO
│   │   ├── solver.py          # 优化求解器
│   │   └── dispatch_model.py  # 调度模型
│   ├── preprocessing/         # 数据预处理
│   │   └── data_utils.py      # 数据工具函数
│   ├── models_saved/          # 保存的模型文件
│   │   └── attention_lstm.pth # 预训练模型
│   ├── data/                  # 数据文件
│   │   ├── raw/               # 原始数据
│   │   └── scaler.pkl         # 数据标准化器
│   └── requirements.txt       # 依赖列表
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── components/        # Vue 组件
│   │   ├── views/             # 页面视图
│   │   ├── router/            # 路由配置
│   │   ├── store/             # Vuex 状态管理
│   │   └── App.vue            # 根组件
│   ├── package.json           # 前端依赖
│   └── README.md              # 前端说明
│
├── energy_db.sql              # 数据库初始化脚本
├── run_server.py              # 简化启动脚本（推荐）
├── test_api.py                # API 健康检查脚本
├── README.md                  # 项目说明
└── PROJECT_STARTUP_GUIDE.md   # 本文件

```

---

## API 端点概览

### 认证相关
- `POST /auth/login` - 用户登录
- `POST /auth/logout` - 用户登出
- `POST /auth/register` - 用户注册

### 数据相关
- `GET /data` - 获取数据列表
- `POST /data` - 上传数据
- `GET /data/<id>` - 获取特定数据

### 预测相关
- `POST /predict` - 执行预测
- `GET /predict/<id>` - 获取预测结果

### 调度相关
- `POST /dispatch` - 执行能量调度
- `GET /dispatch/<id>` - 获取调度结果

### 分析相关
- `GET /analysis` - 获取分析数据
- `POST /analysis` - 执行分析

### 配置相关
- `GET /config` - 获取系统配置
- `PUT /config` - 更新系统配置

---

## 开发工作流

### 后端开发

1. 修改代码后，Flask 会自动重载（debug=True）
2. 查看控制台输出找到问题
3. 修复后刷新页面或重新运行 API 请求

### 前端开发

1. 修改 Vue 组件后，dev server 会热更新
2. 浏览器会自动刷新
3. 使用浏览器开发者工具调试

### 数据库模型修改

如果修改了数据库模型：
1. 运行 `python backend/init_db.py` 重新初始化（会删除所有数据）
2. 或使用 `python backend/init_db.py reset` 重置数据库

---

## 部署指南

### 生产环境准备

1. **关闭 Debug 模式**
   ```python
   app.run(debug=False)
   ```

2. **使用生产 WSGI 服务器**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
   ```

3. **配置安全密钥**
   ```bash
   set SECRET_KEY=your-very-secure-random-key
   ```

4. **配置数据库**
   ```bash
   set DATABASE_URL=mysql+pymysql://prod_user:prod_password@prod_host/prod_db
   ```

5. **配置 CORS**
   修改 `backend/app.py` 中的 CORS 配置，限制允许的源

6. **使用 Nginx 反向代理**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
       }
   }
   ```

---

## 获取帮助

### 查看日志

启动脚本会输出详细的日志信息，帮助诊断问题。

### 调试模式

在 `run_server.py` 中已启用 Flask Debug 模式，可以在控制台看到详细的错误追踪。

### 数据库调试

```bash
# 连接到数据库
mysql -h localhost -u root -p energy_db

# 查看表
SHOW TABLES;

# 查看用户表
SELECT * FROM user;
```

---

## 许可证和贡献

本项目为毕业设计项目。

---

**最后更新**: 2026年4月18日
**维护者**: OpenCode
