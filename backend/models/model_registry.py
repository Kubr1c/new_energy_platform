"""
模型注册表 — 统一管理所有可用的深度学习预测模型。
提供工厂函数 get_model() 按名称自动实例化模型，
以及 list_available_models() 列出所有可选模型供前端渲染。
"""
from .attention_lstm import AttentionLSTM
from .standard_lstm import StandardLSTM
from .gru_model import GRUModel
from .cnn_lstm import CNNLSTM
from .transformer_model import TimeSeriesTransformer


# 模型注册表：model_type → (ModelClass, description_cn, description_en)
MODEL_REGISTRY = {
    'attention_lstm': {
        'class': AttentionLSTM,
        'name': 'Attention-LSTM',
        'description': '双层LSTM + 注意力机制，通过注意力权重自动聚焦关键时段',
        'params': '~25K',
        'icon': 'Star',
    },
    'standard_lstm': {
        'class': StandardLSTM,
        'name': '标准 LSTM',
        'description': '双层LSTM基准模型，无注意力机制，用于对比验证注意力效果',
        'params': '~20K',
        'icon': 'Histogram',
    },
    'gru': {
        'class': GRUModel,
        'name': 'GRU',
        'description': '门控循环单元，比LSTM参数更少、训练更快的轻量替代方案',
        'params': '~15K',
        'icon': 'Timer',
    },
    'cnn_lstm': {
        'class': CNNLSTM,
        'name': 'CNN-LSTM',
        'description': '一维卷积提取局部特征 + LSTM捕获时序依赖的混合架构',
        'params': '~30K',
        'icon': 'Connection',
    },
    'transformer': {
        'class': TimeSeriesTransformer,
        'name': 'Transformer',
        'description': '纯注意力架构，多头自注意力机制并行建模，学术前沿方案',
        'params': '~35K',
        'icon': 'MagicStick',
    },
}


def get_model(model_type, input_size, output_size, **kwargs):
    """
    工厂函数：根据 model_type 实例化对应的神经网络模型。

    Args:
        model_type: 模型类型键值（如 'attention_lstm', 'gru', 'transformer'）
        input_size: 输入特征维度
        output_size: 输出维度
        **kwargs: 传递给模型构造函数的额外参数

    Returns:
        nn.Module 实例

    Raises:
        ValueError: 如果 model_type 不在注册表中
    """
    if model_type not in MODEL_REGISTRY:
        available = ', '.join(MODEL_REGISTRY.keys())
        raise ValueError(f"未知的模型类型: '{model_type}'。可选: {available}")

    model_cls = MODEL_REGISTRY[model_type]['class']
    return model_cls(input_size, output_size=output_size, **kwargs)


def list_available_models():
    """
    返回所有可用模型的描述信息列表，供前端下拉框使用。

    Returns:
        list[dict]: 每个元素包含 model_type, name, description, params, icon
    """
    models = []
    for model_type, info in MODEL_REGISTRY.items():
        models.append({
            'model_type': model_type,
            'name': info['name'],
            'description': info['description'],
            'params': info['params'],
            'icon': info['icon'],
        })
    return models
