"""
models 模块初始化文件

该文件定义了 models 包的公共接口，控制模块的导入和导出。

当前只导出了数据库连接对象 db，其他模型和功能已被注释掉，
可根据需要取消注释以启用相应功能。
"""

# 导入数据库连接对象
from .database import db

# 以下导入已被注释，可根据需要取消注释以启用相应功能
# from .attention_lstm import AttentionLSTM, BahdanauAttention  # 注意力机制增强的 LSTM 模型
# from .standard_lstm import StandardLSTM  # 标准 LSTM 模型（基准对照）
# from .gru_model import GRUModel  # GRU 模型（轻量级替代方案）
# from .cnn_lstm import CNNLSTM  # CNN-LSTM 混合模型
# from .transformer_model import TimeSeriesTransformer  # Transformer 时序预测模型
# from .model_registry import get_model, list_available_models, MODEL_REGISTRY  # 模型注册和管理
# from .train import train_model  # 模型训练函数
# from .predict import Predictor  # 预测器类

# 定义模块的公共接口，控制 from models import * 时导入的内容
__all__ = [
    'db',  # 数据库连接对象
    # 'AttentionLSTM', 'BahdanauAttention',  # 注意力机制相关类
    # 'StandardLSTM', 'GRUModel', 'CNNLSTM', 'TimeSeriesTransformer',  # 各种模型类
    # 'get_model', 'list_available_models', 'MODEL_REGISTRY',  # 模型注册和管理功能
    # 'train_model', 'Predictor',  # 训练和预测功能
]
