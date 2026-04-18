from flask import Blueprint, request, jsonify, current_app
from models.database import db, PredictResult, StrategyConfig, NewEnergyData
from optimization.solver import solve_dispatch
from routes.predict import (
    _build_recent_data_with_padding, get_predictor,
    serialize_prediction_data, _get_model_metrics
)
from models.metrics import evaluate_model_on_testset
import numpy as np
from datetime import datetime, timedelta
import datetime as _dt
import pandas as pd
import time

analysis_bp = Blueprint('analysis', __name__)


def _to_scalar(v):
    """将 numpy 标量/单元素数组统一转为 Python float。"""
    if hasattr(v, 'item'):
        return v.item()
    if hasattr(v, 'tolist'):
        lst = v.tolist()
        return lst[0] if len(lst) == 1 else float(np.mean(lst))
    return float(v)


def _select_comparison_window():
    """
    自动选择一段"白天有风"的 24 小时窗口用于预测 vs 真实值对比。

    策略：在测试集（2023-11-07~12-31）中，寻找白天（09:00 起步）
    且风电均值较高（> 5 MW）的一天，保证曲线在图表中清晰可见。
    返回该段的起始时间，默认回退到 2023-11-15 09:00。
    """
    # 遍历测试集中每天 09:00 起始的 24 步，找风电均值最高的一段
    test_dates = [_dt.datetime(2023, 11, 7) + _dt.timedelta(days=d) for d in range(55)]
    best_start = _dt.datetime(2023, 11, 15, 9, 0)   # 默认值
    best_mean  = -1

    for d in test_dates:
        start = d.replace(hour=9, minute=0, second=0)
        end   = start + _dt.timedelta(hours=24)
        rows = (
            NewEnergyData.query
            .filter(
                NewEnergyData.timestamp >= start,
                NewEnergyData.timestamp <  end,
            )
            .with_entities(NewEnergyData.wind_power)
            .limit(24).all()
        )
        if len(rows) >= 20:
            mean_wind = sum((r.wind_power or 0) for r in rows) / len(rows)
            if mean_wind > best_mean:
                best_mean  = mean_wind
                best_start = start

    return best_start


def _get_comparison_data(predictor, n_steps=24):
    """
    统一预测 + 真实值接口。

    自动选取一段白天风电较活跃的 24 小时窗口，
    用该段 **之前** 的 24 条数据作为模型输入，
    预测这 24 步，同时取该段的真实值。

    返回：
    {
        'ground_truth': {'wind_power': [...], 'pv_power': [...], 'load': [...], 'timestamps': [...]},
        'predictions':  {'wind_power': [...], 'pv_power': [...], 'load': [...]},
        'window_start': '2023-11-15 09:00',
    }
    """
    window_start = _select_comparison_window()
    window_end   = window_start + _dt.timedelta(hours=n_steps)
    ctx_end      = window_start   # 上下文结束 = 目标段开始

    # 1. 取该段之前的 24 条作为模型输入上下文
    ctx_rows = (
        NewEnergyData.query
        .filter(NewEnergyData.timestamp < ctx_end)
        .order_by(NewEnergyData.timestamp.desc())
        .limit(24)
        .all()
    )
    ctx_rows = list(reversed(ctx_rows))

    if len(ctx_rows) < 24:
        return None

    ctx_df = pd.DataFrame([{
        'timestamp':   r.timestamp,
        'wind_power':  r.wind_power  or 0.0,
        'pv_power':    r.pv_power    or 0.0,
        'load':        r.load        or 0.0,
        'temperature': r.temperature or 0.0,
        'irradiance':  r.irradiance  or 0.0,
        'wind_speed':  r.wind_speed  or 0.0,
    } for r in ctx_rows])

    # 2. 取该段的真实值
    gt_rows = (
        NewEnergyData.query
        .filter(
            NewEnergyData.timestamp >= window_start,
            NewEnergyData.timestamp <  window_end,
        )
        .order_by(NewEnergyData.timestamp.asc())
        .limit(n_steps)
        .all()
    )

    if not gt_rows:
        return None

    ground_truth = {
        'wind_power': [round(float(r.wind_power or 0), 3) for r in gt_rows],
        'pv_power':   [round(float(r.pv_power   or 0), 3) for r in gt_rows],
        'load':       [round(float(r.load        or 0), 3) for r in gt_rows],
        'timestamps': [r.timestamp.strftime('%m-%d %H:%M') for r in gt_rows],
    }

    # 3. 用上下文逐步预测 n_steps 步
    predictions = {'wind_power': [], 'pv_power': [], 'load': []}
    current_data = ctx_df.copy()

    for step in range(n_steps):
        pred = predictor.predict(current_data)
        for key in predictions:
            predictions[key].append(round(_to_scalar(pred[key]), 3))
        next_ts  = current_data.iloc[-1]['timestamp'] + timedelta(hours=1)
        next_row = {
            'timestamp':   next_ts,
            'wind_power':  predictions['wind_power'][-1],
            'pv_power':    predictions['pv_power'][-1],
            'load':        predictions['load'][-1],
            'temperature': current_data.iloc[-1]['temperature'],
            'irradiance':  current_data.iloc[-1]['irradiance'],
            'wind_speed':  current_data.iloc[-1]['wind_speed'],
        }
        current_data = pd.concat(
            [current_data.iloc[1:], pd.DataFrame([next_row])],
            ignore_index=True
        )

    return {
        'ground_truth':  ground_truth,
        'predictions':   predictions,
        'window_start':  window_start.strftime('%Y-%m-%d %H:%M'),
    }


