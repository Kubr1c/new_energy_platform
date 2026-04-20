"""
CNN-LSTM 混合模型

本文件实现了一个 CNN-LSTM 混合模型，结合了卷积神经网络（CNN）和长短期记忆网络（LSTM）的优势：

- **CNN 部分**：使用一维卷积（Conv1D）提取局部时间窗口内的特征模式，
  擅长捕捉短时间尺度的特征，如功率突变、日内波动形状等局部模式。

- **LSTM 部分**：负责捕获长时间序列的依赖关系，
  擅长建模长期趋势、周期性规律等全局特征。

模型适用于需要同时考虑局部模式和全局趋势的时间序列预测任务，
如新能源发电量预测、电力负荷预测等场景。
"""

# 导入必要的 PyTorch 模块
import torch  # PyTorch 核心库
import torch.nn as nn  # 神经网络模块
import torch.nn.functional as F  # 函数式接口


class CNNLSTM(nn.Module):
    """
    增强版 CNN-LSTM 混合模型
    
    模型架构设计：
    1. **CNN 特征提取层**：使用一维卷积网络提取局部时间窗口内的特征模式
       - 四层 Conv1D 网络，逐步提取局部特征
       - 批归一化层加速训练收敛，提高模型稳定性
       - 跳跃连接，保留低层特征
    
    2. **LSTM 时序建模层**：捕获长时间序列的依赖关系
       - 双层 LSTM 处理 CNN 提取的特征序列
       - 建模跨时间步的依赖关系
    
    3. **全连接输出层**：将特征映射到预测目标
       - 多层全连接层将 LSTM 输出映射到中间维度
       - 输出层生成最终预测结果
    
    增强特性：
      - 增加卷积层数和通道数，提高特征提取能力
      - 使用更大的卷积核捕获更宽的时间窗口特征
      - 引入跳跃连接，保留低层特征
      - 增加 LSTM 层数，提高时序建模能力
      - 增加输出层深度，增强模型非线性拟合能力
    """
    def __init__(self, input_size, hidden_size1=128, hidden_size2=64, output_size=1, dropout=0.3):
        """
        初始化 CNN-LSTM 模型
        
        Args:
            input_size: int, 输入特征维度
            hidden_size1: int, LSTM 隐藏层维度，默认 128
            hidden_size2: int, 全连接层隐藏维度，默认 64
            output_size: int, 输出维度，默认 1
            dropout: float, dropout 概率，用于防止过拟合，默认 0.3
        """
        super(CNNLSTM, self).__init__()

        # --- CNN 特征提取层 ---
        # Conv1D 期望的输入形状为 (batch, channels, seq_len)，其中 channels = input_size
        # 第一层卷积：从输入特征维度映射到 64 通道，使用 5x5 卷积核
        self.conv1 = nn.Conv1d(
            in_channels=input_size,  # 输入通道数等于特征维度
            out_channels=64,  # 输出通道数
            kernel_size=5,  # 卷积核大小，捕捉 5 个时间步的局部特征
            padding=2  # 填充，保持序列长度不变
        )
        
        # 第二层卷积：进一步提取特征
        self.conv2 = nn.Conv1d(
            in_channels=64,  # 输入通道数
            out_channels=128,  # 输出通道数
            kernel_size=3,  # 卷积核大小
            padding=1  # 填充
        )
        
        # 第三层卷积：更深层特征提取
        self.conv3 = nn.Conv1d(
            in_channels=128,  # 输入通道数
            out_channels=256,  # 输出通道数
            kernel_size=3,  # 卷积核大小
            padding=1  # 填充
        )
        
        # 第四层卷积：最终特征提取
        self.conv4 = nn.Conv1d(
            in_channels=256,  # 输入通道数
            out_channels=128,  # 输出通道数
            kernel_size=3,  # 卷积核大小
            padding=1  # 填充
        )
        
        # 批归一化层：加速训练收敛，提高模型稳定性
        self.batch_norm1 = nn.BatchNorm1d(64)  # 对应第一层卷积的输出通道数
        self.batch_norm2 = nn.BatchNorm1d(128)  # 对应第二层卷积的输出通道数
        self.batch_norm3 = nn.BatchNorm1d(256)  # 对应第三层卷积的输出通道数
        self.batch_norm4 = nn.BatchNorm1d(128)  # 对应第四层卷积的输出通道数

        # --- LSTM 时序建模层 ---
        # 第一层 LSTM：处理时序数据
        self.lstm1 = nn.LSTM(
            input_size=128,  # 输入特征维度，对应 CNN 输出的通道数
            hidden_size=hidden_size1,  # 隐藏层维度
            num_layers=2,  # 两层 LSTM
            batch_first=True,  # 输入格式为 (batch, seq_len, features)
            dropout=dropout  # 防止过拟合
        )

        # --- 全连接输出层 ---
        # 全连接层：将 LSTM 输出映射到中间维度
        self.fc1 = nn.Linear(hidden_size1, hidden_size2)
        self.fc2 = nn.Linear(hidden_size2, 32)
        # 输出层：将中间维度映射到最终预测目标
        self.out = nn.Linear(32, output_size)
        # Dropout 层：防止过拟合
        self.dropout = nn.Dropout(dropout)
        # 层归一化
        self.layer_norm = nn.LayerNorm(hidden_size2)

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

        # 1. CNN 特征提取
        # CNN 需要 (batch, channels, seq_len) 格式，所以需要调整维度
        x_cnn = x.permute(0, 2, 1)  # 形状变为 (batch, input_size, seq_len)
        
        # 第一层卷积 + 批归一化 + ReLU 激活
        x1 = self.conv1(x_cnn)  # (batch, 64, seq_len)
        x1 = self.batch_norm1(x1)  # 批归一化
        x1 = F.relu(x1)  # ReLU 激活
        
        # 第二层卷积 + 批归一化 + ReLU 激活
        x2 = self.conv2(x1)  # (batch, 128, seq_len)
        x2 = self.batch_norm2(x2)  # 批归一化
        x2 = F.relu(x2)  # ReLU 激活
        
        # 第三层卷积 + 批归一化 + ReLU 激活
        x3 = self.conv3(x2)  # (batch, 256, seq_len)
        x3 = self.batch_norm3(x3)  # 批归一化
        x3 = F.relu(x3)  # ReLU 激活
        
        # 第四层卷积 + 批归一化 + ReLU 激活
        x4 = self.conv4(x3)  # (batch, 128, seq_len)
        x4 = self.batch_norm4(x4)  # 批归一化
        x4 = F.relu(x4)  # ReLU 激活
        
        # 跳跃连接：融合多层特征
        x_cnn = x4 + x2  # 融合第二层和第四层特征

        # 2. 准备 LSTM 输入
        # 转回 LSTM 需要的 (batch, seq_len, features) 格式
        x_lstm = x_cnn.permute(0, 2, 1)  # 形状变为 (batch, seq_len, 128)
        
        # 3. LSTM 时序建模
        # LSTM 前向传播，返回输出序列和最终状态
        lstm_out, _ = self.lstm1(x_lstm)  # 输出形状：(batch, seq_len, hidden_size1)

        # 4. 特征融合与预测
        # 取最后一个时刻的输出作为整个序列的表示
        last_hidden = lstm_out[:, -1, :]  # 形状：(batch, hidden_size1)
        
        # 全连接层 + ReLU 激活
        fc_out = self.fc1(last_hidden)  # (batch, hidden_size2)
        fc_out = self.layer_norm(fc_out)  # 层归一化
        fc_out = F.relu(fc_out)  # ReLU 激活
        fc_out = self.dropout(fc_out)  # Dropout
        
        # 中间层
        fc_out = self.fc2(fc_out)  # (batch, 32)
        fc_out = F.relu(fc_out)  # ReLU 激活
        fc_out = self.dropout(fc_out)  # Dropout
        
        # 输出层，生成最终预测
        output = self.out(fc_out)  # (batch, output_size)
        
        return output
