"""
标准 LSTM 模型 — 基准对照模型
双层 LSTM，无注意力机制，用于与 Attention-LSTM 形成对比，
验证注意力机制对预测精度的提升效果。
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class StandardLSTM(nn.Module):
    def __init__(self, input_size, hidden_size1=64, hidden_size2=32, output_size=1, dropout=0.2):
        super(StandardLSTM, self).__init__()
        self.lstm1 = nn.LSTM(input_size, hidden_size1, batch_first=True, dropout=dropout)
        self.lstm2 = nn.LSTM(hidden_size1, hidden_size2, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size2, 16)
        self.out = nn.Linear(16, output_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        lstm_out1, _ = self.lstm1(x)          # (batch, seq_len, hidden1)
        lstm_out2, _ = self.lstm2(lstm_out1)  # (batch, seq_len, hidden2)
        # 仅取最后一个时刻的输出
        last_hidden = lstm_out2[:, -1, :]     # (batch, hidden2)
        fc_out = F.relu(self.fc(last_hidden))
        fc_out = self.dropout(fc_out)
        output = self.out(fc_out)
        return output
