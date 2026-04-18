"""
公共预测评估指标模块
提供 MAPE / RMSE / MAE / R2 计算函数，以及基于 CSV 测试集的
滑动窗口批量评估工具 evaluate_model_on_testset()。

所有函数均为纯函数（无随机性），相同输入保证相同输出。
"""

import os
import numpy as np
import pandas as pd

# 测试集 CSV 路径（相对于 backend 目录）
_TEST_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         'backend', 'data', 'raw', 'test_data.csv')
# 如果从 backend 内部导入，路径需要一级
_TEST_CSV_INNER = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'data', 'raw', 'test_data.csv')

TARGET_COLS = ['wind_power', 'pv_power', 'load']
INPUT_LEN   = 24   # 模型输入窗口长度（小时）


# ---------------------------------------------------------------------------
# 基础指标
# ---------------------------------------------------------------------------

def calc_mape(y_true: np.ndarray, y_pred: np.ndarray,
              zero_threshold: float = 0.5) -> float:
    """
    平均绝对百分比误差（MAPE）。
    跳过真实值绝对值 < zero_threshold 的样本，避免除零导致的天文数字。
    返回值单位：%
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.abs(y_true) >= zero_threshold
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) /
                                 np.abs(y_true[mask]))) * 100)


def calc_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """均方根误差（RMSE），单位与原始数据相同。"""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def calc_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """平均绝对误差（MAE）。"""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def calc_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """决定系数 R²，越接近 1 越好。"""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    return float(1 - ss_res / ss_tot)


def compute_all(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """一次性计算 MAPE/RMSE/MAE/R2，返回字典，值均保留 4 位小数。"""
    return {
        'mape': round(calc_mape(y_true, y_pred), 4),
        'rmse': round(calc_rmse(y_true, y_pred), 4),
        'mae':  round(calc_mae(y_true, y_pred),  4),
        'r2':   round(calc_r2(y_true, y_pred),   4),
    }


# ---------------------------------------------------------------------------
# 基于测试集的批量评估
# ---------------------------------------------------------------------------

def _load_test_df() -> pd.DataFrame:
    """加载测试集 CSV，自动兼容 backend 内外两种调用路径。"""
    for path in (_TEST_CSV_INNER, _TEST_CSV):
        if os.path.exists(path):
            df = pd.read_csv(path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
    raise FileNotFoundError(
        f"找不到测试集文件，尝试路径：{_TEST_CSV_INNER}, {_TEST_CSV}"
    )


def evaluate_model_on_testset(predictor, train_csv_path: str = None) -> dict:
    """
    使用滑动窗口在测试集上评估 Predictor 实例的真实性能。

    流程：
      1. 加载训练集末尾 INPUT_LEN 行作为初始上下文
      2. 逐步将测试集样本送入模型，收集预测值与真实值
      3. 对每个目标变量分别计算 MAPE/RMSE/MAE/R2
      4. 计算三个目标变量的综合平均指标

    参数：
      predictor       : models.predict.Predictor 实例
      train_csv_path  : 训练集 CSV 路径（用于提供初始上下文窗口）
                        默认自动定位 backend/data/raw/training_data.csv

    返回示例：
    {
        'per_target': {
            'wind_power': {'mape': 12.3, 'rmse': 3.2, 'mae': 2.1, 'r2': 0.85},
            'pv_power':   {...},
            'load':       {...},
        },
        'overall': {'mape': 10.5, 'rmse': 3.0, 'mae': 2.0, 'r2': 0.87},
        'n_samples': 168
    }
    """
    # 定位训练集
    if train_csv_path is None:
        base = os.path.dirname(os.path.dirname(__file__))
        train_csv_path = os.path.join(base, 'data', 'raw', 'training_data.csv')

    df_train = pd.read_csv(train_csv_path)
    df_train['timestamp'] = pd.to_datetime(df_train['timestamp'])
    df_test = _load_test_df()

    # 初始上下文：训练集末尾 INPUT_LEN 行
    context = pd.concat(
        [df_train.tail(INPUT_LEN), df_test],
        ignore_index=True
    )

    preds   = {col: [] for col in TARGET_COLS}
    actuals = {col: [] for col in TARGET_COLS}

    for i in range(len(df_test)):
        window = context.iloc[i: i + INPUT_LEN]
        pred = predictor.predict(window)
        actual_row = df_test.iloc[i]

        for col in TARGET_COLS:
            val = pred.get(col, 0.0)
            if hasattr(val, 'item'):
                val = val.item()
            elif hasattr(val, 'tolist'):
                lst = val.tolist()
                val = lst[0] if len(lst) == 1 else float(np.mean(lst))
            preds[col].append(float(val))
            actuals[col].append(float(actual_row[col]))

    # 逐目标计算指标
    per_target = {}
    for col in TARGET_COLS:
        per_target[col] = compute_all(
            np.array(actuals[col]),
            np.array(preds[col])
        )

    # 综合平均（排除 pv_power 的 MAPE，因夜间零值会导致其偏高）
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

    return {
        'per_target': per_target,
        'overall':    overall,
        'n_samples':  len(df_test),
    }


# ---------------------------------------------------------------------------
# 基于数据库测试段的评估（无泄露，与训练集完全隔离）
# ---------------------------------------------------------------------------

import datetime as _dt

# 与 train.py 中 70/15/15 切分一致的测试段时间范围
# 2023 年全年 8737 条：前 70%=6115 train，中 15%=1310 val，后 15%=1312 test
# test 段约为 2023-11-07 ~ 2023-12-31
_DB_TEST_START = _dt.datetime(2023, 11, 7)
_DB_TEST_END   = _dt.datetime(2024, 1, 1)    # 不含
_DB_CTX_BEFORE = _dt.datetime(2023, 11, 7)   # 取此时刻之前最后 INPUT_LEN 条作为上下文


def evaluate_model_on_db_testset(predictor, app) -> dict:
    """
    从数据库读取独立测试段（约 2023-11-07 ~ 2023-12-31，~1312 条），
    做滑窗单步预测评估，返回与 evaluate_model_on_testset() 完全相同格式的 dict。

    与 evaluate_model_on_testset() 的关键区别：
      - 测试数据来自数据库而非 CSV 文件
      - 测试段严格在训练集（2023-01~09）和验证集（2023-09~11）之后
      - 无数据泄露

    参数：
      predictor : models.predict.Predictor 实例
      app       : Flask app 实例（用于访问数据库）

    返回格式：
    {
        'per_target': {
            'wind_power': {'mape': ..., 'rmse': ..., 'mae': ..., 'r2': ...},
            'pv_power':   {...},
            'load':       {...},
        },
        'overall':   {'mape': ..., 'rmse': ..., 'mae': ..., 'r2': ...},
        'n_samples': 1312,
        'test_range': '2023-11-07 ~ 2023-12-31',
        'source': 'database',
    }
    """
    from models.database import NewEnergyData

    with app.app_context():
        # 测试段记录
        test_records = (
            NewEnergyData.query
            .filter(
                NewEnergyData.timestamp >= _DB_TEST_START,
                NewEnergyData.timestamp <  _DB_TEST_END,
            )
            .order_by(NewEnergyData.timestamp.asc())
            .all()
        )
        # 上下文：测试段开始前最后 INPUT_LEN 条
        ctx_records = (
            NewEnergyData.query
            .filter(NewEnergyData.timestamp < _DB_CTX_BEFORE)
            .order_by(NewEnergyData.timestamp.desc())
            .limit(INPUT_LEN)
            .all()
        )

    if not test_records:
        raise ValueError(
            f"数据库中没有测试段数据 ({_DB_TEST_START.date()} ~ "
            f"{_DB_TEST_END.date()})，请先确认训练数据已导入"
        )
    if len(ctx_records) < INPUT_LEN:
        raise ValueError(
            f"数据库中上下文数据不足，需要 {INPUT_LEN} 条，"
            f"实际 {len(ctx_records)} 条"
        )

    _cols = ['timestamp', 'wind_power', 'pv_power', 'load',
             'temperature', 'irradiance', 'wind_speed']

    def _to_row(r):
        return {
            'timestamp':   r.timestamp,
            'wind_power':  r.wind_power  or 0.0,
            'pv_power':    r.pv_power    or 0.0,
            'load':        r.load        or 0.0,
            'temperature': r.temperature or 0.0,
            'irradiance':  r.irradiance  or 0.0,
            'wind_speed':  r.wind_speed  or 0.0,
        }

    # 上下文按时间升序排列（query 结果是倒序，需要翻转）
    df_ctx  = pd.DataFrame([_to_row(r) for r in reversed(ctx_records)])
    df_test = pd.DataFrame([_to_row(r) for r in test_records])

    # 拼接：上下文 + 测试段，用于滑窗
    context = pd.concat([df_ctx, df_test], ignore_index=True)

    preds   = {col: [] for col in TARGET_COLS}
    actuals = {col: [] for col in TARGET_COLS}

    for i in range(len(df_test)):
        window = context.iloc[i: i + INPUT_LEN]
        pred = predictor.predict(window)
        actual_row = df_test.iloc[i]

        for col in TARGET_COLS:
            val = pred.get(col, 0.0)
            if hasattr(val, 'item'):
                val = val.item()
            elif hasattr(val, 'tolist'):
                lst = val.tolist()
                val = lst[0] if len(lst) == 1 else float(np.mean(lst))
            preds[col].append(float(val))
            actuals[col].append(float(actual_row[col]))

    # 逐目标计算指标
    per_target = {}
    for col in TARGET_COLS:
        per_target[col] = compute_all(
            np.array(actuals[col]),
            np.array(preds[col])
        )

    # 综合均值（排除 pv_power 的 MAPE）
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

    return {
        'per_target': per_target,
        'overall':    overall,
        'n_samples':  len(df_test),
        'test_range': f"{_DB_TEST_START.date()} ~ {(_DB_TEST_END - _dt.timedelta(days=1)).date()}",
        'source':     'database',
    }
