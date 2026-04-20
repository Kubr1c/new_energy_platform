"""
模型注册表模块

本模块统一管理所有可用的深度学习预测模型，提供以下功能：

- **模型注册**：维护一个包含所有可用模型的注册表
- **模型实例化**：通过工厂函数按名称自动创建模型实例
- **模型信息查询**：提供所有模型的详细信息，供前端界面使用

该模块采用工厂模式设计，使得模型的添加和管理更加灵活和可扩展。
"""

# 尝试导入torch和模型类，如果失败则只提供模型信息
TORCH_AVAILABLE = False
try:
    import torch
    from .attention_lstm import AttentionLSTM  # 注意力机制增强的 LSTM 模型
    from .standard_lstm import StandardLSTM  # 标准 LSTM 模型（基准对照）
    from .gru_model import GRUModel  # GRU 模型（轻量级替代方案）
    from .cnn_lstm import CNNLSTM  # CNN-LSTM 混合模型
    from .transformer_model import TimeSeriesTransformer  # Transformer 时序预测模型
    from .tft_model import get_tft_model  # Temporal Fusion Transformer 模型
    TORCH_AVAILABLE = True
except ImportError:
    print("Warning: torch not available, only providing model information")


# 模型注册表：model_type → 模型信息
# 每个模型信息包含：类、名称、描述、参数量、图标
MODEL_REGISTRY = {
    'attention_lstm': {
        'class': AttentionLSTM if TORCH_AVAILABLE else None,  # 模型类
        'name': 'Attention-LSTM',  # 模型名称
        'description': '双层LSTM + 注意力机制，通过注意力权重自动聚焦关键时段',  # 模型描述
        'params': '~25K',  # 参数量
        'icon': 'Star',  # 图标
    },
    'standard_lstm': {
        'class': StandardLSTM if TORCH_AVAILABLE else None,  # 模型类
        'name': '标准 LSTM',  # 模型名称
        'description': '双层LSTM基准模型，无注意力机制，用于对比验证注意力效果',  # 模型描述
        'params': '~20K',  # 参数量
        'icon': 'Histogram',  # 图标
    },
    'gru': {
        'class': GRUModel if TORCH_AVAILABLE else None,  # 模型类
        'name': 'GRU',  # 模型名称
        'description': '门控循环单元，比LSTM参数更少、训练更快的轻量替代方案',  # 模型描述
        'params': '~15K',  # 参数量
        'icon': 'Timer',  # 图标
    },
    'cnn_lstm': {
        'class': CNNLSTM if TORCH_AVAILABLE else None,  # 模型类
        'name': 'CNN-LSTM',  # 模型名称
        'description': '一维卷积提取局部特征 + LSTM捕获时序依赖的混合架构',  # 模型描述
        'params': '~30K',  # 参数量
        'icon': 'Connection',  # 图标
    },
    'transformer': {
        'class': TimeSeriesTransformer if TORCH_AVAILABLE else None,  # 模型类
        'name': 'Transformer',  # 模型名称
        'description': '纯注意力架构，多头自注意力机制并行建模，学术前沿方案',  # 模型描述
        'params': '~35K',  # 参数量
        'icon': 'MagicStick',  # 图标
    },
    'tft': {
        'class': get_tft_model if TORCH_AVAILABLE else None,  # 模型类
        'name': 'Temporal Fusion Transformer',  # 模型名称
        'description': '先进的时序预测模型，结合Transformer注意力和门控机制，处理静态和时间特征',  # 模型描述
        'params': '~45K',  # 参数量
        'icon': 'Lightbulb',  # 图标
    },
}


def get_model(model_type, input_size, output_size, **kwargs):
    """
    工厂函数：根据模型类型实例化对应的神经网络模型
    
    Args:
        model_type: str, 模型类型键值（如 'attention_lstm', 'gru', 'transformer'）
        input_size: int, 输入特征维度
        output_size: int, 输出维度
        **kwargs: dict, 传递给模型构造函数的额外参数
    
    Returns:
        nn.Module, 实例化的模型对象
    
    Raises:
        ValueError, 如果 model_type 不在注册表中
        ImportError, 如果 torch 不可用
    """
    # 检查模型类型是否在注册表中
    if model_type not in MODEL_REGISTRY:
        available = ', '.join(MODEL_REGISTRY.keys())
        raise ValueError(f"未知的模型类型: '{model_type}'。可选: {available}")

    # 检查torch是否可用
    if not TORCH_AVAILABLE:
        raise ImportError("torch not available, cannot instantiate model")

    # 获取模型类并实例化
    model_cls = MODEL_REGISTRY[model_type]['class']
    if model_cls is None:
        raise ImportError(f"Model class for {model_type} not available")
    
    # 特殊处理TFT模型
    if model_type == 'tft':
        return model_cls(input_size, output_size)
    else:
        return model_cls(input_size, output_size=output_size, **kwargs)


def list_available_models():
    """
    返回所有可用模型的描述信息列表
    
    该函数返回的信息可直接用于前端下拉框等界面元素，
    包含每个模型的类型、名称、描述、参数量和图标信息。
    
    Returns:
        list[dict], 每个元素包含 model_type, name, description, params, icon
    """
    models = []
    # 遍历注册表，构建模型信息列表
    for model_type, info in MODEL_REGISTRY.items():
        models.append({
            'model_type': model_type,  # 模型类型键值
            'name': info['name'],  # 模型名称
            'description': info['description'],  # 模型描述
            'params': info['params'],  # 参数量
            'icon': info['icon'],  # 图标
        })
    return models
