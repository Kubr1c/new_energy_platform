"""
数据库模型定义

本文件定义了 Flask SQLAlchemy 数据库实例和多个数据库模型，
用于存储用户信息、新能源数据、预测结果、调度结果、策略配置和储能站点等数据。
"""

# 导入必要的模块
from flask_sqlalchemy import SQLAlchemy  # Flask SQLAlchemy 扩展
from datetime import datetime  # 日期时间模块
from werkzeug.security import generate_password_hash, check_password_hash  # 密码哈希处理

# 创建数据库实例
db = SQLAlchemy()


class User(db.Model):
    """
    用户模型
    
    存储系统用户信息，包括用户名、密码哈希、角色、邮箱等。
    """
    __tablename__ = 'sys_user'  # 数据库表名
    
    id = db.Column(db.Integer, primary_key=True)  # 主键
    username = db.Column(db.String(64), unique=True, nullable=False)  # 用户名，唯一
    password_hash = db.Column('password', db.String(512), nullable=False)  # 密码哈希，映射到数据库的 password 字段
    role = db.Column(db.String(20), default='operator')  # 角色：admin/operator/viewer
    email = db.Column(db.String(120), unique=True)  # 邮箱，唯一
    status = db.Column(db.String(20), default='active')  # 状态：active/inactive/locked
    last_login = db.Column(db.DateTime)  # 最后登录时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间

    def set_password(self, password):
        """
        设置密码，使用 werkzeug 生成密码哈希
        
        Args:
            password: str, 明文密码
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        验证密码是否匹配哈希
        
        兼容旧的明文密码：如果 hash 不以 'pbkdf2:' / 'scrypt:' 开头，
        说明是旧的明文密码，做一次性迁移。
        
        Args:
            password: str, 待验证的明文密码
        
        Returns:
            bool, 密码是否匹配
        """
        # 检查是否为旧的明文密码
        if not self.password_hash.startswith(('pbkdf2:', 'scrypt:')):
            if self.password_hash == password:
                # 明文匹配，自动迁移为哈希
                self.set_password(password)
                db.session.commit()
                return True
            return False
        # 验证哈希密码
        return check_password_hash(self.password_hash, password)


class NewEnergyData(db.Model):
    """
    新能源数据模型
    
    存储新能源相关的时间序列数据，包括风力发电、光伏发电、负荷、温度、辐照度和风速等。
    """
    __tablename__ = 'new_energy_data'  # 数据库表名
    
    id = db.Column(db.Integer, primary_key=True)  # 主键
    timestamp = db.Column(db.DateTime, unique=True, nullable=False)  # 时间戳，唯一
    wind_power = db.Column(db.Float)  # 风力发电量
    pv_power = db.Column(db.Float)  # 光伏发电量
    load = db.Column(db.Float)  # 负荷
    temperature = db.Column(db.Float)  # 温度
    irradiance = db.Column(db.Float)  # 辐照度
    wind_speed = db.Column(db.Float)  # 风速


class PredictResult(db.Model):
    """
    预测结果模型
    
    存储模型预测结果，包括预测类型、使用的模型、预测时间范围、预测数据和精度指标等。
    """
    __tablename__ = 'predict_result'  # 数据库表名
    
    id = db.Column(db.Integer, primary_key=True)  # 主键
    predict_type = db.Column(db.String(20))  # 预测类型：wind/pv/load
    model_type = db.Column(db.String(30), default='attention_lstm')  # 使用的模型类型
    start_time = db.Column(db.DateTime)  # 预测开始时间
    horizon = db.Column(db.Integer)  # 预测 horizon：1 or 24
    data = db.Column(db.JSON)  # 存储预测值列表
    mape = db.Column(db.Float)  # 平均绝对百分比误差
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间


class DispatchResult(db.Model):
    """
    调度结果模型
    
    存储储能系统的调度结果，包括充电计划、放电计划、SOC曲线、弃风弃光率和成本等。
    """
    __tablename__ = 'dispatch_result'  # 数据库表名
    
    id = db.Column(db.Integer, primary_key=True)  # 主键
    schedule_date = db.Column(db.Date)  # 调度日期
    charge_plan = db.Column(db.JSON)  # 24个时段的充电功率
    discharge_plan = db.Column(db.JSON)  # 24个时段的放电功率
    soc_curve = db.Column(db.JSON)  # 24个时段的SOC曲线
    abandon_rate = db.Column(db.Float)  # 弃风弃光率
    cost = db.Column(db.Float)  # 成本
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间


class StrategyConfig(db.Model):
    """
    策略配置模型
    
    存储电价策略配置，包括不同时段的电价、需求响应比例和分时电价配置等。
    """
    __tablename__ = 'sys_strategy'  # 数据库表名
    
    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(64), nullable=False)  # 策略名称
    extreme_peak_price = db.Column(db.Float, nullable=False)  # 尖峰电价
    peak_price = db.Column(db.Float, nullable=False)  # 高峰电价
    flat_price = db.Column(db.Float, nullable=False)  # 平时电价
    valley_price = db.Column(db.Float, nullable=False)  # 低谷电价
    deep_valley_price = db.Column(db.Float, nullable=False)  # 深谷电价
    dr_ratio = db.Column(db.Float, default=0.2)  # 需求响应比例
    tou_config = db.Column(db.JSON, nullable=False)  # 24小时标签映射
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间


class EnergyStorageSite(db.Model):
    """
    储能电站站点模型
    
    存储储能电站的基本信息、地理位置、技术参数和运营状态等。
    """
    __tablename__ = 'energy_storage_site'  # 数据库表名
    
    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(128), nullable=False)  # 站点名称
    adcode = db.Column(db.String(6), nullable=False)  # 所属地区adcode
    level = db.Column(db.String(20), default='province')  # 行政级别：nation/province/city
    
    # 地理位置
    longitude = db.Column(db.Float, nullable=False)  # 经度
    latitude = db.Column(db.Float, nullable=False)  # 纬度
    address = db.Column(db.String(256))  # 详细地址
    
    # 站点属性
    capacity_mwh = db.Column(db.Float, nullable=False)  # 额定容量 (MWh)
    power_mw = db.Column(db.Float, nullable=False)  # 最高功率 (MW)
    soh_percent = db.Column(db.Float, default=100.0)  # 健康度 (%)
    status = db.Column(db.String(20), default='active')  # 状态：active/inactive/maintenance
    
    # 运营数据
    current_soc = db.Column(db.Float, default=50.0)  # 当前SOC (%)
    charge_power = db.Column(db.Float, default=0.0)  # 当前充电功率 (MW)
    discharge_power = db.Column(db.Float, default=0.0)  # 当前放电功率 (MW)
    
    # 管理信息
    owner = db.Column(db.String(128))  # 业主单位
    operator = db.Column(db.String(128))  # 运营单位
    created_by = db.Column(db.Integer, db.ForeignKey('sys_user.id'))  # 创建人，外键关联 sys_user 表
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    
    # 索引
    __table_args__ = (
        db.Index('idx_adcode_level', 'adcode', 'level'),  # 地区和级别索引
        db.Index('idx_location', 'longitude', 'latitude'),  # 地理位置索引
        db.Index('idx_status', 'status'),  # 状态索引
    )
