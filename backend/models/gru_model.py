"""
GRU 模型 — 门控循环单元

本文件实现了一个 GRU（门控循环单元）模型，作为 LSTM 的轻量级替代方案：

- **GRU 特点**：比 LSTM 参数更少（无独立的记忆门），训练速度更快
- **适用场景**：作为轻量级替代方案进行对比实验
- **功能**：能够有效捕获时间序列中的长期依赖关系

GRU 模型通过门控机制控制信息的流动，相比 LSTM 结构更简单，但在很多任务上表现相当。
"""

# 导入必要的 PyTorch 模块
import torch  # PyTorch 核心库
import torch.nn as nn  # 神经网络模块
import torch.nn.functional as F  # 函数式接口


class GRUModel(nn.Module):
    """
    GRU 模型（门控循环单元）
    
    模型架构设计：
    1. **双层 GRU 网络**：使用门控循环单元捕获时序依赖
       - 第一层 GRU：处理输入序列，提取初级时序特征
       - 第二层 GRU：进一步提炼时序特征，捕获更高级的依赖关系
    
    2. **全连接输出层**：将 GRU 输出映射到预测目标
       - 全连接层：将 GRU 输出映射到中间维度
       - 输出层：将中间维度映射到最终预测目标
    
    模型特点：
    - 比 LSTM 参数更少（无独立的记忆门），训练速度更快
    - 适合作为轻量级替代方案进行对比实验
    - 能够有效捕获时间序列中的长期依赖关系
    - 结构简洁，易于训练和部署
    """
    def __init__(self, input_size, hidden_size1=64, hidden_size2=32, output_size=1, dropout=0.2):
        """
        初始化 GRU 模型
        
        Args:
            input_size: int, 输入特征维度
            hidden_size1: int, 第一层 GRU 隐藏层维度，默认 64
            hidden_size2: int, 第二层 GRU 隐藏层维度，默认 32
            output_size: int, 输出维度，默认 1
            dropout: float, dropout 概率，用于防止过拟合，默认 0.2
        """
        super(GRUModel, self).__init__()
        
        # 第一层 GRU：处理输入序列，提取初级时序特征
        self.gru1 = nn.GRU(
            input_size=input_size,  # 输入特征维度
            hidden_size=hidden_size1,  # 隐藏层维度
            batch_first=True,  # 输入格式为 (batch, seq_len, features)
            dropout=dropout  # 防止过拟合
        )
        
        # 第二层 GRU：进一步提炼时序特征，捕获更高级的依赖关系
        self.gru2 = nn.GRU(
            input_size=hidden_size1,  # 输入特征维度，对应第一层 GRU 的输出
            hidden_size=hidden_size2,  # 隐藏层维度
            batch_first=True,
            dropout=dropout
        )
        
        # 全连接层：将 GRU 输出映射到中间维度
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
        
        # 1. 第一层 GRU 前向传播
        # 输出形状：(batch, seq_len, hidden_size1)
        gru_out1, _ = self.gru1(x)
        
        # 2. 第二层 GRU 前向传播
        # 输出形状：(batch, seq_len, hidden_size2)
        gru_out2, _ = self.gru2(gru_out1)
        
        # 3. 特征提取
        # 取最后一个时刻的输出作为整个序列的表示
        last_hidden = gru_out2[:, -1, :]  # 形状：(batch, hidden_size2)
        
        # 4. 输出层处理
        # 全连接层 + ReLU 激活
        fc_out = self.fc(last_hidden)  # (batch, 16)
        fc_out = F.relu(fc_out)  # ReLU 激活
        
        # Dropout 层，防止过拟合
        fc_out = self.dropout(fc_out)
        
        # 输出层，生成最终预测
        output = self.out(fc_out)  # (batch, output_size)
        
        return output
