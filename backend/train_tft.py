#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
TFT模型单独训练脚本
================================================================================

【文件说明】
    本脚本用于单独训练Temporal Fusion Transformer (TFT)模型。
    TFT是一种先进的时间序列预测模型，特别适合处理带有静态特征和时间
    特征的时间序列数据，如新能源发电预测和系统负荷预测。

【功能特点】
    1. 从数据库加载2023年全年数据
    2. 按时间顺序将数据切分为训练集、验证集和测试集（70%/15%/15%）
    3. 使用早停机制防止过拟合
    4. 自动选择计算设备（GPU优先）
    5. 保存训练过程的历史记录和最优模型权重

【使用场景】
    - 调试和测试TFT模型
    - 单独训练TFT模型而无需训练其他模型
    - 快速验证TFT模型的性能

【输出结果】
    - 模型权重文件：backend/models_saved/tft.pth
    - 训练过程日志（控制台输出）

================================================================================
"""

import os
import sys
import datetime

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import pandas as pd

# ================================================================================
# 路径配置
# ================================================================================

# 获取当前脚本所在目录的绝对路径
_backend_dir = os.path.dirname(os.path.abspath(__file__))

# 将backend目录添加到Python模块搜索路径
# 这样可以确保正确导入项目内的自定义模块
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# 导入项目内部模块
from models.model_registry import get_model  # 模型注册表，提供统一的模型获取接口
from preprocessing.data_utils import DataPreprocessor  # 数据预处理器，负责数据清洗和归一化
from models.database import NewEnergyData  # 数据库模型，定义新能源数据的表结构
from app import create_app  # Flask应用工厂函数，用于创建Web应用实例

# ================================================================================
# 常量定义
# ================================================================================

# 【特征列】
# 定义模型使用的输入特征：
# - wind_power: 风电发电功率
# - pv_power: 光伏发电功率
# - load: 系统负荷
# - temperature: 环境温度
# - irradiance: 太阳辐照度
# - wind_speed: 风速
FEATURES = ['wind_power', 'pv_power', 'load', 'temperature', 'irradiance', 'wind_speed']

# 【目标列】
# 定义模型需要预测的目标变量：
# - wind_power: 风电发电功率预测
# - pv_power: 光伏发电功率预测
# - load: 系统负荷预测
TARGETS = ['wind_power', 'pv_power', 'load']

# 【输入序列长度】
# 定义输入模型的历史数据时间窗口长度（小时）
# 24小时的历史数据用于预测下一个时刻
INPUT_LEN = 24

# 【输出序列长度】
# 定义模型一次性预测的未来时间步数
# 这里设为1，表示单步预测（预测下一个小时）
OUTPUT_LEN = 1

# 【数据时间范围】
# 定义用于训练的数据时间范围（2023年全年）
# 选择2023年是因为该年数据覆盖率高达99.7%，且数据连续无大间隔
_DB_YEAR_START = datetime.datetime(2023, 1, 1)  # 数据起始时间（包含）
_DB_YEAR_END = datetime.datetime(2024, 1, 1)    # 数据结束时间（不包含）

# ================================================================================
# 数据加载与分割函数
# ================================================================================

def load_split_from_database(app):
    """
    ======================================================================
    从数据库加载并分割训练数据
    ======================================================================

    【函数功能】
        从MySQL数据库中加载指定时间范围的新能源数据，并按时间顺序
        将数据切分为训练集、验证集和测试集三个不相交的子集。

    【数据切分策略】
        - 切分比例：70%训练集 / 15%验证集 / 15%测试集
        - 切分方式：严格按时间先后顺序（时序数据不能打乱！）
        - 这样可以确保：
          1. 训练时看不到未来数据，避免数据泄露
          2. 验证集和测试集都是"没见过"的数据，能真实反映模型泛化能力

    【参数说明】
        app : Flask应用实例
            Flask应用对象，用于获取数据库连接上下文

    【返回值的具体内容】
        tuple: 包含三个DataFrame的元组
            - df_train: 训练集（70%），时间范围的前70%数据
            - df_val: 验证集（15%），时间范围的中间15%数据
            - df_test: 测试集（15%），时间范围的后15%数据
        每个DataFrame都包含FEATURES中定义的所有特征列，以及timestamp时间戳列

    【数据质量保证】
        - 自动过滤None/NaN值，替换为0.0
        - 按时间戳升序排列，确保数据的时间顺序正确
        - 重置所有DataFrame的索引，从0开始连续编号

    【使用示例】
        >>> app = create_app()
        >>> df_train, df_val, df_test = load_split_from_database(app)
        >>> print(f"训练集大小: {len(df_train)}")
    """
    # -------------------------------------------------------------------------
    # 第1步：数据库查询
    # -------------------------------------------------------------------------
    # 使用Flask应用上下文执行数据库查询
    # 查询2023年全年的数据，按时间戳升序排列
    with app.app_context():
        records = (
            NewEnergyData.query  # 获取数据库查询对象
            .filter(
                # 时间范围过滤：只取2023年的数据
                NewEnergyData.timestamp >= _DB_YEAR_START,  # 大于等于开始时间
                NewEnergyData.timestamp < _DB_YEAR_END,    # 小于结束时间
            )
            .order_by(NewEnergyData.timestamp.asc())  # 按时间升序排列
            .all()  # 获取所有匹配的记录
        )

    # -------------------------------------------------------------------------
    # 第2步：数据校验
    # -------------------------------------------------------------------------
    # 确保数据库中有可用的训练数据
    if not records:
        raise ValueError("数据库中没有2023年训练数据，请先导入数据！")

    # -------------------------------------------------------------------------
    # 第3步：数据转换
    # -------------------------------------------------------------------------
    # 将数据库记录对象转换为Pandas DataFrame格式
    # 每个记录包含：timestamp, wind_power, pv_power, load, temperature, irradiance, wind_speed
    rows = [{
        'timestamp':   r.timestamp,        # 时间戳，保持原始格式
        'wind_power':  r.wind_power or 0.0,  # 风电功率，None值替换为0.0
        'pv_power':    r.pv_power or 0.0,    # 光伏功率，None值替换为0.0
        'load':        r.load or 0.0,         # 系统负荷，None值替换为0.0
        'temperature': r.temperature or 0.0,  # 温度，None值替换为0.0
        'irradiance':  r.irradiance or 0.0,   # 辐照度，None值替换为0.0
        'wind_speed':  r.wind_speed or 0.0,   # 风速，None值替换为0.0
    } for r in records]

    # 创建DataFrame
    df = pd.DataFrame(rows)
    n = len(df)  # 总数据条数

    # -------------------------------------------------------------------------
    # 第4步：计算切分点
    # -------------------------------------------------------------------------
    # 按70%/15%/15%的比例计算各子集的大小
    n_train = int(0.70 * n)  # 训练集大小（前70%）
    n_val = int(0.15 * n)    # 验证集大小（中间15%）
    n_test = n - n_train - n_val  # 测试集大小（剩余15%，避免取整误差）

    # -------------------------------------------------------------------------
    # 第5步：数据切分
    # -------------------------------------------------------------------------
    # 使用iloc进行位置索引切分，保证数据不重叠
    df_train = df.iloc[:n_train].reset_index(drop=True)  # 训练集：时间最早的部分
    df_val = df.iloc[n_train: n_train + n_val].reset_index(drop=True)  # 验证集：中间部分
    df_test = df.iloc[n_train + n_val:].reset_index(drop=True)  # 测试集：时间最新的部分

    # -------------------------------------------------------------------------
    # 第6步：输出信息
    # -------------------------------------------------------------------------
    # 打印数据切分信息，方便人工确认数据范围是否正确
    print(f"\n[数据加载] 2023年全年数据共 {n} 条")
    print(f"  Train : {len(df_train)} 条  "
          f"({df_train['timestamp'].iloc[0].date()} ~ "
          f"{df_train['timestamp'].iloc[-1].date()})")
    print(f"  Val   : {len(df_val)} 条  "
          f"({df_val['timestamp'].iloc[0].date()} ~ "
          f"{df_val['timestamp'].iloc[-1].date()})")
    print(f"  Test  : {len(df_test)} 条  "
          f"({df_test['timestamp'].iloc[0].date()} ~ "
          f"{df_test['timestamp'].iloc[-1].date()})")

    return df_train, df_val, df_test


def _build_sequences(scaled_values, target_indices):
    """
    ======================================================================
    构建时间序列监督学习样本
    ======================================================================

    【函数功能】
        将连续的时间序列数据转换为监督学习所需的(X, y)样本对。
        使用滑动窗口技术，对于每个时间步i，X是[i:i+INPUT_LEN]的历史数据，
        y是[i+INPUT_LEN]的预测目标。

    【技术细节】
        输入格式：二维数组 (n_samples, n_features)
        输出格式：
            - X: 三维数组 (n_samples, INPUT_LEN, n_features) - 历史窗口数据
            - y: 二维数组 (n_samples, n_targets) - 预测目标值

    【参数说明】
        scaled_values : np.ndarray
            归一化后的特征数据，形状为(时间步数, 特征数)
            例如：(8000, 6)表示8000个时间点，每个时间点6个特征

        target_indices : list
            目标变量在特征数组中的索引位置
            例如：[0, 1, 2]表示取前3个特征作为预测目标

    【返回值】
        tuple: (X, y)
            - X: 输入序列，形状为(样本数, 24, 6)
            - y: 目标值，形状为(样本数, 3)

    【滑动窗口示意】
        假设 INPUT_LEN=24, OUTPUT_LEN=1
        时间轴: [0  1  2  3  ...  23 | 24 | 25 ...]
                  <---- 输入 ---->
                                <-目标->

        样本1: X=[0:24],   y=[24]
        样本2: X=[1:25],   y=[25]
        样本3: X=[2:26],   y=[26]
        ...

    【使用示例】
        >>> target_indices = [0, 1, 2]  # wind_power, pv_power, load
        >>> X, y = _build_sequences(scaled_values, target_indices)
        >>> print(f"X shape: {X.shape}, y shape: {y.shape}")
    """
    X, y = [], []  # 初始化样本列表

    # 计算可生成的样本数量
    # 总时间步数 - 输入长度 - 输出长度 + 1 = 最大起始位置数
    for i in range(len(scaled_values) - INPUT_LEN - OUTPUT_LEN + 1):
        # -------------------------------------------------------------------------
        # 提取输入序列 X
        # -------------------------------------------------------------------------
        # 从位置i开始，提取INPUT_LEN个时间步的所有特征
        # 形状: (INPUT_LEN, n_features)
        X.append(scaled_values[i: i + INPUT_LEN])

        # -------------------------------------------------------------------------
        # 提取目标值 y
        # -------------------------------------------------------------------------
        # 从位置i+INPUT_LEN开始，提取OUTPUT_LEN个时间步的目标变量
        # 只取target_indices指定的列
        # 形状: (OUTPUT_LEN, n_targets)
        y.append(scaled_values[i + INPUT_LEN: i + INPUT_LEN + OUTPUT_LEN,
                               target_indices])

    # -------------------------------------------------------------------------
    # 转换为NumPy数组并指定数据类型
    # -------------------------------------------------------------------------
    # X: (n_samples, INPUT_LEN, n_features)
    X = np.array(X, dtype=np.float32)

    # y: (n_samples, n_targets)
    # reshape(-1, -1)将形状展平为二维数组
    y = np.array(y, dtype=np.float32).reshape(len(X), -1)

    return X, y


def train_tft_model(df_train, df_val, df_test):
    """
    ======================================================================
    TFT模型训练主函数
    ======================================================================

    【函数功能】
        完整的模型训练流程，包括：
        1. 数据预处理（缺失值处理、异常值修复、归一化）
        2. 模型初始化（创建TFT模型实例）
        3. 训练循环（正向传播、损失计算、反向传播、参数更新）
        4. 早停机制（防止过拟合）
        5. 模型保存（保存最优权重）

    【参数说明】
        df_train : pd.DataFrame
            训练数据集，包含FEATURES中的所有特征列和timestamp列

        df_val : pd.DataFrame
            验证数据集，用于在训练过程中评估模型性能
            【重要】验证集不能用于训练，只能用于评估

        df_test : pd.DataFrame
            测试数据集，用于最终评估模型性能
            【重要】测试集在训练过程中完全不可见

    【返回值】
        tuple: (model, train_history, test_metrics)
            - model: 训练好的PyTorch模型
            - train_history: 训练历史记录（包含每个epoch的损失值）
            - test_metrics: 测试集评估指标（目前返回None）

    【训练流程图】
        ┌─────────────────────────────────────────────────────────────┐
        │                    开始训练                                  │
        └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────────────────────────┐
        │ 1. 数据预处理                                               │
        │    - 缺失值处理（样条插值）                                   │
        │    - 异常值修复（中位数替换）                                 │
        │    - 归一化（MinMaxScaler，范围0-1）                         │
        └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────────────────────────┐
        │ 2. 序列样本构建                                              │
        │    - 滑动窗口切分（窗口大小24小时）                            │
        │    - 生成(X, y)样本对                                        │
        └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────────────────────────┐
        │ 3. 模型初始化                                              │
        │    - 创建ImprovedTFT模型实例                                 │
        │    - 选择Adam优化器                                         │
        │    - 设置ReduceLROnPlateau学习率调度器                       │
        └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────────────────────────┐
        │ 4. 训练循环（最多100个epoch）                                 │
        │    ┌─────────────────────────────────────────────────────┐  │
        │    │ for each epoch:                                     │  │
        │    │     # 训练阶段                                       │  │
        │    │     for each batch:                                 │  │
        │    │         前向传播 → 计算损失 → 反向传播 → 更新参数     │  │
        │    │                                                     │  │
        │    │     # 验证阶段                                       │  │
        │    │     计算验证集损失                                    │  │
        │    │                                                     │  │
        │    │     # 早停检查                                       │  │
        │    │     if 验证损失连续10个epoch未改善:                   │  │
        │    │         停止训练                                      │  │
        │    └─────────────────────────────────────────────────────┘  │
        └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────────────────────────┐
        │ 5. 保存最优模型                                             │
        │    - 加载验证集上表现最好的模型权重                           │
        │    - 保存到 backend/models_saved/tft.pth                     │
        └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────────────────────────┐
        │                    训练完成                                  │
        └─────────────────────────────────────────────────────────────┘
    """
    # ==========================================================================
    # 第1步：设备选择
    # ==========================================================================
    # 自动检测并选择计算设备
    # 优先使用NVIDIA GPU（通过CUDA），如果不可用则使用CPU
    # PyTorch的张量运算会在指定的设备上执行
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"设备: {device}")

    # ==========================================================================
    # 第2步：数据预处理
    # ==========================================================================
    # 创建数据预处理器实例
    # DataPreprocessor提供一站式数据清洗和归一化功能
    preprocessor = DataPreprocessor()

    # -------------------------------------------------------------------------
    # 2.1 处理训练集
    # -------------------------------------------------------------------------
    # 复制特征列，避免修改原始数据
    train_feat = df_train[FEATURES].copy()

    # 步骤1：处理缺失值
    # 使用样条插值方法填补缺失值，适合非线性数据
    train_feat = preprocessor.handle_missing(train_feat, method='spline')

    # 步骤2：检测并修复异常值
    # 使用IQR方法检测异常值，修复时使用中位数替换
    train_feat = preprocessor.fix_outliers(train_feat, FEATURES, method='median')

    # -------------------------------------------------------------------------
    # 2.2 归一化处理
    # -------------------------------------------------------------------------
    # 将特征值缩放到[0, 1]区间
    # fit=True表示基于当前数据拟合归一化参数（计算min和max）
    # 归一化器会被保存到文件，后续用于验证集和测试集的归一化
    print("  [Scaler] 基于训练集重新拟合MinMaxScaler...")
    scaled_train = preprocessor.normalize(train_feat, fit=True)

    # 显示归一化参数，方便人工检查数据范围是否合理
    sc = preprocessor.scaler
    for feat, lo, hi in zip(sc.feature_names_in_, sc.data_min_, sc.data_max_):
        print(f"    {feat:15s}: [{lo:.3f}, {hi:.3f}]")

    # -------------------------------------------------------------------------
    # 2.3 定义验证集/测试集的归一化函数
    # -------------------------------------------------------------------------
    # 注意：验证集和测试集必须使用训练集拟合的归一化参数
    # 不能在验证集或测试集上重新拟合归一化器（否则会数据泄露）
    def _scale(df_seg):
        """
        对单个数据段进行预处理和归一化

        参数:
            df_seg: pd.DataFrame，要处理的数据段

        返回:
            pd.DataFrame: 归一化后的数据
        """
        # 处理缺失值
        feat = preprocessor.handle_missing(df_seg[FEATURES].copy(), method='spline')
        # 修复异常值
        feat = preprocessor.fix_outliers(feat, FEATURES, method='median')
        # 归一化（fit=False，使用预训练的归一化器）
        return preprocessor.normalize(feat, fit=False)

    # 对验证集进行预处理
    scaled_val = _scale(df_val)

    # ==========================================================================
    # 第3步：构建序列样本
    # ==========================================================================
    # 确定目标变量在特征列表中的索引位置
    # 例如：FEATURES=['wind_power','pv_power','load','temperature','irradiance','wind_speed']
    #       TARGETS=['wind_power','pv_power','load']
    #       target_indices=[0, 1, 2]
    target_indices = [FEATURES.index(col) for col in TARGETS]

    # 构建监督学习样本
    # 输入X: (n_samples, 24, 6) - 24小时历史，6个特征
    # 输出y: (n_samples, 3) - 3个目标变量的预测值
    X_tr, y_tr = _build_sequences(scaled_train.values, target_indices)
    X_vl, y_vl = _build_sequences(scaled_val.values, target_indices)

    # 校验样本数量
    if len(X_tr) == 0:
        raise ValueError(
            f"训练样本不足！需要至少 {INPUT_LEN + OUTPUT_LEN} 条数据，"
            f"当前只有 {len(scaled_train)} 条"
        )

    # ==========================================================================
    # 第4步：创建数据加载器
    # ==========================================================================
    # DataLoader负责批量数据加载和并行处理
    # batch_size=32: 每次迭代处理32个样本
    # shuffle=True: 训练时打乱数据顺序，增加随机性
    train_loader = DataLoader(
        TensorDataset(torch.tensor(X_tr), torch.tensor(y_tr)),
        batch_size=32,
        shuffle=True  # 训练集需要打乱，验证集不需要
    )

    # 验证集的数据加载器
    # 注意：验证集不需要shuffle，因为我们需要按顺序评估
    val_loader = DataLoader(
        TensorDataset(torch.tensor(X_vl), torch.tensor(y_vl)),
        batch_size=32
    )

    # ==========================================================================
    # 第5步：模型初始化
    # ==========================================================================
    model_type = 'tft'  # 模型类型标识符
    print(f"\n[模型初始化] {model_type}")

    # 通过模型注册表创建TFT模型实例
    # 参数说明：
    #   - len(FEATURES)=6: 输入特征维度
    #   - len(TARGETS)*OUTPUT_LEN=3*1=3: 输出维度（3个目标变量）
    model = get_model(
        model_type, len(FEATURES), len(TARGETS) * OUTPUT_LEN
    ).to(device)  # 将模型参数和缓冲区移动到指定设备

    # 计算并打印模型参数量
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  参数量: {n_params:,}  |  训练样本: {len(X_tr)}  |  "
          f"验证样本: {len(X_vl)}  |  设备: {device}")

    # ==========================================================================
    # 第6步：设置训练参数
    # ==========================================================================
    # 损失函数：均方误差损失（MSE）
    # 适用于回归任务，对大误差惩罚更重
    criterion = nn.MSELoss()

    # 优化器：Adam
    # Adam是深度学习中最常用的优化器之一，自动调整学习率
    # lr=0.001: 初始学习率，控制参数更新的步长
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # 学习率调度器：ReduceLROnPlateau
    # 当验证集损失停止改善时，自动降低学习率
    # mode='min': 监控验证损失，损失不下降时降低学习率
    # patience=5: 连续5个epoch没有改善才降低学习率
    # factor=0.5: 学习率降低为原来的一半
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', patience=5, factor=0.5
    )

    # ==========================================================================
    # 第7步：设置模型保存路径
    # ==========================================================================
    # 模型权重保存目录
    model_dir = os.path.join(
        os.path.dirname(__file__),  # 当前脚本所在目录
        'models_saved'  # 子目录名
    )

    # 确保目录存在（如果不存在则创建）
    os.makedirs(model_dir, exist_ok=True)

    # 完整的模型权重文件路径
    save_path = os.path.join(model_dir, f'{model_type}.pth')

    # ==========================================================================
    # 第8步：初始化训练状态变量
    # ==========================================================================
    best_val_loss = float('inf')     # 最佳验证损失，初始化为正无穷
    patience_counter = 0             # 早停计数器，记录连续未改善的epoch数
    train_history = {                # 训练历史记录
        'train_loss': [],            # 每个epoch的训练损失
        'val_loss': []               # 每个epoch的验证损失
    }

    # ==========================================================================
    # 第9步：训练循环
    # ==========================================================================
    print("\n[开始训练]")
    for epoch in range(100):  # 最多训练100个epoch
        # -------------------------------------------------------------------------
        # 9.1 训练阶段
        # -------------------------------------------------------------------------
        model.train()  # 设置模型为训练模式（启用dropout和batch normalization的训练行为）
        tloss = 0.0    # 累积训练损失

        for xb, yb in train_loader:  # 遍历每个batch
            # 将数据移动到计算设备
            xb, yb = xb.to(device), yb.to(device)

            # 梯度清零（防止梯度累积）
            optimizer.zero_grad()

            try:
                # 前向传播：通过模型计算预测值
                output = model(xb)

                # 计算预测值与真实值之间的损失
                loss = criterion(output, yb)

                # 反向传播：计算损失相对于参数的梯度
                loss.backward()

                # 使用梯度更新模型参数
                optimizer.step()

                # 累积当前batch的损失
                tloss += loss.item()
            except Exception as e:
                # 捕获训练过程中的异常，打印错误信息并返回
                print(f"训练错误: {e}")
                import traceback
                traceback.print_exc()
                return None, None, None

        # 计算平均训练损失
        avg_t = tloss / max(len(train_loader), 1)

        # -------------------------------------------------------------------------
        # 9.2 验证阶段
        # -------------------------------------------------------------------------
        model.eval()  # 设置模型为评估模式（禁用dropout，使用整体统计信息）
        vloss = 0.0   # 累积验证损失

        with torch.no_grad():  # 禁用梯度计算，减少内存占用
            for xb, yb in val_loader:  # 遍历验证集的每个batch
                # 将数据移动到计算设备
                xb, yb = xb.to(device), yb.to(device)

                try:
                    # 前向传播：计算预测值
                    output = model(xb)

                    # 计算验证损失
                    vloss += criterion(output, yb).item()
                except Exception as e:
                    # 捕获验证过程中的异常
                    print(f"验证错误: {e}")
                    import traceback
                    traceback.print_exc()
                    return None, None, None

        # 计算平均验证损失
        avg_v = vloss / max(len(val_loader), 1)

        # 更新学习率（如果验证损失没有改善，学习率会降低）
        scheduler.step(avg_v)

        # 记录训练历史
        train_history['train_loss'].append(avg_t)
        train_history['val_loss'].append(avg_v)

        # -------------------------------------------------------------------------
        # 9.3 日志输出
        # -------------------------------------------------------------------------
        # 每10个epoch打印一次训练状态
        if epoch % 10 == 0:
            print(f"  Epoch {epoch:3d}: train={avg_t:.6f}  val={avg_v:.6f}")

        # -------------------------------------------------------------------------
        # 9.4 早停检查
        # -------------------------------------------------------------------------
        if avg_v < best_val_loss:
            # 如果当前验证损失优于历史最佳
            best_val_loss = avg_v          # 更新最佳验证损失
            patience_counter = 0            # 重置早停计数器

            # 保存当前最优模型权重
            torch.save(model.state_dict(), save_path)
        else:
            # 如果验证损失没有改善
            patience_counter += 1           # 早停计数器加1

            # 连续10个epoch没有改善，触发早停
            if patience_counter >= 10:
                print(f"  早停 @ epoch {epoch}  (最佳验证损失={best_val_loss:.6f})")
                break  # 退出训练循环

    # ==========================================================================
    # 第10步：加载并返回最优模型
    # ==========================================================================
    # 将最优模型权重加载回模型
    try:
        state = torch.load(save_path, map_location=device, weights_only=True)
    except TypeError:
        # 兼容旧版PyTorch（不支持weights_only参数）
        state = torch.load(save_path, map_location=device)

    model.load_state_dict(state)  # 将最优权重加载到模型
    print(f"  已保存最优权重: {save_path}")

    return model, train_history, None


# ================================================================================
# 程序入口
# ================================================================================

if __name__ == '__main__':
    """
    主程序入口

    当直接运行此脚本时（而非被其他模块导入时），执行以下操作：
    1. 创建Flask应用实例
    2. 从数据库加载并分割数据
    3. 训练TFT模型
    4. 输出训练结果
    """
    # 第1步：创建Flask应用实例
    app = create_app()

    # 第2步：从数据库加载训练数据
    df_train, df_val, df_test = load_split_from_database(app)

    # 第3步：训练TFT模型
    model, history, metrics = train_tft_model(df_train, df_val, df_test)

    # 第4步：输出训练结果
    if model:
        print("\nTFT模型训练成功！")
        print(f"模型已保存至: backend/models_saved/tft.pth")
        print(f"训练历史: {len(history['train_loss'])} 个epoch")
    else:
        print("\nTFT模型训练失败！请检查错误信息。")
