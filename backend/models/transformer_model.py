"""
Transformer 时序预测模型

本文件实现了一个基于 Transformer 的时序预测模型，采用纯注意力架构：

- **核心组件**：Positional Encoding + TransformerEncoder
- **与 RNN 系列的区别**：
  - 无循环结构，完全基于自注意力机制（Self-Attention）
  - 支持并行计算，理论训练速度更快
  - 通过多头注意力同时关注不同时刻的特征交互

模型适用于需要捕捉长序列依赖关系的时间序列预测任务，
如新能源发电量预测、金融时间序列预测等。
"""

# 导入必要的模块
import torch  # PyTorch 核心库
import torch.nn as nn  # 神经网络模块
import math  # 数学运算库


class PositionalEncoding(nn.Module):
    """
    正弦-余弦位置编码
    
    为 Transformer 模型提供序列位置信息，因为 Transformer 本身不包含循环结构，
    无法像 RNN 那样自然地捕获序列顺序。
    
    位置编码公式：
    - PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
    - PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    
    其中 pos 是位置索引，i 是维度索引，d_model 是模型维度。
    """

    def __init__(self, d_model, max_len=500, dropout=0.1):
        """
        初始化位置编码模块
        
        Args:
            d_model: int, 模型维度
            max_len: int, 最大序列长度，默认 500
            dropout: float, dropout 概率，默认 0.1
        """
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        # 构建位置编码矩阵
        pe = torch.zeros(max_len, d_model)  # 形状：(max_len, d_model)
        
        # 生成位置索引：[0, 1, 2, ..., max_len-1]
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)  # 形状：(max_len, 1)
        
        # 计算分母项：10000^(2i/d_model)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))  # 形状：(d_model/2,)

        # 偶数位置使用正弦函数
        pe[:, 0::2] = torch.sin(position * div_term)
        
        # 奇数位置使用余弦函数
        if d_model % 2 == 0:
            pe[:, 1::2] = torch.cos(position * div_term)
        else:
            # 处理 d_model 为奇数的情况
            pe[:, 1::2] = torch.cos(position * div_term[:-1]) if div_term[:-1].shape[0] > 0 else torch.cos(position * div_term)

        # 扩展维度，添加批次维度：(1, max_len, d_model)
        pe = pe.unsqueeze(0)
        
        # 注册为缓冲区，不参与梯度计算
        self.register_buffer('pe', pe)

    def forward(self, x):
        """
        前向传播过程
        
        Args:
            x: 输入张量，形状为 (batch, seq_len, d_model)
        
        Returns:
            添加位置编码后的张量，形状为 (batch, seq_len, d_model)
        """
        # 添加位置编码
        x = x + self.pe[:, :x.size(1), :]  # 只取与输入序列长度匹配的部分
        
        # 应用 dropout
        return self.dropout(x)


class TimeSeriesTransformer(nn.Module):
    """
    基于 Transformer 的时间序列预测模型
    
    模型架构：
    1. 输入投影层：将原始特征维度映射到 Transformer 内部维度
    2. 位置编码层：为序列添加位置信息
    3. Transformer Encoder：通过多头自注意力捕获序列依赖关系
    4. 全连接输出层：将 Transformer 输出映射到预测目标
    """
    def __init__(self, input_size, hidden_size1=64, hidden_size2=32, output_size=1, dropout=0.2):
        """
        初始化 Transformer 时序预测模型
        
        Args:
            input_size: int, 输入特征维度
            hidden_size1: int, Transformer 内部维度，默认 64
            hidden_size2: int, 全连接层隐藏维度，默认 32
            output_size: int, 输出维度，默认 1
            dropout: float, dropout 概率，默认 0.2
        """
        super(TimeSeriesTransformer, self).__init__()

        d_model = hidden_size1  # Transformer 内部维度

        # --- 输入投影层 ---
        # 将原始特征维度映射到 d_model 维
        self.input_projection = nn.Linear(input_size, d_model)

        # --- 位置编码 ---
        self.positional_encoding = PositionalEncoding(d_model, dropout=dropout)

        # --- Transformer Encoder ---
        # 定义单个 Transformer 编码器层
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,           # 模型维度
            nhead=4,                  # 4 头注意力
            dim_feedforward=128,       # 前馈网络隐藏层维度
            dropout=dropout,           # Dropout 概率
            batch_first=True           # 输入格式为 (batch, seq_len, features)
        )
        # 堆叠多个编码器层
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=2)  # 2 层编码器

        # --- 全连接输出层 ---
        self.fc = nn.Linear(d_model, hidden_size2)  # 中间隐藏层
        self.out = nn.Linear(hidden_size2, output_size)  # 输出层
        self.dropout = nn.Dropout(dropout)  # Dropout 层

    def forward(self, x):
        """
        前向传播过程
        
        Args:
            x: 输入张量，形状为 (batch, seq_len, input_size)
        
        Returns:
            预测输出，形状为 (batch, output_size)
        """
        # 输入形状：(batch, seq_len, input_size)

        # 1. 投影到 d_model 维度
        x = self.input_projection(x)  # 形状：(batch, seq_len, d_model)

        # 2. 添加位置编码
        x = self.positional_encoding(x)  # 形状：(batch, seq_len, d_model)

        # 3. Transformer Encoder 处理
        x = self.transformer_encoder(x)  # 形状：(batch, seq_len, d_model)

        # 4. 取最后一个时刻的表示（类似 LSTM 取 last hidden）
        last_output = x[:, -1, :]  # 形状：(batch, d_model)

        # 5. 全连接层处理
        fc_out = torch.relu(self.fc(last_output))  # 形状：(batch, hidden_size2)
        fc_out = self.dropout(fc_out)  # 防止过拟合
        
        # 6. 输出层
        output = self.out(fc_out)  # 形状：(batch, output_size)
        
        return output
