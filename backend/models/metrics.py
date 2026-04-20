"""
公共预测评估指标模块

本模块提供了多种预测评估指标的计算函数，以及基于测试集和数据库的批量评估工具：

- **基础指标**：MAPE（平均绝对百分比误差）、RMSE（均方根误差）、MAE（平均绝对误差）、R2（决定系数）
- **批量评估**：基于 CSV 测试集的滑动窗口评估
- **数据库评估**：基于数据库测试段的滑动窗口评估

所有函数均为纯函数（无随机性），相同输入保证相同输出。
"""

# 导入必要的模块
import os  # 文件路径操作
import numpy as np  # 数值计算
import pandas as pd  # 数据处理

# 测试集 CSV 路径（相对于 backend 目录）
_TEST_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         'data', 'raw', 'test_data.csv')
# 如果从 backend 内部导入，路径需要一级
_TEST_CSV_INNER = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'data', 'raw', 'test_data.csv')

# 目标列定义
TARGET_COLS = ['wind_power', 'pv_power', 'load']  # 需要预测的目标变量
INPUT_LEN   = 24   # 模型输入窗口长度（小时）


# ---------------------------------------------------------------------------
# 基础指标
# ---------------------------------------------------------------------------

def calc_mape(y_true: np.ndarray, y_pred: np.ndarray,
              zero_threshold: float = 0.5) -> float:
    """
    计算平均绝对百分比误差（MAPE）
    
    跳过真实值绝对值 < zero_threshold 的样本，避免除零导致的天文数字。
    
    Args:
        y_true: np.ndarray, 真实值数组
        y_pred: np.ndarray, 预测值数组
        zero_threshold: float, 零值阈值，默认 0.5
    
    Returns:
        float, MAPE 值，单位：%
    """
    y_true = np.asarray(y_true, dtype=float)  # 转换为浮点数数组
    y_pred = np.asarray(y_pred, dtype=float)  # 转换为浮点数数组
    
    # 创建掩码，过滤掉真实值过小的样本
    mask = np.abs(y_true) >= zero_threshold
    
    # 如果没有有效的样本，返回 0.0
    if mask.sum() == 0:
        return 0.0
    
    # 计算 MAPE
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) /
                                 np.abs(y_true[mask]))) * 100)


def calc_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    计算均方根误差（RMSE）
    
    Args:
        y_true: np.ndarray, 真实值数组
        y_pred: np.ndarray, 预测值数组
    
    Returns:
        float, RMSE 值，单位与原始数据相同
    """
    y_true = np.asarray(y_true, dtype=float)  # 转换为浮点数数组
    y_pred = np.asarray(y_pred, dtype=float)  # 转换为浮点数数组
    
    # 计算 RMSE
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def calc_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    计算平均绝对误差（MAE）
    
    Args:
        y_true: np.ndarray, 真实值数组
        y_pred: np.ndarray, 预测值数组
    
    Returns:
        float, MAE 值
    """
    y_true = np.asarray(y_true, dtype=float)  # 转换为浮点数数组
    y_pred = np.asarray(y_pred, dtype=float)  # 转换为浮点数数组
    
    # 计算 MAE
    return float(np.mean(np.abs(y_true - y_pred)))


def calc_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    计算决定系数 R²
    
    越接近 1 表示模型拟合效果越好。
    
    Args:
        y_true: np.ndarray, 真实值数组
        y_pred: np.ndarray, 预测值数组
    
    Returns:
        float, R² 值
    """
    y_true = np.asarray(y_true, dtype=float)  # 转换为浮点数数组
    y_pred = np.asarray(y_pred, dtype=float)  # 转换为浮点数数组
    
    # 计算残差平方和
    ss_res = np.sum((y_true - y_pred) ** 2)
    # 计算总平方和
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    
    # 处理特殊情况
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    
    # 计算 R²
    return float(1 - ss_res / ss_tot)


def compute_all(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    一次性计算所有评估指标
    
    计算 MAPE、RMSE、MAE、R2，并返回一个包含所有指标的字典，值均保留 4 位小数。
    
    Args:
        y_true: np.ndarray, 真实值数组
        y_pred: np.ndarray, 预测值数组
    
    Returns:
        dict, 包含所有评估指标的字典
    """
    return {
        'mape': round(calc_mape(y_true, y_pred), 4),  # 平均绝对百分比误差
        'rmse': round(calc_rmse(y_true, y_pred), 4),  # 均方根误差
        'mae':  round(calc_mae(y_true, y_pred),  4),  # 平均绝对误差
        'r2':   round(calc_r2(y_true, y_pred),   4),  # 决定系数
    }


# ---------------------------------------------------------------------------
# 基于测试集的批量评估
# ---------------------------------------------------------------------------

