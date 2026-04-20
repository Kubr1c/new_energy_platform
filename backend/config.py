import os


class Config:
    """应用配置类
    
    包含应用所需的各种配置项，包括：
    1. 安全配置
    2. 数据库配置
    3. 模型配置
    4. 储能系统参数
    """
    # 安全配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    """Flask 应用密钥
    
    用于会话管理、CSRF 保护等安全功能。
    生产环境中应通过环境变量设置，避免硬编码。
    """
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:123456@localhost/energy_db'
    """数据库连接 URI
    
    格式：mysql+pymysql://用户名:密码@主机/数据库名
    生产环境中应通过环境变量设置，避免硬编码敏感信息。
    """
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    """是否跟踪数据库修改
    
    设置为 False 以提高性能，避免不必要的开销。
    """
    
    # 模型配置
    MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models_saved', 'attention_lstm.pth')
    """预测模型文件路径
    
    存储训练好的注意力 LSTM 模型文件的路径。
    """
    
    SCALER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'scaler.pkl')
    """数据标准化器文件路径
    
    存储用于数据标准化的 scaler 对象的路径。
    """
    
    # 储能系统参数
    ESS_CAPACITY = 40.0  # MWh
    """储能系统容量
    
    单位：兆瓦时 (MWh)
    """
    
    ESS_POWER = 20.0     # MW
    """储能系统功率
    
    单位：兆瓦 (MW)
    """
    
    ETA_CHARGE = 0.95
    """充电效率
    
    储能系统充电时的能量转换效率。
    """
    
    ETA_DISCHARGE = 0.95
    """放电效率
    
    储能系统放电时的能量转换效率。
    """
    
    SOC_MIN = 0.1
    """最小荷电状态
    
    储能系统允许的最小荷电状态（0-1 之间）。
    """
    
    SOC_MAX = 0.9
    """最大荷电状态
    
    储能系统允许的最大荷电状态（0-1 之间）。
    """
    
    GRID_MAX = 30.0     # MW
    """电网最大输入/输出功率
    
    单位：兆瓦 (MW)
    """

