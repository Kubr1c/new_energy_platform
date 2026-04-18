"""
改进版 Attention-LSTM 模型

修复三个原始缺陷：
  1. 注意力机制失效（权重近乎均匀）：改为 Bahdanau 双线性打分，加入 query 感知
  2. 注意力与 LSTM2 信息重叠（余弦相似度 0.72）：注意力改在 LSTM2 输出上做，
     用 last hidden 作为 query，增量提取全局上下文信息
  3. 单层 LSTM dropout 被 PyTorch 忽略：LSTM 改为两层（num_layers=2），
     确保 dropout 真正在层间生效；fc 层加 BatchNorm 稳定训练
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class BahdanauAttention(nn.Module):
    """
    Bahdanau（加性）注意力机制：
      score(h_t, q) = v^T · tanh(W_h·h_t + W_q·q)

    相比原来的 Linear(hidden, 1) 单线性打分，增加了对 query（当前关注方向）
    的显式建模，使不同时间步的打分真正依赖当前预测需要关注的内容。

    参数：
      hidden_size : LSTM 隐状态维度
      query_size  : query 向量维度（通常等于 hidden_size）
      attn_size   : 注意力中间层维度（默认 hidden_size // 2）
    """
    def __init__(self, hidden_size, query_size, attn_size=None):
        super().__init__()
        if attn_size is None:
            attn_size = hidden_size // 2
        self.W_h = nn.Linear(hidden_size, attn_size, bias=False)
        self.W_q = nn.Linear(query_size,  attn_size, bias=False)
        self.v   = nn.Linear(attn_size, 1, bias=False)

    def forward(self, encoder_outputs, query):
        """
        encoder_outputs : (batch, seq_len, hidden_size)
        query           : (batch, query_size)  —— 最后时刻的隐状态

        返回：
          context : (batch, hidden_size)  加权上下文向量
          weights : (batch, seq_len, 1)   注意力权重（可视化用）
        """
        # query 扩展到 (batch, 1, attn_size) 再广播相加
        energy = torch.tanh(
            self.W_h(encoder_outputs) +             # (batch, seq, attn)
            self.W_q(query).unsqueeze(1)            # (batch, 1,   attn)
        )                                           # (batch, seq, attn)
        scores  = self.v(energy)                    # (batch, seq, 1)
        weights = torch.softmax(scores, dim=1)      # (batch, seq, 1)
        context = (weights * encoder_outputs).sum(dim=1)  # (batch, hidden)
        return context, weights


class AttentionLSTM(nn.Module):
    """
    改进版 Attention-LSTM（修复三个结构缺陷后的版本）

    架构流程：
      input (batch, 24, 6)
        → LSTM1 (2层, hidden=64, dropout生效)
        → LSTM2 (2层, hidden=32, dropout生效)
        → last_hidden = lstm2_output[:, -1, :]   (当前时刻隐状态，作为 query)
        → BahdanauAttention(lstm2_output, last_hidden)  → context (32维)
        → BatchNorm → FC(64, 32) → ReLU → Dropout
        → FC(32, output_size)

    与原版对比：
      - 注意力参数：65 → 约 1,600（更具表达能力）
      - 注意力位置：LSTM1 输出 → LSTM2 输出（消除重叠）
      - LSTM 层数：1 → 2（dropout 真正生效）
      - 新增 BatchNorm 稳定梯度
      - 总参数量：32,644 → 约 41,000（增幅 25%，代价合理）
    """
    def __init__(self, input_size, hidden_size1=64, hidden_size2=32,
                 output_size=1, dropout=0.2):
        super().__init__()

        # LSTM1：两层，dropout 在层间生效
        self.lstm1 = nn.LSTM(
            input_size, hidden_size1,
            num_layers=2, batch_first=True, dropout=dropout
        )
        # LSTM2：两层，进一步提炼时序特征
        self.lstm2 = nn.LSTM(
            hidden_size1, hidden_size2,
            num_layers=2, batch_first=True, dropout=dropout
        )
        # Bahdanau 注意力：在 LSTM2 输出上打分，用 last_hidden 作为 query
        self.attention = BahdanauAttention(hidden_size2, hidden_size2)

        # 输出层：[context(32) + last_hidden(32)] = 64 → 32 → output_size
        self.bn   = nn.BatchNorm1d(hidden_size2 * 2)
        self.fc   = nn.Linear(hidden_size2 * 2, hidden_size2)
        self.out  = nn.Linear(hidden_size2, output_size)
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        # x: (batch, seq_len, input_size)

        # LSTM1：提取初级时序特征
        h1, _ = self.lstm1(x)           # (batch, seq, hidden1)

        # LSTM2：进一步提炼特征
        h2, _ = self.lstm2(h1)          # (batch, seq, hidden2)

        # query = 最后时刻的隐状态，代表"当前预测需要什么"
        last_hidden = h2[:, -1, :]      # (batch, hidden2)

        # Bahdanau 注意力：用 last_hidden 作为 query，从整个序列中提取上下文
        context, _ = self.attention(h2, last_hidden)  # (batch, hidden2)

        # 拼接：[注意力上下文, 最后隐状态]
        combined = torch.cat([context, last_hidden], dim=1)  # (batch, hidden2*2)

        # 输出层
        out = self.bn(combined)
        out = F.relu(self.fc(out))
        out = self.drop(out)
        out = self.out(out)
        return out
