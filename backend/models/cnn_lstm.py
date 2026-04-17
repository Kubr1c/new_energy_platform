"""
CNN-LSTM 混合模型
使用一维卷积（Conv1D）提取局部特征，然后通过 LSTM 捕获时序依赖关系。
CNN 擅长发现短时间窗口内的特征模式（如功率突变、日内波动形状），
LSTM 负责建模长时间依赖（如日间趋势、周期性规律）。
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CNNLSTM(nn.Module):
    def __init__(self, input_size, hidden_size1=64, hidden_size2=32, output_size=1, dropout=0.2):
        super(CNNLSTM, self).__init__()

        # --- CNN 特征提取层 ---
        # Conv1D 需要 (batch, channels, seq_len)，输入的 channels = input_size
        self.conv1 = nn.Conv1d(in_channels=input_size, out_channels=64, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(in_channels=64, out_channels=64, kernel_size=3, padding=1)
        self.batch_norm1 = nn.BatchNorm1d(64)
        self.batch_norm2 = nn.BatchNorm1d(64)

        # --- LSTM 时序建模层 ---
        self.lstm = nn.LSTM(64, hidden_size1, batch_first=True, dropout=dropout)

        # --- 全连接输出层 ---
        self.fc = nn.Linear(hidden_size1, hidden_size2)
        self.out = nn.Linear(hidden_size2, output_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x: (batch, seq_len, input_size)

        # CNN 需要 (batch, channels, seq_len)
        x_cnn = x.permute(0, 2, 1)                     # (batch, input_size, seq_len)
        x_cnn = F.relu(self.batch_norm1(self.conv1(x_cnn)))  # (batch, 64, seq_len)
        x_cnn = F.relu(self.batch_norm2(self.conv2(x_cnn)))  # (batch, 64, seq_len)

        # 转回 LSTM 需要的 (batch, seq_len, features)
        x_lstm = x_cnn.permute(0, 2, 1)                # (batch, seq_len, 64)
        lstm_out, _ = self.lstm(x_lstm)                 # (batch, seq_len, hidden1)

        # 取最后一个时刻
        last_hidden = lstm_out[:, -1, :]                # (batch, hidden1)
        fc_out = F.relu(self.fc(last_hidden))
        fc_out = self.dropout(fc_out)
        output = self.out(fc_out)
        return output
