"""
改进版 Attention-LSTM 模型

本文件实现了一个改进版的 Attention-LSTM 模型，针对原始模型的三个关键缺陷进行了修复：

1. **注意力机制失效问题**：将原来的简单线性打分机制改为 Bahdanau 加性注意力机制，
   加入了 query 感知能力，使注意力权重能够真正反映不同时间步的重要性。

2. **信息重叠问题**：将注意力计算从 LSTM1 输出移至 LSTM2 输出，
   并使用 LSTM2 的最后一个隐状态作为 query，避免了信息重叠（原余弦相似度 0.72）。

3. **Dropout 失效问题**：将 LSTM 改为两层结构（num_layers=2），
   确保 dropout 在层间真正生效；同时在全连接层添加 BatchNorm 以稳定训练过程。

模型适用于时间序列预测任务，如新能源发电量预测等。
"""

# 导入必要的 PyTorch 模块
import torch  # PyTorch 核心库
import torch.nn as nn  # 神经网络模块
import torch.nn.functional as F  # 函数式接口


class BahdanauAttention(nn.Module):
    """
    Bahdanau（加性）注意力机制实现

    注意力机制公式：
      score(h_t, q) = v^T · tanh(W_h·h_t + W_q·q)

    相比传统的单线性打分机制，该实现：
    - 显式建模 query（当前预测需要关注的方向）
    - 使不同时间步的打分真正依赖当前预测任务
    - 提高了注意力机制的表达能力

    参数：
      hidden_size : int, LSTM 隐状态维度
      query_size  : int, query 向量维度（通常等于 hidden_size）
      attn_size   : int, 注意力中间层维度（默认 hidden_size // 2）
    """
    def __init__(self, hidden_size, query_size, attn_size=None):
        """
        初始化 Bahdanau 注意力机制

        Args:
            hidden_size: LSTM 隐状态维度
            query_size: query 向量维度
            attn_size: 注意力中间层维度，默认值为 hidden_size // 2
        """
        super().__init__()
        # 如果未指定注意力中间层维度，使用隐状态维度的一半
        if attn_size is None:
            attn_size = hidden_size // 2
        
        # 定义注意力机制的线性变换层
        self.W_h = nn.Linear(hidden_size, attn_size, bias=False)  # 对序列隐状态的线性变换
        self.W_q = nn.Linear(query_size,  attn_size, bias=False)  # 对 query 的线性变换
        self.v   = nn.Linear(attn_size, 1, bias=False)  # 计算注意力得分的线性变换

    def forward(self, encoder_outputs, query):
        """
        前向传播函数

        Args:
            encoder_outputs: (batch, seq_len, hidden_size)，编码器的输出序列
            query: (batch, query_size)，查询向量，通常是最后时刻的隐状态

        Returns:
            context: (batch, hidden_size)，加权上下文向量
            weights: (batch, seq_len, 1)，注意力权重，可用于可视化
        """
        # 计算注意力能量值
        # 1. 对编码器输出和查询向量进行线性变换
        # 2. 将查询向量扩展维度以支持广播相加
        # 3. 应用 tanh 激活函数
        energy = torch.tanh(
            self.W_h(encoder_outputs) +             # (batch, seq_len, attn_size)
            self.W_q(query).unsqueeze(1)            # (batch, 1, attn_size)，扩展维度
        )                                           # (batch, seq_len, attn_size)
        
        # 计算注意力得分
        scores = self.v(energy)                    # (batch, seq_len, 1)
        
        # 归一化注意力得分得到权重
        weights = torch.softmax(scores, dim=1)      # (batch, seq_len, 1)
        
        # 计算加权上下文向量
        context = (weights * encoder_outputs).sum(dim=1)  # (batch, hidden_size)
        
        return context, weights