@analysis_bp.route('/api/analysis/model_compare', methods=['POST'])
def model_compare():
    """
    比较多个预测模型在同一测试片段上的预测序列，并附带真实值用于对比展示。

    请求参数:
        {"models": ["attention_lstm", "cnn_lstm", ...]}

    返回:
        ground_truth  : 测试集真实值 (24步，2023-11-07 起) + 时间标签
        results[model]: predictions (对同一片段的逐步预测，真正配对)
                        metrics     (完整测试集 1312 条的真实指标)
    """
    try:
        data = request.json or {}
        model_names = data.get('models', ['attention_lstm'])
        n_steps = 24

        # 第一个模型用来确定对比窗口和真实值（所有模型复用同一窗口）
        first_predictor = get_predictor(model_names[0])
        comparison = _get_comparison_data(first_predictor, n_steps)

        if comparison is None:
            return jsonify({'code': 400, 'message': '数据库测试集数据不足，无法生成对比'})

        ground_truth  = comparison['ground_truth']
        window_start  = comparison['window_start']

        results = {}

        # 第一个模型的预测已在 comparison 里算好，其余模型复用同一输入窗口
        for idx, model_type in enumerate(model_names):
            predictor_instance = get_predictor(model_type)

            if idx == 0:
                predictions = comparison['predictions']
            else:
                # 其余模型在同一窗口上重新预测（保证公平对比）
                comp = _get_comparison_data(predictor_instance, n_steps)
                predictions = comp['predictions'] if comp else comparison['predictions']

            # 在完整测试集（1312条）上的真实指标（带缓存）
            m = _get_model_metrics(model_type)
            metrics = {
                'mape':           m.get('mape'),
                'rmse':           m.get('rmse'),
                'mae':            m.get('mae'),
                'r2':             m.get('r2'),
                'model_accuracy': m.get('model_accuracy'),
                'per_target':     m.get('per_target', {}),
                'n_samples':      m.get('n_samples', 0),
                'data_source':    f'数据库测试集 2023-11-07~12-31 (1312条)，展示窗口: {window_start}',
            }

            results[model_type] = {
                'predictions': serialize_prediction_data(predictions),
                'metrics':     metrics,
            }

        return jsonify({
            'code': 200,
            'data': {
                'results':      results,
                'ground_truth': ground_truth,
                'window_start': window_start,
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'模型比较失败: {str(e)}'})


@analysis_bp.route('/api/analysis/algorithm_compare', methods=['POST'])
def algorithm_compare():
    """
    比较不同优化算法（PSO，AWPSO，GA）对相同预测数据的调度结果
    请求参数: {"algorithms": ["awpso", "pso", "ga"], "date": "2023-01-01"}
    """
    try:
        data = request.json or {}
        algorithms = data.get('algorithms', ['awpso', 'pso', 'ga'])
        
        latest_prediction = PredictResult.query.filter_by(
            predict_type='multi',
            horizon=24
        ).order_by(PredictResult.created_at.desc()).first()
        
        if not latest_prediction:
            return jsonify({'code': 400, 'message': '没有可用的预测数据，请先执行预测'})
            
        forecasts = latest_prediction.data
        
        strategy = StrategyConfig.query.first()
        dr_ratio = 0.2
        if strategy:
            price_map = {
                'extreme_peak': strategy.extreme_peak_price,
                'peak': strategy.peak_price,
                'flat': strategy.flat_price,
                'valley': strategy.valley_price,
                'deep_valley': strategy.deep_valley_price
            }
            tou_config = strategy.tou_config
            price_buy = [price_map.get(tou_config.get(str(h), 'flat'), strategy.flat_price) for h in range(24)]
            dr_ratio = strategy.dr_ratio
        else:
            price_buy = [500] * 24
            
        price_sell = [300] * 24
        ess_params = data.get('ess_params', {})
        
        results = {}
        for algo in algorithms:
            t0 = time.time()
            res = solve_dispatch(forecasts, price_buy, price_sell, ess_params, dr_ratio=dr_ratio, algorithm=algo)
            t1 = time.time()
            
            results[algo] = {
                'charge_plan': res['charge_plan'],
                'discharge_plan': res['discharge_plan'],
                'soc_curve': res['soc_curve'],
                'abandon_rate': res['abandon_rate'],
                'total_cost': res['total_cost'],
                'fitness_history': res.get('fitness_history', []),
                'time_cost': round(t1 - t0, 3)
            }
            
        return jsonify({
            'code': 200,
            'data': results
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'算法比较失败: {str(e)}'})
