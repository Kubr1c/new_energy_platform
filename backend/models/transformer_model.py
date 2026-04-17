"""
Transformer 时序预测模型
基于 Positional Encoding + TransformerEncoder 的纯注意力架构。
与 RNN 系列（LSTM/GRU）有本质区别：
  - 无循环结构，完全基于自注意力机制（Self-Attention）
  - 支持并行计算，理论训练速度更快
  - 通过多头注意力同时关注不同时刻的特征交互
"""
import torch
import torch.nn as nn
import math


class PositionalEncoding(nn.Module):
    """正弦-余弦位置编码，为 Transformer 提供序列位置信息"""

    def __init__(self, d_model, max_len=500, dropout=0.1):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        # 构建位置编码矩阵
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        if d_model % 2 == 0:
            pe[:, 1::2] = torch.cos(position * div_term)
        else:
            pe[:, 1::2] = torch.cos(position * div_term[:-1]) if div_term[:-1].shape[0] > 0 else torch.cos(position * div_term)

        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer('pe', pe)

    def forward(self, x):
        # x: (batch, seq_len, d_model)
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class TimeSeriesTransformer(nn.Module):
    def __init__(self, input_size, hidden_size1=64, hidden_size2=32, output_size=1, dropout=0.2):
        super(TimeSeriesTransformer, self).__init__()

        d_model = hidden_size1  # Transformer 内部维度

        # --- 输入投影层 ---
        # 将原始特征维度映射到 d_model 维
        self.input_projection = nn.Linear(input_size, d_model)

        # --- 位置编码 ---
        self.positional_encoding = PositionalEncoding(d_model, dropout=dropout)

        # --- Transformer Encoder ---
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=4,           # 4 头注意力
            dim_feedforward=128,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=2)

        # --- 全连接输出层 ---
        self.fc = nn.Linear(d_model, hidden_size2)
        self.out = nn.Linear(hidden_size2, output_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x: (batch, seq_len, input_size)

        # 投影到 d_model 维度
        x = self.input_projection(x)           # (batch, seq_len, d_model)

        # 添加位置编码
        x = self.positional_encoding(x)         # (batch, seq_len, d_model)

        # Transformer Encoder
        x = self.transformer_encoder(x)         # (batch, seq_len, d_model)

        # 取最后一个时刻的表示（类似 LSTM 取 last hidden）
        last_output = x[:, -1, :]               # (batch, d_model)

        fc_out = torch.relu(self.fc(last_output))
        fc_out = self.dropout(fc_out)
        output = self.out(fc_out)
        return output