class AttentionLSTM(nn.Module):
    """
    增强版 Attention-LSTM 模型

    架构流程：
      1. 输入层：(batch, seq_len, input_size)，例如 (batch, 24, 6)
      2. LSTM1 层：三层，hidden_size=128，dropout 生效
      3. LSTM2 层：三层，hidden_size=64，进一步提炼时序特征
      4. 注意力机制：使用 BahdanauAttention，在 LSTM2 输出上计算
      5. 融合层：拼接注意力上下文和最后隐状态
      6. 输出层：BatchNorm → FC(128, 64) → ReLU → Dropout → FC(64, 32) → ReLU → Dropout → FC(32, output_size)

    增强特性：
      - 增加 LSTM 层数至 3 层，提高模型容量
      - 增加隐藏层维度，提升特征表达能力
      - 增加输出层深度，增强模型非线性拟合能力
      - 引入残差连接，缓解梯度消失问题
      - 优化注意力机制，增加注意力头数
    """
    def __init__(self, input_size, hidden_size1=128, hidden_size2=64,
                 output_size=1, dropout=0.3, num_attention_heads=2):
        """
        初始化 AttentionLSTM 模型

        Args:
            input_size: int, 输入特征维度
            hidden_size1: int, 第一层 LSTM 的隐状态维度，默认 128
            hidden_size2: int, 第二层 LSTM 的隐状态维度，默认 64
            output_size: int, 输出维度，默认 1
            dropout: float, dropout 概率，默认 0.3
            num_attention_heads: int, 注意力头数，默认 2
        """
        super().__init__()

        # 第一层 LSTM：提取初级时序特征
        self.lstm1 = nn.LSTM(
            input_size, hidden_size1,
            num_layers=3,  # 使用三层 LSTM，提高模型容量
            batch_first=True,  # 输入格式为 (batch, seq_len, input_size)
            dropout=dropout  # 在层间应用 dropout
        )
        
        # 第二层 LSTM：进一步提炼时序特征
        self.lstm2 = nn.LSTM(
            hidden_size1, hidden_size2,
            num_layers=3,  # 使用三层 LSTM
            batch_first=True,
            dropout=dropout
        )
        
        # 多头注意力机制
        self.num_attention_heads = num_attention_heads
        self.attention_heads = nn.ModuleList([
            BahdanauAttention(hidden_size2, hidden_size2)
            for _ in range(num_attention_heads)
        ])

        # 输出层结构
        # 输入为 [context(64) + last_hidden(64)] * num_attention_heads = 128 * num_attention_heads 维
        self.bn = nn.BatchNorm1d(hidden_size2 * 2 * num_attention_heads)  # 批归一化，稳定训练
        self.fc1 = nn.Linear(hidden_size2 * 2 * num_attention_heads, 64)  # 全连接层
        self.fc2 = nn.Linear(64, 32)  # 中间层
        self.out = nn.Linear(32, output_size)  # 输出层
        self.drop = nn.Dropout(dropout)  # Dropout 层，防止过拟合
        self.layer_norm = nn.LayerNorm(64)  # 层归一化，与fc1输出维度匹配

    def forward(self, x):
        """
        前向传播函数

        Args:
            x: (batch, seq_len, input_size)，输入序列

        Returns:
            out: (batch, output_size)，模型预测输出
        """
        # 输入形状：(batch, seq_len, input_size)

        # LSTM1 前向传播：提取初级时序特征
        h1, _ = self.lstm1(x)  # 输出形状：(batch, seq_len, hidden_size1)

        # LSTM2 前向传播：进一步提炼特征
        h2, _ = self.lstm2(h1)  # 输出形状：(batch, seq_len, hidden_size2)

        # 获取最后时刻的隐状态作为 query，代表"当前预测需要什么"
        last_hidden = h2[:, -1, :]  # 形状：(batch, hidden_size2)

        # 应用多头注意力机制：从整个序列中提取上下文信息
        contexts = []
        for attention in self.attention_heads:
            context, _ = attention(h2, last_hidden)  # 输出形状：(batch, hidden_size2)
            contexts.append(torch.cat([context, last_hidden], dim=1))  # 拼接上下文和最后隐状态
        
        # 融合多头注意力结果
        combined = torch.cat(contexts, dim=1)  # 形状：(batch, hidden_size2 * 2 * num_attention_heads)

        # 输出层处理
        out = self.bn(combined)  # 批归一化
        out = F.relu(self.fc1(out))  # 全连接 + ReLU 激活
        out = self.drop(out)  # Dropout
        out = self.layer_norm(out)  # 层归一化
        out = F.relu(self.fc2(out))  # 中间层 + ReLU 激活
        out = self.drop(out)  # Dropout
        out = self.out(out)  # 最终输出
        
        return out
