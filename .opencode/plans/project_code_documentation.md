# 新能源储能电池管理与优化调度系统 - 代码文档

## 项目概述

这是一个基于 **Flask + Vue.js** 的新能源储能电池管理与优化调度系统，主要功能包括：
- 电池剩余寿命(SOH)预测
- 实时能量调度优化
- 5阶段分时电价配置
- 系统状态仪表盘展示

### 技术栈
- **后端**: Flask, SQLAlchemy, PyTorch, Scikit-learn, NumPy, Pandas
- **前端**: Vue 3, Vuex, Vue Router, Element Plus, ECharts
- **数据库**: MySQL (生产), SQLite (开发)
- **机器学习**: LSTM, GRU, CNN-LSTM, Transformer, Attention机制
- **优化算法**: 粒子群算法(PSO), 遗传算法(GA), 自适应粒子群算法(AWPSO)

### 项目结构
```
├── backend/                     # Flask 后端
├── frontend/                    # Vue.js 前端
├── energy_db.sql               # MySQL 数据库初始化脚本
├── generate_demo_data.py       # 演示数据生成脚本
├── run_server.py              # 统一启动脚本
└── README.md                  # 项目说明文档
```

---

## 后端代码

### 目录结构
```
backend/
├── app.py                     # Flask 应用主入口
├── start.py                   # 启动脚本
├── config.py                  # 应用配置
├── models/                    # 机器学习模型
├── routes/                    # API路由
├── optimization/              # 优化算法
├── preprocessing/             # 数据预处理
├── data/                      # 数据目录
├── models_saved/              # 训练好的模型文件
└── instance/                  # 实例目录
```

---

### app.py - Flask应用主入口

```python
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from models.database import db
from routes import data_bp, predict_bp, dispatch_bp, auth_bp, analysis_bp
from routes.config import config_bp
from config import Config
import os
import sys
import io

# 强制设置标准输出为 UTF-8 编码，解决 Windows 环境下的乱码问题
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def create_app():
    app = Flask(__name__, 
                 static_folder='../frontend/dist', 
                 static_url_path='/')
    
    # 配置
    app.config.from_object(Config)
    
    # enable CORS with specific configuration
    CORS(app, 
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # 初始化数据库
    db.init_app(app)
    
    # 注册蓝图
    app.register_blueprint(data_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(dispatch_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(analysis_bp)
    
    # 静态文件服务
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(app.static_folder + '/' + path):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'code': 404, 'message': '资源不存在'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'code': 500, 'message': '服务器内部错误'}), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'code': 400, 'message': '请求参数错误'}), 400
    
    return app

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # 创建数据库表
        db.create_all()
        print("数据库表创建完成")
    
    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**注释**：
- 这是Flask应用的入口文件，负责初始化应用、配置CORS、注册蓝图、提供静态文件服务和错误处理。
- `create_app()` 工厂函数创建Flask应用实例，配置数据库和路由蓝图。
- CORS配置允许跨域请求，支持凭证和特定HTTP方法。
- 静态文件服务用于托管前端构建产物，当访问根路径时返回index.html。
- 错误处理函数返回JSON格式的错误响应。

---

### config.py - 应用配置

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:123456@localhost/energy_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 模型配置
    MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models_saved', 'attention_lstm.pth')
    SCALER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'scaler.pkl')
    
    # 储能系统参数
    ESS_CAPACITY = 40.0  # MWh
    ESS_POWER = 20.0     # MW
    ETA_CHARGE = 0.95
    ETA_DISCHARGE = 0.95
    SOC_MIN = 0.1
    SOC_MAX = 0.9
    GRID_MAX = 30.0     # MW
```

**注释**：
- 配置文件定义了应用的核心参数，包括数据库连接、模型路径和储能系统技术参数。
- `SECRET_KEY` 用于会话安全，在生产环境中应从环境变量读取。
- `SQLALCHEMY_DATABASE_URI` 指定数据库连接字符串，默认使用MySQL。
- `MODEL_PATH` 和 `SCALER_PATH` 指向训练好的模型和数据标准化器。
- 储能系统参数包括容量、功率、充放电效率、SOC上下限和电网最大功率。

---

