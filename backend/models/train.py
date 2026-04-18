#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型训练模块

公开接口：
  train_all_models(app)          -- 一次性训练全部 5 个模型（推荐入口）
  train_model_on_db(...)         -- 训练单个模型
  load_split_from_database(app)  -- 从 DB 加载并按 70/15/15 时间顺序切分数据

兼容性接口（旧版，保留供向后兼容）：
  train_model(data_path, ...)    -- 原始 CSV/数据库训练函数
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

# 确保 backend 目录在 sys.path 中
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from models.model_registry import get_model
from preprocessing.data_utils import DataPreprocessor
from models.database import NewEnergyData

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

ALL_MODEL_TYPES = ['attention_lstm', 'standard_lstm', 'gru', 'cnn_lstm', 'transformer']

FEATURES  = ['wind_power', 'pv_power', 'load', 'temperature', 'irradiance', 'wind_speed']
TARGETS   = ['wind_power', 'pv_power', 'load']
INPUT_LEN  = 24
OUTPUT_LEN = 1

# 只用 2023 年完整连续数据（覆盖率 99.7%，内部无大间隔）
_DB_YEAR_START = datetime.datetime(2023, 1, 1)
_DB_YEAR_END   = datetime.datetime(2024, 1, 1)   # 不含


# ---------------------------------------------------------------------------
# 数据加载与分割
# ---------------------------------------------------------------------------

def load_split_from_database(app):
    """
    从数据库加载 2023 年全年数据，按时间顺序切分为三段。

    切分比例：70% train / 15% val / 15% test
    切分方式：严格按时间先后顺序，确保无数据泄露。

    返回：(df_train, df_val, df_test)，每段均含 FEATURES 列及 timestamp。
    """
    with app.app_context():
        records = (
            NewEnergyData.query
            .filter(
                NewEnergyData.timestamp >= _DB_YEAR_START,
                NewEnergyData.timestamp <  _DB_YEAR_END,
            )
            .order_by(NewEnergyData.timestamp.asc())
            .all()
        )

    if not records:
        raise ValueError("数据库中没有 2023 年训练数据，请先导入数据")

    rows = [{
        'timestamp':   r.timestamp,
        'wind_power':  r.wind_power  or 0.0,
        'pv_power':    r.pv_power    or 0.0,
        'load':        r.load        or 0.0,
        'temperature': r.temperature or 0.0,
        'irradiance':  r.irradiance  or 0.0,
        'wind_speed':  r.wind_speed  or 0.0,
    } for r in records]

    df = pd.DataFrame(rows)
    n  = len(df)

    n_train = int(0.70 * n)
    n_val   = int(0.15 * n)
    n_test  = n - n_train - n_val   # 剩余全部，避免取整丢失

    df_train = df.iloc[:n_train].reset_index(drop=True)
    df_val   = df.iloc[n_train: n_train + n_val].reset_index(drop=True)
    df_test  = df.iloc[n_train + n_val:].reset_index(drop=True)

    print(f"\n[数据加载] 2023 年全年数据共 {n} 条")
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


# ---------------------------------------------------------------------------
# 滑窗样本构造
# ---------------------------------------------------------------------------

def _build_sequences(scaled_values, target_indices):
    """将归一化后的二维数组切成 (X, y) 样本对。"""
    X, y = [], []
    for i in range(len(scaled_values) - INPUT_LEN - OUTPUT_LEN + 1):
        X.append(scaled_values[i: i + INPUT_LEN])
        y.append(scaled_values[i + INPUT_LEN: i + INPUT_LEN + OUTPUT_LEN,
                               target_indices])
    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32).reshape(len(X), -1)
    return X, y


# ---------------------------------------------------------------------------
# 测试集评估（训练内部使用）
# ---------------------------------------------------------------------------

