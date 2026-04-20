"""
================================================================================
Temporal Fusion Transformer (TFT) 模型
================================================================================

【模型简介】
    Temporal Fusion Transformer（TFT）是一种先进的时间序列预测模型，
    由Google于2019年提出，专门设计用于处理复杂的时间序列预测问题。
    它结合了Transformer架构的强大表示能力和专门针对时间序列的创新设计。

【核心设计理念】
    1. 多时间尺度建模：通过多头注意力机制捕获不同时间尺度的依赖关系
    2. 特征自适应选择：通过门控机制自动选择最相关的输入特征
    3. 静态特征融合：有效利用不随时间变化的静态特征（如地理位置）
    4. 可解释性：提供特征重要性分析和注意力权重可视化

【适用场景】
    - 新能源发电功率预测（风电、光伏）
    - 系统负荷预测
    - 电力价格预测
    - 交通流量预测
    - 销售量预测

【本实现包含的模型】
    1. TemporalFusionTransformer：基础TFT模型
    2. ImprovedTFT：改进版TFT模型（本项目使用）

【改进版TFT的优化点】
    - 更深的网络结构（3层Transformer）
    - 更大的隐藏层维度（128）
    - 位置编码增强（可处理更长序列）
    - 改进的输出层设计

================================================================================
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class GatedLinearUnit(nn.Module):
    """
    ==========================================================================
    门控线性单元 (Gated Linear Unit, GLU)
    ==========================================================================

    【功能说明】
        门控线性单元是TFT模型的核心组件之一，用于实现特征的自适应选择。
        它通过学习一个"门控"信号来控制信息流量，决定哪些特征更重要。

    【数学原理】
        输出 = Linear(x) * sigmoid(Gate(x))

        - Linear(x): 主路径的特征变换
        - Gate(x): 门控信号，输出[0,1]范围的数值
        - *: 逐元素乘法

        当门控值接近1时，信息通过；接近0时，信息被阻断。

    【优势】
        - 梯度流更稳定
        - 可以学习"什么信息要传递，什么信息要阻断"
        - 对输入的适应性更强

    【输入输出】
        - 输入: (batch, input_dim)
        - 输出: (batch, output_dim)
    """
    def __init__(self, input_dim, output_dim):
        """
        初始化门控线性单元

        参数:
            input_dim (int): 输入特征维度
            output_dim (int): 输出特征维度
        """
        super(GatedLinearUnit, self).__init__()

        # 主路径：正常的线性变换
        self.linear = nn.Linear(input_dim, output_dim)

        # 门控路径：生成门控信号的线性变换
        # 输出维度相同，用于逐元素相乘
        self.gate = nn.Linear(input_dim, output_dim)

    def forward(self, x):
        """
        前向传播

        参数:
            x (torch.Tensor): 输入张量，形状为 (batch, input_dim)

        返回:
            torch.Tensor: 门控后的输出，形状为 (batch, output_dim)
        """
        # 主路径变换
        linear_out = self.linear(x)

        # 门控信号，使用sigmoid将输出压缩到[0,1]
        gate_signal = torch.sigmoid(self.gate(x))

        # 逐元素相乘，实现门控效果
        return linear_out * gate_signal


class GatedResidualNetwork(nn.Module):
    """
    ==========================================================================
    门控残差网络 (Gated Residual Network, GRN)
    ==========================================================================

    【功能说明】
        门控残差网络是TFT模型中用于特征处理的基本模块。
        它结合了残差连接（Residual Connection）和门控机制，
        可以在深层网络中有效传递梯度，同时自适应地选择特征。

    【网络结构】
        输入
          │
          ├──────────────────┐
          │                  │
          ▼                  │ (残差分支)
      ┌─────────┐            │
      │   FC1   │            │
      └────┬────┘            │
          │                  │
      ┌────▼────┐            │
      │   GLU   │            │
      └────┬────┘            │
          │                  │
      ┌────▼────┐            │
      │   FC2   │            │
      └────┬────┘            │
          │                  │
          ▼                  │
      ┌─────────┐            │
      │ LayerNorm│◄───────────┤
      └────┬────┘            │
          │                  │
          ▼                  │
        输出 ◄───────────────┘
                   (加法残差连接)

    【残差连接的作用】
        - 缓解深层网络的梯度消失问题
        - 允许梯度直接回传
        - 使网络更容易学习恒等映射

    【门控机制的作用】
        - 自适应地决定是否添加残差
        - 如果主路径没有学到有用信息，门控可以"关闭"残差

    【输入输出】
        - 输入: (batch, input_dim)
        - 输出: (batch, output_dim)
    """
    def __init__(self, input_dim, hidden_dim, output_dim, dropout=0.1):
        """
        初始化门控残差网络

        参数:
            input_dim (int): 输入特征维度
            hidden_dim (int): 隐藏层维度（GLU内部使用）
            output_dim (int): 输出特征维度
            dropout (float): Dropout比率，防止过拟合
        """
        super(GatedResidualNetwork, self).__init__()

        # 第一层全连接：将输入维度映射到隐藏维度
        self.fc1 = nn.Linear(input_dim, hidden_dim)

        # 门控线性单元：实现特征选择
        self.glu = GatedLinearUnit(hidden_dim, hidden_dim)

        # 第二层全连接：将隐藏维度映射到输出维度
        self.fc2 = nn.Linear(hidden_dim, output_dim)

        # Dropout层：在训练时随机断开部分连接，防止过拟合
        self.dropout = nn.Dropout(dropout)

        # 层归一化：稳定训练过程，加速收敛
        self.layer_norm = nn.LayerNorm(output_dim)

        # 残差连接：输入和输出维度不同时，需要线性变换来匹配
        self.residual = nn.Linear(input_dim, output_dim) if input_dim != output_dim else None

    def forward(self, x):
        """
        前向传播

        参数:
            x (torch.Tensor): 输入张量

        返回:
            torch.Tensor: 处理后的输出
        """
        # ========== 主路径 ==========
        # 第一层：降维/变换
        out = F.relu(self.fc1(x))

        # 门控：自适应特征选择
        out = self.glu(out)

        # Dropout：防止过拟合
        out = self.dropout(out)

        # 第二层：升维/变换
        out = self.fc2(out)

        # ========== 残差连接 ==========
        if self.residual is not None:
            # 当输入输出维度不匹配时，使用线性变换的残差
            out = out + self.residual(x)
        else:
            # 当输入输出维度相同时，直接相加
            out = out + x

        # ========== 层归一化 ==========
        # 稳定训练过程
        out = self.layer_norm(out)

        return out


class TemporalFusionTransformer(nn.Module):
    """
    ==========================================================================
    基础Temporal Fusion Transformer模型
    ==========================================================================

    【模型架构】
        1. 静态特征编码器：处理不随时间变化的特征
        2. 时间特征编码器：使用GRN处理时间序列
        3. Transformer编码器：捕获多时间尺度依赖
        4. 输出层：生成预测结果

    【输入输出】
        - 输入: (batch, seq_len, input_size) - 时间序列数据
        - 输出: (batch, output_size) - 预测值
    """
    def __init__(self, input_size, static_size=0, hidden_size=64, num_heads=4,
                 num_layers=2, dropout=0.1, output_size=1):
        """
        初始化TFT模型

        参数:
            input_size (int): 时间特征的维度（每个时间步的特征数）
            static_size (int): 静态特征的维度（不随时间变化的特征数）
            hidden_size (int): 隐藏层维度
            num_heads (int): 注意力头数（用于Multi-Head Attention）
            num_layers (int): Transformer编码器的层数
            dropout (float): Dropout比率
            output_size (int): 输出维度（要预测的目标数）
        """
        super(TemporalFusionTransformer, self).__init__()

        # 保存模型配置参数
        self.input_size = input_size
        self.static_size = static_size
        self.hidden_size = hidden_size

        # ========== 静态特征处理 ==========
        if static_size > 0:
            # 静态特征编码器
            self.static_encoder = GatedResidualNetwork(
                static_size, hidden_size, hidden_size, dropout
            )
            # 静态特征注意力（用于加权融合）
            self.static_attention = GatedResidualNetwork(
                hidden_size, hidden_size, num_heads, dropout
            )

        # ========== 时间特征编码 ==========
        # 使用GRN对输入的每个时间步进行特征处理
        self.temporal_encoder = GatedResidualNetwork(
            input_size, hidden_size, hidden_size, dropout
        )

        # ========== Transformer编码器 ==========
        # 多头自注意力机制，捕获时间序列中的长期依赖
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,          # 输入输出的特征维度
            nhead=num_heads,               # 注意力头数
            dim_feedforward=hidden_size * 4,  # 前馈网络的隐藏层维度
            dropout=dropout,               # Dropout比率
            batch_first=True               # 输入格式为(batch, seq, feature)
        )
        # 堆叠多个Transformer编码器层
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        # ========== 输出层 ==========
        # 使用GRN处理解码器的输出
        self.output_gate = GatedResidualNetwork(
            hidden_size, hidden_size, hidden_size, dropout
        )
        # 最终的线性输出层
        self.output_linear = nn.Linear(hidden_size, output_size)

    def forward(self, x, static=None):
        """
        前向传播

        参数:
            x (torch.Tensor): 时间序列输入，形状 (batch, seq_len, input_size)
                - batch: 批量大小
                - seq_len: 序列长度（时间步数）
                - input_size: 每个时间步的特征数
            static (torch.Tensor): 静态特征，形状 (batch, static_size)
                可选，如果不提供则不处理静态特征

        返回:
            torch.Tensor: 预测输出，形状 (batch, output_size)
        """
        batch_size, seq_len, _ = x.shape

        # ========== 时间特征编码 ==========
        # 对每个时间步独立应用GRN
        temporal_emb = self.temporal_encoder(x)

        # ========== 静态特征融合 ==========
        if self.static_size > 0 and static is not None:
            # 编码静态特征
            static_emb = self.static_encoder(static)

            # 生成静态注意力权重
            static_attn = self.static_attention(static_emb)

            # 扩展注意力权重以匹配序列长度
            # 从 (batch, num_heads) -> (batch, 1, num_heads) -> (batch, seq_len, num_heads)
            static_attn = static_attn.unsqueeze(1).repeat(1, seq_len, 1)

            # 融合静态特征（通过加法）
            temporal_emb = temporal_emb + static_attn

        # ========== Transformer编码 ==========
        # 通过自注意力机制捕获时间依赖
        transformer_out = self.transformer_encoder(temporal_emb)

        # ========== 输出处理 ==========
        # 取最后一个时间步的输出（用于预测）
        last_hidden = transformer_out[:, -1, :]

        # 通过输出门控层
        out = self.output_gate(last_hidden)

        # 最终线性变换
        out = self.output_linear(out)

        return out


class ImprovedTFT(nn.Module):
    """
    ==========================================================================
    改进版Temporal Fusion Transformer模型
    ==========================================================================

    【相对于基础TFT的改进】
        1. 更深的网络：3层Transformer（基础版是2层）
        2. 更大的隐藏层：128维（基础版是64维）
        3. 增强的位置编码：可处理更长的序列
        4. 改进的特征投影层：更好地处理输入特征
        5. 更强的输出层：两层GRN（基础版是一层）

    【模型架构图】

        输入序列 (batch, 24, 6)
              │
              ▼
        ┌─────────────────┐
        │   输入投影层    │  ← GatedResidualNetwork
        └────────┬────────┘
              │
              ▼
        ┌─────────────────┐
        │   位置编码      │  ← 可学习的正弦位置编码
        └────────┬────────┘
              │
              ▼
        ┌─────────────────┐
        │ 静态特征融合    │  ← (可选) 与位置编码相加
        └────────┬────────┘
              │
              ▼
        ┌─────────────────┐
        │   层归一化      │
        └────────┬────────┘
              │
              ▼
        ┌─────────────────┐
        │ Transformer     │  ← 3层Transformer编码器
        │ Encoder × 3    │
        └────────┬────────┘
              │
              ▼
        ┌─────────────────┐
        │ 取最后时间步    │  ← decoder读取最后一个隐状态
        └────────┬────────┘
              │
              ▼
        ┌─────────────────┐
        │   输出投影层    │  ← 两层GatedResidualNetwork
        └────────┬────────┘
              │
              ▼
        ┌─────────────────┐
        │   线性输出层    │  ← 输出预测值
        └────────┬────────┘
              │
              ▼
        预测结果 (batch, 3)
    """
    def __init__(self, input_size, static_size=0, hidden_size=128, num_heads=4,
                 num_layers=3, dropout=0.2, output_size=1):
        """
        初始化改进版TFT模型

        参数:
            input_size (int): 输入特征维度（每个时间步的特征数）
            static_size (int): 静态特征维度（不随时间变化的特征数）
            hidden_size (int): 隐藏层维度（默认128，更大的表示能力）
            num_heads (int): 注意力头数（默认4）
            num_layers (int): Transformer编码器层数（默认3，更深的网络）
            dropout (float): Dropout比率（默认0.2，防止过拟合）
            output_size (int): 输出维度（要预测的目标变量数）

        示例:
            # 创建模型实例
            model = ImprovedTFT(
                input_size=6,      # 6个时间特征
                static_size=0,     # 无静态特征
                hidden_size=128,   # 128维隐藏层
                num_heads=4,       # 4头注意力
                num_layers=3,      # 3层Transformer
                dropout=0.2,       # 20%的Dropout
                output_size=3      # 3个输出（风电、光伏、负荷）
            )

            # 前向传播
            x = torch.randn(32, 24, 6)  # batch=32, seq_len=24, features=6
            output = model(x)           # (32, 3)
        """
        super(ImprovedTFT, self).__init__()

        # 保存模型配置
        self.input_size = input_size
        self.static_size = static_size
        self.hidden_size = hidden_size

        # ========== 输入特征处理 ==========
        # 对输入的每个时间步进行初步特征提取和变换
        # 使用更大的隐藏层维度（128）来处理输入特征
        self.input_proj = GatedResidualNetwork(
            input_size, hidden_size, hidden_size, dropout
        )

        # ========== 静态特征处理 ==========
        if static_size > 0:
            # 静态特征投影
            self.static_proj = GatedResidualNetwork(
                static_size, hidden_size, hidden_size, dropout
            )
            # 静态特征注意力
            self.static_attention = GatedResidualNetwork(
                hidden_size, hidden_size, num_heads, dropout
            )

        # ========== 位置编码 ==========
        # 可学习的位置编码，帮助模型理解时间序列的顺序
        # 初始化为随机参数，训练过程中自动学习
        # 支持最长1000个时间步的位置编码
        self.pos_encoding = nn.Parameter(torch.randn(1, 1000, hidden_size))

        # ========== Transformer编码器 ==========
        # 使用更深（3层）和更宽（128维）的Transformer
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,            # 隐藏层维度
            nhead=num_heads,                 # 注意力头数
            dim_feedforward=hidden_size * 4, # 前馈网络维度（512）
            dropout=dropout,                # Dropout比率
            batch_first=True                # batch优先的输入格式
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        # ========== 输出层 ==========
        # 两层GRN，更强的输出变换能力
        self.output_proj = GatedResidualNetwork(
            hidden_size, hidden_size * 2, hidden_size, dropout
        )
        # 最终线性输出
        self.output_linear = nn.Linear(hidden_size, output_size)

        # ========== 层归一化 ==========
        # 在进入Transformer之前进行归一化，稳定训练
        self.layer_norm = nn.LayerNorm(hidden_size)

    def forward(self, x, static=None):
        """
        前向传播

        参数:
            x (torch.Tensor): 时间序列输入
                形状: (batch_size, sequence_length, input_size)
                示例: (32, 24, 6) 表示32个样本，每个样本24个时间步，6个特征
            static (torch.Tensor, optional): 静态特征
                形状: (batch_size, static_size)
                可选，如果不提供则跳过静态特征处理

        返回:
            torch.Tensor: 预测输出
                形状: (batch_size, output_size)
                示例: (32, 3) 表示32个样本的3个目标预测值

        处理流程:
            1. 输入投影：将输入特征映射到隐藏维度
            2. 添加位置编码：注入序列位置信息
            3. 静态特征融合：(可选) 融入静态特征
            4. Transformer编码：捕获多时间尺度依赖
            5. 输出投影：变换到输出空间
        """
        batch_size, seq_len, _ = x.shape

        # ========== 第1步：输入特征处理 ==========
        # 将原始输入特征投影到隐藏空间
        x = self.input_proj(x)

        # ========== 第2步：添加位置编码 ==========
        # 位置编码帮助模型理解时间步的相对和绝对位置
        # 使用切片确保位置编码长度匹配序列长度
        if seq_len > 1000:
            # 对于超长序列，使用截断的位置编码
            pos_enc = self.pos_encoding[:, :1000, :]
        else:
            # 正常情况：直接使用前seq_len个位置编码
            pos_enc = self.pos_encoding[:, :seq_len, :]

        # 将位置编码添加到序列中
        x = x + pos_enc

        # ========== 第3步：静态特征融合 ==========
        if self.static_size > 0 and static is not None:
            # 投影静态特征到隐藏空间
            static_emb = self.static_proj(static)

            # 扩展以匹配序列长度
            static_emb = static_emb.unsqueeze(1).repeat(1, seq_len, 1)

            # 通过加法融合静态特征
            x = x + static_emb

        # ========== 第4步：层归一化 ==========
        # 在进入Transformer之前进行归一化
        x = self.layer_norm(x)

        # ========== 第5步：Transformer编码 ==========
        # 通过多层自注意力捕获时间依赖
        x = self.transformer_encoder(x)

        # ========== 第6步：取最后一个时间步 ==========
        # 假设最后一个时间步包含最完整的上下文信息
        last_hidden = x[:, -1, :]

        # ========== 第7步：输出处理 ==========
        # 两层GRN变换
        out = self.output_proj(last_hidden)

        # 线性输出
        out = self.output_linear(out)

        return out


def get_tft_model(input_size, output_size, static_size=0):
    """
    ==========================================================================
    TFT模型工厂函数
    ==========================================================================

    【功能说明】
        创建一个ImprovedTFT模型实例的便捷函数。
        这是推荐的使用方式，因为它：
        1. 封装了模型创建的细节
        2. 提供了合理的默认参数
        3. 与模型注册表（model_registry.py）的接口兼容

    【参数说明】
        input_size (int): 输入特征维度
            示例：如果使用6个时间特征（风功率、光伏、负荷、温度、辐照度、风速）
            则 input_size = 6

        output_size (int): 输出维度
            示例：如果要预测3个目标（风功率、光伏、负荷）
            则 output_size = 3

        static_size (int, 可选): 静态特征维度
            如果没有静态特征，默认为0

    【返回值的类型】
        ImprovedTFT: 改进版TFT模型实例

    【使用示例】
        # 创建模型
        >>> model = get_tft_model(input_size=6, output_size=3)
        >>> print(model)
        ImprovedTFT(
          (input_proj): GatedResidualNetwork(...)
          (transformer_encoder): TransformerEncoder(...)
          (output_proj): GatedResidualNetwork(...)
          (output_linear): Linear(...)
        )

        # 前向传播
        >>> x = torch.randn(32, 24, 6)  # (batch, seq_len, features)
        >>> y = model(x)               # (32, 3)

    【默认参数说明】
        - hidden_size=128: 较大的隐藏维度，提供更强的表示能力
        - num_heads=4: 4头注意力，平衡表达能力和计算效率
        - num_layers=3: 3层Transformer，足够捕获复杂的时序依赖
        - dropout=0.2: 适中的Dropout，防止过拟合
    """
    return ImprovedTFT(
        input_size=input_size,
        static_size=static_size,
        hidden_size=128,     # 更大的隐藏层，更强的表示能力
        num_heads=4,          # 4头注意力
        num_layers=3,         # 3层Transformer
        dropout=0.2,          # 20% Dropout
        output_size=output_size
    )
