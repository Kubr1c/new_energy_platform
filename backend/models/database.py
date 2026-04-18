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
