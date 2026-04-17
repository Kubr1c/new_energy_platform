import torch
import torch.nn as nn
import torch.nn.functional as F

class Attention(nn.Module):
    def __init__(self, hidden_size):
        super(Attention, self).__init__()
        self.attn = nn.Linear(hidden_size, 1)

    def forward(self, lstm_output):
        # lstm_output: (batch, seq_len, hidden_size)
        attn_weights = torch.softmax(self.attn(lstm_output), dim=1)
        context = torch.sum(attn_weights * lstm_output, dim=1)
        return context, attn_weights

class AttentionLSTM(nn.Module):
    def __init__(self, input_size, hidden_size1=64, hidden_size2=32, output_size=1, dropout=0.2):
        super(AttentionLSTM, self).__init__()
        self.lstm1 = nn.LSTM(input_size, hidden_size1, batch_first=True, dropout=dropout)
        self.lstm2 = nn.LSTM(hidden_size1, hidden_size2, batch_first=True, dropout=dropout)
        self.attention = Attention(hidden_size1)   # 对第一层输出做注意力
        self.fc = nn.Linear(hidden_size1 + hidden_size2, 16)
        self.out = nn.Linear(16, output_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        lstm_out1, _ = self.lstm1(x)           # (batch, seq_len, hidden1)
        context, _ = self.attention(lstm_out1) # (batch, hidden1)
        lstm_out2, _ = self.lstm2(lstm_out1)   # (batch, seq_len, hidden2)
        # 取最后一个时刻的LSTM2输出作为特征
        last_hidden2 = lstm_out2[:, -1, :]      # (batch, hidden2)
        combined = torch.cat([context, last_hidden2], dim=1)
        fc_out = F.relu(self.fc(combined))
        fc_out = self.dropout(fc_out)
        output = self.out(fc_out)
        return output