### start.py - 系统启动脚本

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统启动脚本
检查依赖并启动应用
"""

import sys
import os
import io

# 强制设置标准输出为 UTF-8 编码，解决 Windows 环境下的乱码问题
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def check_dependencies():
    """检查必需的依赖"""
    required_modules = {
        'flask': 'Flask',
        'flask_cors': 'flask-cors',
        'flask_sqlalchemy': 'flask-sqlalchemy',
        'pymysql': 'pymysql',
        'jwt': 'PyJWT',
        'werkzeug': 'Werkzeug'
    }
    
    missing = []
    for module, package in required_modules.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    return missing

def install_dependencies(missing):
    """安装缺失的依赖"""
    if not missing:
        return True
    
    print(f"检测到缺失的依赖: {', '.join(missing)}")
    print("正在安装...")
    
    for package in missing:
        print(f"安装 {package}...")
        result = os.system(f'"{sys.executable}" -m pip install "{package}"')
        if result != 0:
            print(f"安装 {package} 失败")
            return False
    
    print("依赖安装完成")
    return True

def main():
    """主函数"""
    print("=== 新能源储能系统启动脚本 ===\n")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("错误: 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 检查并安装依赖
    missing = check_dependencies()
    if missing:
        if not install_dependencies(missing):
            print("\n依赖安装失败，请手动运行:")
            print(f"pip install {' '.join(missing)}")
            sys.exit(1)
    
    # 再次检查
    missing = check_dependencies()
    if missing:
        print(f"仍有依赖缺失: {', '.join(missing)}")
        sys.exit(1)
    
    print("\n✓ 所有依赖检查通过")
    
    # 初始化数据库
    print("\n初始化数据库...")
    try:
        from init_db import init_database
        init_database()
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        print("请检查数据库配置")
        sys.exit(1)
    
    # 启动应用
    print("\n启动应用...")
    try:
        from app import app
        print("应用启动成功!")
        print("访问地址: http://localhost:5000")
        print("按 Ctrl+C 停止应用")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"应用启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n应用已停止")
    except Exception as e:
        print(f"\n启动过程中出现错误: {e}")
        input("按回车键退出...")
```

**注释**：
- 启动脚本负责检查Python版本、安装缺失依赖、初始化数据库并启动Flask应用。
- `check_dependencies()` 函数验证必需Python包是否已安装。
- `install_dependencies()` 自动安装缺失的包。
- `main()` 函数协调整个启动流程，包括数据库初始化和应用启动。
- 脚本提供友好的命令行交互和错误处理。

---

### models/database.py - 数据库模型定义

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'sys_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column('password', db.String(256), nullable=False)
    role = db.Column(db.String(20), default='operator')  # admin/operator/viewer
    email = db.Column(db.String(120), unique=True)
    status = db.Column(db.String(20), default='active')  # active/inactive/locked
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """使用 werkzeug 生成密码哈希"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码是否匹配哈希"""
        # 兼容旧的明文密码：如果 hash 不以 'pbkdf2:' / 'scrypt:' 开头，
        # 说明是旧的明文密码，做一次性迁移
        if not self.password_hash.startswith(('pbkdf2:', 'scrypt:')):
            if self.password_hash == password:
                # 明文匹配，自动迁移为哈希
                self.set_password(password)
                db.session.commit()
                return True
            return False
        return check_password_hash(self.password_hash, password)

class NewEnergyData(db.Model):
    __tablename__ = 'new_energy_data'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, unique=True, nullable=False)
    wind_power = db.Column(db.Float)
    pv_power = db.Column(db.Float)
    load = db.Column(db.Float)
    temperature = db.Column(db.Float)
    irradiance = db.Column(db.Float)
    wind_speed = db.Column(db.Float)

class PredictResult(db.Model):
    __tablename__ = 'predict_result'
    id = db.Column(db.Integer, primary_key=True)
    predict_type = db.Column(db.String(20))  # wind/pv/load
    model_type = db.Column(db.String(30), default='attention_lstm')  # 使用的模型类型
    start_time = db.Column(db.DateTime)
    horizon = db.Column(db.Integer)  # 1 or 24
    data = db.Column(db.JSON)        # 存储预测值列表
    mape = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DispatchResult(db.Model):
    __tablename__ = 'dispatch_result'
    id = db.Column(db.Integer, primary_key=True)
    schedule_date = db.Column(db.Date)
    charge_plan = db.Column(db.JSON)     # 24个时段的充电功率
    discharge_plan = db.Column(db.JSON)  # 放电功率
    soc_curve = db.Column(db.JSON)
    abandon_rate = db.Column(db.Float)
    cost = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StrategyConfig(db.Model):
    __tablename__ = 'sys_strategy'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    extreme_peak_price = db.Column(db.Float, nullable=False)  # 尖峰
    peak_price = db.Column(db.Float, nullable=False)          # 高峰
    flat_price = db.Column(db.Float, nullable=False)          # 平时
    valley_price = db.Column(db.Float, nullable=False)        # 低谷
    deep_valley_price = db.Column(db.Float, nullable=False)   # 深谷
    dr_ratio = db.Column(db.Float, default=0.2)               # 需求响应比例
    tou_config = db.Column(db.JSON, nullable=False)           # 24小时标签映射
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**注释**：
- 数据库模型使用SQLAlchemy ORM定义，包括用户、新能源数据、预测结果、调度结果和策略配置表。
- `User` 类包含身份验证逻辑，支持密码哈希和明文密码迁移。
- `NewEnergyData` 存储风电、光伏、负荷等实时监测数据。
- `PredictResult` 保存不同模型的预测结果和评估指标。
- `DispatchResult` 存储优化调度方案，包括充放电计划和SOC曲线。
- `StrategyConfig` 管理分时电价策略和需求响应配置。

---

