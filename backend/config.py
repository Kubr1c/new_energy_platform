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