def evaluate_on_test(model, preprocessor, df_context_tail, df_test, device):
    """
    在测试段做滑窗单步预测评估，打印并返回 per_target + overall 指标。

    df_context_tail : val 段末尾 INPUT_LEN 行，作为 test 第一步的初始上下文。
    df_test         : 完整测试段 DataFrame。
    """
    from models.metrics import compute_all

    model.eval()
    preds   = {col: [] for col in TARGETS}
    actuals = {col: [] for col in TARGETS}

    context = pd.concat(
        [df_context_tail[FEATURES], df_test[FEATURES]],
        ignore_index=True
    )

    with torch.no_grad():
        for i in range(len(df_test)):
            window_df = context.iloc[i: i + INPUT_LEN][FEATURES]
            try:
                scaled = preprocessor.normalize(window_df, fit=False)
                inp = torch.tensor(
                    scaled.values, dtype=torch.float32
                ).unsqueeze(0).to(device)
                pred_norm = model(inp).cpu().numpy().flatten()

                pred_vals = {}
                for j, col in enumerate(TARGETS):
                    raw = preprocessor.inverse_transform(pred_norm[j], [col])
                    # inverse_transform 可能返回 ndarray，统一转标量
                    pred_vals[col] = float(
                        raw.flat[0] if hasattr(raw, 'flat') else raw
                    )
            except Exception:
                for col in TARGETS:
                    pred_vals[col] = float(window_df[col].mean())

            actual_row = df_test.iloc[i]
            for col in TARGETS:
                preds[col].append(pred_vals[col])
                actuals[col].append(float(actual_row[col]))

    # 逐目标指标
    per_target = {}
    for col in TARGETS:
        per_target[col] = compute_all(
            np.array(actuals[col]),
            np.array(preds[col])
        )

    # 综合均值（排除 pv_power 的 MAPE——夜间零值导致天文数字）
    mapes = [per_target[c]['mape'] for c in ['wind_power', 'load']]
    rmses = [per_target[c]['rmse'] for c in TARGETS]
    maes  = [per_target[c]['mae']  for c in TARGETS]
    r2s   = [per_target[c]['r2']   for c in TARGETS]

    overall = {
        'mape': round(float(np.mean(mapes)), 4),
        'rmse': round(float(np.mean(rmses)), 4),
        'mae':  round(float(np.mean(maes)),  4),
        'r2':   round(float(np.mean(r2s)),   4),
    }

    print(f"\n  测试集评估 ({len(df_test)} 样本):")
    print(f"  {'目标':12s}  {'MAPE(%)':>8}  {'RMSE':>8}  {'MAE':>8}  {'R2':>8}")
    print(f"  {'-'*52}")
    for col in TARGETS:
        m = per_target[col]
        print(f"  {col:12s}  {m['mape']:8.2f}  {m['rmse']:8.3f}"
              f"  {m['mae']:8.3f}  {m['r2']:8.4f}")
    print(f"  {'overall':12s}  {overall['mape']:8.2f}  {overall['rmse']:8.3f}"
          f"  {overall['mae']:8.3f}  {overall['r2']:8.4f}")

    return {'per_target': per_target, 'overall': overall,
            'n_samples': len(df_test)}


# ---------------------------------------------------------------------------
# 单模型训练
# ---------------------------------------------------------------------------

