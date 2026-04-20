"""
标准 LSTM 模型 — 基准对照模型

本文件实现了一个标准的双层 LSTM 模型，作为基准对照模型：

- **模型结构**：双层 LSTM，无注意力机制
- **用途**：与 Attention-LSTM 形成对比，验证注意力机制对预测精度的提升效果
- **特点**：结构简单，实现经典的 LSTM 时序建模能力

该模型作为基线模型，用于评估其他增强模型（如 Attention-LSTM）的性能提升。
"""

# 导入必要的 PyTorch 模块
import torch  # PyTorch 核心库
import torch.nn as nn  # 神经网络模块
import torch.nn.functional as F  # 函数式接口


class StandardLSTM(nn.Module):
    """
    标准 LSTM 模型
    
    模型架构：
    1. 双层 LSTM 网络：捕获时序依赖关系
    2. 全连接输出层：将 LSTM 输出映射到预测目标
    
    特点：
    - 无注意力机制，作为基准对照模型
    - 结构简单，实现经典的 LSTM 时序建模
    - 用于与 Attention-LSTM 对比，验证注意力机制的效果
    """
    def __init__(self, input_size, hidden_size1=64, hidden_size2=32, output_size=1, dropout=0.2):
        """
        初始化标准 LSTM 模型
        
        Args:
            input_size: int, 输入特征维度
            hidden_size1: int, 第一层 LSTM 的隐藏层维度，默认 64
            hidden_size2: int, 第二层 LSTM 的隐藏层维度，默认 32
            output_size: int, 输出维度，默认 1
            dropout: float, dropout 概率，用于防止过拟合，默认 0.2
        """
        super(StandardLSTM, self).__init__()
        
        # 第一层 LSTM：处理输入序列，提取初级时序特征
        self.lstm1 = nn.LSTM(
            input_size=input_size,  # 输入特征维度
            hidden_size=hidden_size1,  # 隐藏层维度
            batch_first=True,  # 输入格式为 (batch, seq_len, features)
            dropout=dropout  # 防止过拟合
        )
        
        # 第二层 LSTM：进一步提炼时序特征
        self.lstm2 = nn.LSTM(
            input_size=hidden_size1,  # 输入特征维度，对应第一层 LSTM 的输出
            hidden_size=hidden_size2,  # 隐藏层维度
            batch_first=True,
            dropout=dropout
        )
        
        # 全连接层：将 LSTM 输出映射到中间维度
        self.fc = nn.Linear(hidden_size2, 16)  # 中间维度设为 16
        
        # 输出层：将中间维度映射到最终预测目标
        self.out = nn.Linear(16, output_size)
        
        # Dropout 层：防止过拟合
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        """
        前向传播过程
        
        Args:
            x: 输入张量，形状为 (batch, seq_len, input_size)
            - batch: 批次大小
            - seq_len: 序列长度
            - input_size: 输入特征维度
        
        Returns:
            output: 预测输出，形状为 (batch, output_size)
        """
        # 输入形状：(batch, seq_len, input_size)
        
        # 第一层 LSTM 前向传播
        # 输出形状：(batch, seq_len, hidden_size1)
        lstm_out1, _ = self.lstm1(x)
        
        # 第二层 LSTM 前向传播
        # 输出形状：(batch, seq_len, hidden_size2)
        lstm_out2, _ = self.lstm2(lstm_out1)
        
        # 取最后一个时刻的输出作为整个序列的表示
        # 形状：(batch, hidden_size2)
        last_hidden = lstm_out2[:, -1, :]
        
        # 全连接层 + ReLU 激活
        # 形状：(batch, 16)
        fc_out = self.fc(last_hidden)
        fc_out = F.relu(fc_out)
        
        # Dropout 层，防止过拟合
        fc_out = self.dropout(fc_out)
        
        # 输出层，生成最终预测
        # 形状：(batch, output_size)
        output = self.out(fc_out)
        
        return output