def _load_test_df() -> pd.DataFrame:
    """
    加载测试集 CSV 文件
    
    自动兼容 backend 内外两种调用路径，尝试多个路径直到找到文件。
    
    Returns:
        pd.DataFrame, 测试集数据框
    
    Raises:
        FileNotFoundError, 如果找不到测试集文件
    """
    for path in (_TEST_CSV_INNER, _TEST_CSV):
        if os.path.exists(path):
            df = pd.read_csv(path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])  # 转换时间戳
            return df
    
    # 如果所有路径都找不到文件，抛出异常
    raise FileNotFoundError(
        f"找不到测试集文件，尝试路径：{_TEST_CSV_INNER}, {_TEST_CSV}"
    )


def evaluate_model_on_testset(predictor, train_csv_path: str = None) -> dict:
    """
    使用滑动窗口在测试集上评估 Predictor 实例的真实性能
    
    评估流程：
    1. 加载训练集末尾 INPUT_LEN 行作为初始上下文
    2. 逐步将测试集样本送入模型，收集预测值与真实值
    3. 对每个目标变量分别计算 MAPE/RMSE/MAE/R2
    4. 计算三个目标变量的综合平均指标
    
    Args:
        predictor: models.predict.Predictor 实例，用于生成预测
        train_csv_path: str, 训练集 CSV 路径（用于提供初始上下文窗口）
            默认自动定位 backend/data/raw/training_data.csv
    
    Returns:
        dict, 评估结果，包含每个目标变量的指标和综合指标
    """
    # 定位训练集路径
    if train_csv_path is None:
        base = os.path.dirname(os.path.dirname(__file__))
        train_csv_path = os.path.join(base, 'data', 'raw', 'training_data.csv')

    # 加载训练集和测试集
    df_train = pd.read_csv(train_csv_path)
    df_train['timestamp'] = pd.to_datetime(df_train['timestamp'])
    df_test = _load_test_df()

    # 构建初始上下文：训练集末尾 INPUT_LEN 行 + 测试集
    context = pd.concat(
        [df_train.tail(INPUT_LEN), df_test],
        ignore_index=True
    )

    # 初始化预测值和真实值存储
    preds   = {col: [] for col in TARGET_COLS}
    actuals = {col: [] for col in TARGET_COLS}

    # 滑动窗口评估
    for i in range(len(df_test)):
        # 提取当前窗口
        window = context.iloc[i: i + INPUT_LEN]
        # 生成预测
        pred = predictor.predict(window)
        # 获取真实值
        actual_row = df_test.iloc[i]

        # 处理每个目标变量
        for col in TARGET_COLS:
            val = pred.get(col, 0.0)
            # 处理不同类型的预测值
            if hasattr(val, 'item'):
                val = val.item()  # 处理张量类型
            elif hasattr(val, 'tolist'):
                lst = val.tolist()  # 处理数组类型
                val = lst[0] if len(lst) == 1 else float(np.mean(lst))
            # 存储预测值和真实值
            preds[col].append(float(val))
            actuals[col].append(float(actual_row[col]))

    # 逐目标计算指标
    per_target = {}
    for col in TARGET_COLS:
        per_target[col] = compute_all(
            np.array(actuals[col]),
            np.array(preds[col])
        )

    # 计算综合平均指标（排除 pv_power 的 MAPE，因夜间零值会导致其偏高）
    mapes = [per_target[c]['mape'] for c in ['wind_power', 'load']]
    rmses = [per_target[c]['rmse'] for c in TARGET_COLS]
    maes  = [per_target[c]['mae']  for c in TARGET_COLS]
    r2s   = [per_target[c]['r2']   for c in TARGET_COLS]

    overall = {
        'mape': round(float(np.mean(mapes)), 4),
        'rmse': round(float(np.mean(rmses)), 4),
        'mae':  round(float(np.mean(maes)),  4),
        'r2':   round(float(np.mean(r2s)),   4),
    }

    # 返回评估结果
    return {
        'per_target': per_target,  # 每个目标变量的指标
        'overall':    overall,     # 综合指标
        'n_samples':  len(df_test),  # 测试样本数量
    }


# ---------------------------------------------------------------------------
# 基于数据库测试段的评估（无泄露，与训练集完全隔离）
# ---------------------------------------------------------------------------

import datetime as _dt  # 导入日期时间模块

# 与 train.py 中 70/15/15 切分一致的测试段时间范围
# 2023 年全年 8737 条：前 70%=6115 train，中 15%=1310 val，后 15%=1312 test
# test 段约为 2023-11-07 ~ 2023-12-31
_DB_TEST_START = _dt.datetime(2023, 11, 7)  # 测试段开始时间
_DB_TEST_END   = _dt.datetime(2024, 1, 1)    # 测试段结束时间（不含）
_DB_CTX_BEFORE = _dt.datetime(2023, 11, 7)   # 上下文获取时间点


