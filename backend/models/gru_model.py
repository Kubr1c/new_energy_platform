"""
GRU 模型 — 门控循环单元
比 LSTM 参数更少（无独立的记忆门），训练速度更快，
适合作为轻量级替代方案进行对比实验。
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class GRUModel(nn.Module):
    def __init__(self, input_size, hidden_size1=64, hidden_size2=32, output_size=1, dropout=0.2):
        super(GRUModel, self).__init__()
        self.gru1 = nn.GRU(input_size, hidden_size1, batch_first=True, dropout=dropout)
        self.gru2 = nn.GRU(hidden_size1, hidden_size2, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size2, 16)
        self.out = nn.Linear(16, output_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        gru_out1, _ = self.gru1(x)           # (batch, seq_len, hidden1)
        gru_out2, _ = self.gru2(gru_out1)    # (batch, seq_len, hidden2)
        # 取最后一个时刻的输出
        last_hidden = gru_out2[:, -1, :]     # (batch, hidden2)
        fc_out = F.relu(self.fc(last_hidden))
        fc_out = self.dropout(fc_out)
        output = self.out(fc_out)
        return output