def train_model_on_db(df_train, df_val, df_test,
                      model_type='attention_lstm',
                      fit_scaler=True,
                      epochs=100,
                      batch_size=32,
                      lr=0.001):
    """
    在给定的 train/val/test 三段上训练并评估单个模型。

    fit_scaler=True  : 用 df_train 重新拟合并保存 scaler.pkl（覆盖旧文件）
    fit_scaler=False : 加载已有 scaler.pkl，复用同一套归一化参数

    返回 (model, train_history, test_metrics)
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # ---- 1. 预处理 ----
    preprocessor = DataPreprocessor()

    train_feat = preprocessor.handle_missing(df_train[FEATURES].copy())
    train_feat = preprocessor.fix_outliers(train_feat, FEATURES)

    if fit_scaler:
        print("  [Scaler] 基于训练集重新拟合 MinMaxScaler（将覆盖 scaler.pkl）...")
        scaled_train = preprocessor.normalize(train_feat, fit=True)
        sc = preprocessor.scaler
        for feat, lo, hi in zip(sc.feature_names_in_,
                                 sc.data_min_, sc.data_max_):
            print(f"    {feat:15s}: [{lo:.3f}, {hi:.3f}]")
    else:
        scaled_train = preprocessor.normalize(train_feat, fit=False)

    def _scale(df_seg):
        feat = preprocessor.handle_missing(df_seg[FEATURES].copy())
        feat = preprocessor.fix_outliers(feat, FEATURES)
        return preprocessor.normalize(feat, fit=False)

    scaled_val = _scale(df_val)

    target_indices = [FEATURES.index(col) for col in TARGETS]
    X_tr, y_tr = _build_sequences(scaled_train.values, target_indices)
    X_vl, y_vl = _build_sequences(scaled_val.values,   target_indices)

    if len(X_tr) == 0:
        raise ValueError(
            f"训练样本不足：需要至少 {INPUT_LEN + OUTPUT_LEN} 条，"
            f"当前 {len(scaled_train)} 条"
        )

    train_loader = DataLoader(
        TensorDataset(torch.tensor(X_tr), torch.tensor(y_tr)),
        batch_size=batch_size, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(torch.tensor(X_vl), torch.tensor(y_vl)),
        batch_size=batch_size
    )

    # ---- 2. 模型初始化 ----
    model = get_model(
        model_type, len(FEATURES), len(TARGETS) * OUTPUT_LEN
    ).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  参数量: {n_params:,}  |  训练: {len(X_tr)} 样本  "
          f"|  验证: {len(X_vl)} 样本  |  设备: {device}")

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', patience=5, factor=0.5
    )

    model_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'models_saved'
    )
    os.makedirs(model_dir, exist_ok=True)
    save_path = os.path.join(model_dir, f'{model_type}.pth')

    best_val_loss    = float('inf')
    patience_counter = 0
    train_history    = {'train_loss': [], 'val_loss': []}

    # ---- 3. 训练循环 ----
    for epoch in range(epochs):
        # train
        model.train()
        tloss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            tloss += loss.item()
        avg_t = tloss / max(len(train_loader), 1)

        # val
        model.eval()
        vloss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                vloss += criterion(model(xb), yb).item()
        avg_v = vloss / max(len(val_loader), 1)

        scheduler.step(avg_v)
        train_history['train_loss'].append(avg_t)
        train_history['val_loss'].append(avg_v)

        if epoch % 10 == 0:
            print(f"  Epoch {epoch:3d}: train={avg_t:.6f}  val={avg_v:.6f}")

        if avg_v < best_val_loss:
            best_val_loss    = avg_v
            patience_counter = 0
            torch.save(model.state_dict(), save_path)
        else:
            patience_counter += 1
            if patience_counter >= 10:
                print(f"  Early stopping @ epoch {epoch}  "
                      f"(best_val={best_val_loss:.6f})")
                break

    # 加载最优权重再做测试集评估
    try:
        state = torch.load(save_path, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(save_path, map_location=device)
    model.load_state_dict(state)
    print(f"  已保存最优权重: {save_path}")

    # val 段末尾 INPUT_LEN 行作为 test 第一步的上下文
    df_ctx = df_val.tail(INPUT_LEN).reset_index(drop=True)
    test_metrics = evaluate_on_test(
        model, preprocessor, df_ctx, df_test, device
    )

    return model, train_history, test_metrics


# ---------------------------------------------------------------------------
# 批量训练全部模型（推荐入口）
# ---------------------------------------------------------------------------

def train_all_models(app, epochs=100, batch_size=32, lr=0.001,
                     model_types=None):
    """
    一次性训练全部（或指定的）预测模型，共享同一个 scaler。

    - 第一个模型 fit_scaler=True（重新拟合并覆盖 scaler.pkl）
    - 后续模型 fit_scaler=False（复用同一套归一化参数）
    - 训练完成后打印 5 个模型的汇总对比表

    返回 {model_type: test_metrics_dict}
    """
    if model_types is None:
        model_types = ALL_MODEL_TYPES

    print("=" * 62)
    print("  新能源储能系统 -- 全模型训练")
    print("=" * 62)

    # 数据只加载和分割一次
    df_train, df_val, df_test = load_split_from_database(app)

    all_results = {}

    for idx, model_type in enumerate(model_types):
        print(f"\n{'--'*31}")
        print(f"  [{idx+1}/{len(model_types)}] {model_type}")
        print(f"{'--'*31}")
        try:
            _, history, metrics = train_model_on_db(
                df_train, df_val, df_test,
                model_type=model_type,
                fit_scaler=(idx == 0),   # 只有第一个模型拟合 scaler
                epochs=epochs,
                batch_size=batch_size,
                lr=lr,
            )
            all_results[model_type] = metrics
        except Exception as e:
            import traceback
            print(f"  [ERROR] {model_type} 训练失败: {e}")
            traceback.print_exc()
            all_results[model_type] = None

    # ---- 汇总对比表 ----
    print(f"\n{'='*62}")
    print("  全模型训练完成！测试集指标汇总：")
    print(f"{'='*62}")
    print(f"  {'模型类型':20s}  {'MAPE(%)':>8}  {'RMSE':>8}  "
          f"{'MAE':>8}  {'R2':>8}")
    print(f"  {'-'*56}")
    for mt in model_types:
        r = all_results.get(mt)
        if r and r.get('overall'):
            o = r['overall']
            print(f"  {mt:20s}  {o['mape']:8.2f}  {o['rmse']:8.3f}"
                  f"  {o['mae']:8.3f}  {o['r2']:8.4f}")
        else:
            print(f"  {mt:20s}  {'失败':>8}")
    print(f"{'='*62}")
    print(f"  测试集: {df_test['timestamp'].iloc[0].date()} ~ "
          f"{df_test['timestamp'].iloc[-1].date()} ({len(df_test)} 条)")
    print("\n  训练完成后请调用以下接口令服务加载新权重（无需重启）：")
    print("  POST http://localhost:5000/api/predict/reload_models")

    return all_results


# ---------------------------------------------------------------------------
# 兼容性保留（旧版 train_model 接口）
# ---------------------------------------------------------------------------

def resolve_data_path(data_path):
    """解析训练数据路径（兼容旧调用）。"""
    if os.path.isabs(data_path) and os.path.exists(data_path):
        return data_path
    cwd = os.path.abspath(data_path)
    if os.path.exists(cwd):
        return cwd
    root = os.path.dirname(os.path.dirname(__file__))
    bp = os.path.join(root, data_path)
    if os.path.exists(bp):
        return bp
    for c in [os.path.join(root, 'data', 'processed', 'train.csv'),
              os.path.join(root, 'data', 'raw', 'training_data.csv')]:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"未找到: {data_path}")


def load_data_from_database(app, limit=None):
    """从数据库获取全量训练数据（兼容旧调用，推荐改用 load_split_from_database）。"""
    with app.app_context():
        q = NewEnergyData.query.order_by(NewEnergyData.timestamp.asc())
        if limit:
            q = q.limit(limit)
        records = q.all()
    if not records:
        raise ValueError("数据库中没有训练数据")
    rows = [{
        'timestamp': r.timestamp, 'wind_power': r.wind_power,
        'pv_power': r.pv_power, 'load': r.load,
        'temperature': r.temperature, 'irradiance': r.irradiance,
        'wind_speed': r.wind_speed,
    } for r in records]
    df = pd.DataFrame(rows)
    print(f"从数据库获取了 {len(df)} 条训练数据")
    return df


def train_model(data_path=None, input_len=24, output_len=1,
                epochs=100, batch_size=32, lr=0.001,
                app=None, model_type='attention_lstm'):
    """
    原始训练函数（兼容旧调用）。
    推荐改用 train_all_models(app) 或 train_model_on_db(...)。
    """
    if data_path and data_path == 'database':
        if app is None:
            raise ValueError("从数据库获取数据需要提供 Flask app 实例")
        df = load_data_from_database(app)
    elif data_path:
        data_path = resolve_data_path(data_path)
        df = pd.read_csv(data_path, parse_dates=['timestamp'])
    else:
        raise ValueError("请提供数据路径或指定使用数据库")

    preprocessor = DataPreprocessor()
    model_df = preprocessor.fix_outliers(
        preprocessor.handle_missing(df[FEATURES].copy()), FEATURES
    )
    scaled_df = preprocessor.normalize(model_df, fit=True)

    target_indices = [FEATURES.index(col) for col in TARGETS]
    values = scaled_df.values
    X, y = [], []
    for i in range(len(values) - input_len - output_len + 1):
        X.append(values[i: i + input_len])
        y.append(values[i + input_len: i + input_len + output_len,
                        target_indices])
    X = np.array(X)
    y = np.array(y).reshape(len(X), -1)

    split = int(0.8 * len(X))
    X_tr, X_vl = X[:split], X[split:]
    y_tr, y_vl = y[:split], y[split:]

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    tr_loader = DataLoader(
        TensorDataset(torch.tensor(X_tr, dtype=torch.float32),
                      torch.tensor(y_tr, dtype=torch.float32)),
        batch_size=batch_size, shuffle=True
    )
    vl_loader = DataLoader(
        TensorDataset(torch.tensor(X_vl, dtype=torch.float32),
                      torch.tensor(y_vl, dtype=torch.float32)),
        batch_size=batch_size
    )

    model = get_model(
        model_type, len(FEATURES), len(TARGETS) * output_len
    ).to(device)
    print(f"使用模型: {model_type}, "
          f"参数量: {sum(p.numel() for p in model.parameters())}")

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, patience=5, factor=0.5
    )

    model_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'models_saved'
    )
    os.makedirs(model_dir, exist_ok=True)

    best_val     = float('inf')
    patience_cnt = 0
    history      = {'train_loss': [], 'val_loss': []}

    for epoch in range(epochs):
        model.train()
        tl = 0.0
        for xb, yb in tr_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            tl += loss.item()
        at = tl / max(len(tr_loader), 1)

        model.eval()
        vl = 0.0
        with torch.no_grad():
            for xb, yb in vl_loader:
                xb, yb = xb.to(device), yb.to(device)
                vl += criterion(model(xb), yb).item()
        av = vl / max(len(vl_loader), 1)
        scheduler.step(av)
        history['train_loss'].append(at)
        history['val_loss'].append(av)

        if av < best_val:
            best_val     = av
            patience_cnt = 0
            torch.save(model.state_dict(),
                       os.path.join(model_dir, f'{model_type}.pth'))
        else:
            patience_cnt += 1
            if patience_cnt >= 10:
                print(f"Early stopping at epoch {epoch}")
                break

        if epoch % 10 == 0:
            print(f"Epoch {epoch}, train={at:.6f}, val={av:.6f}")

    return model, preprocessor, history


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    from app import create_app
    app = create_app()
    train_all_models(app)