def evaluate_model_on_db_testset(predictor, app) -> dict:
    """
    从数据库读取独立测试段进行评估
    
    从数据库读取测试段（约 2023-11-07 ~ 2023-12-31，~1312 条），
    做滑窗单步预测评估，返回与 evaluate_model_on_testset() 完全相同格式的结果。
    
    与 evaluate_model_on_testset() 的关键区别：
    - 测试数据来自数据库而非 CSV 文件
    - 测试段严格在训练集（2023-01~09）和验证集（2023-09~11）之后
    - 无数据泄露
    
    Args:
        predictor: models.predict.Predictor 实例，用于生成预测
        app: Flask app 实例（用于访问数据库）
    
    Returns:
        dict, 评估结果，包含每个目标变量的指标和综合指标
    """
    from models.database import NewEnergyData  # 导入数据库模型

    with app.app_context():
        # 查询测试段记录
        test_records = (
            NewEnergyData.query
            .filter(
                NewEnergyData.timestamp >= _DB_TEST_START,
                NewEnergyData.timestamp <  _DB_TEST_END,
            )
            .order_by(NewEnergyData.timestamp.asc())
            .all()
        )
        
        # 查询上下文记录：测试段开始前最后 INPUT_LEN 条
        ctx_records = (
            NewEnergyData.query
            .filter(NewEnergyData.timestamp < _DB_CTX_BEFORE)
            .order_by(NewEnergyData.timestamp.desc())
            .limit(INPUT_LEN)
            .all()
        )

    # 检查测试数据是否存在
    if not test_records:
        raise ValueError(
            f"数据库中没有测试段数据 ({_DB_TEST_START.date()} ~ "
            f"{_DB_TEST_END.date()})，请先确认训练数据已导入"
        )
    
    # 检查上下文数据是否足够
    if len(ctx_records) < INPUT_LEN:
        raise ValueError(
            f"数据库中上下文数据不足，需要 {INPUT_LEN} 条，"
            f"实际 {len(ctx_records)} 条"
        )

    # 定义需要的列
    _cols = ['timestamp', 'wind_power', 'pv_power', 'load',
             'temperature', 'irradiance', 'wind_speed']

    # 辅助函数：将数据库记录转换为字典
    def _to_row(r):
        return {
            'timestamp':   r.timestamp,
            'wind_power':  r.wind_power  or 0.0,  # 处理空值
            'pv_power':    r.pv_power    or 0.0,  # 处理空值
            'load':        r.load        or 0.0,  # 处理空值
            'temperature': r.temperature or 0.0,  # 处理空值
            'irradiance':  r.irradiance  or 0.0,  # 处理空值
            'wind_speed':  r.wind_speed  or 0.0,  # 处理空值
        }

    # 上下文按时间升序排列（query 结果是倒序，需要翻转）
    df_ctx  = pd.DataFrame([_to_row(r) for r in reversed(ctx_records)])
    df_test = pd.DataFrame([_to_row(r) for r in test_records])

    # 拼接：上下文 + 测试段，用于滑窗
    context = pd.concat([df_ctx, df_test], ignore_index=True)

    # 初始化预测值和真实值存储
    preds   = {col: [] for col in TARGET_COLS}
    actuals = {col: [] for col in TARGET_COLS}

    # 滑动窗口评估
    for i in range(len(df_test)):
        # 提取当前窗口
        window = context.iloc[i: i + INPUT_LEN]
        # 生成预测
        pred = predictor.predict(window)
        # 获取真实值
        actual_row = df_test.iloc[i]

        # 处理每个目标变量
        for col in TARGET_COLS:
            val = pred.get(col, 0.0)
            # 处理不同类型的预测值
            if hasattr(val, 'item'):
                val = val.item()  # 处理张量类型
            elif hasattr(val, 'tolist'):
                lst = val.tolist()  # 处理数组类型
                val = lst[0] if len(lst) == 1 else float(np.mean(lst))
            # 存储预测值和真实值
            preds[col].append(float(val))
            actuals[col].append(float(actual_row[col]))

    # 逐目标计算指标
    per_target = {}
    for col in TARGET_COLS:
        per_target[col] = compute_all(
            np.array(actuals[col]),
            np.array(preds[col])
        )

    # 计算综合平均指标（排除 pv_power 的 MAPE）
    mapes = [per_target[c]['mape'] for c in ['wind_power', 'load']]
    rmses = [per_target[c]['rmse'] for c in TARGET_COLS]
    maes  = [per_target[c]['mae']  for c in TARGET_COLS]
    r2s   = [per_target[c]['r2']   for c in TARGET_COLS]

    overall = {
        'mape': round(float(np.mean(mapes)), 4),
        'rmse': round(float(np.mean(rmses)), 4),
        'mae':  round(float(np.mean(maes)),  4),
        'r2':   round(float(np.mean(r2s)),   4),
    }

    # 返回评估结果
    return {
        'per_target': per_target,  # 每个目标变量的指标
        'overall':    overall,     # 综合指标
        'n_samples':  len(df_test),  # 测试样本数量
        'test_range': f"{_DB_TEST_START.date()} ~ {(_DB_TEST_END - _dt.timedelta(days=1)).date()}",  # 测试时间范围
        'source':     'database',  # 数据来源
    }
