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


def _get_testset_ground_truth(n_steps=24):
    """
    从 DB 测试段（2023-11-07 起的前 n_steps 条）取真实值，
    用于与各模型预测序列配对对比。固定取同一片段保证公平对比。
    """
    test_start = _dt.datetime(2023, 11, 7)
    test_end   = test_start + _dt.timedelta(hours=n_steps)

    rows = (
        NewEnergyData.query
        .filter(
            NewEnergyData.timestamp >= test_start,
            NewEnergyData.timestamp <  test_end,
        )
        .order_by(NewEnergyData.timestamp.asc())
        .limit(n_steps)
        .all()
    )

    if not rows:
        return None

    return {
        'wind_power': [round(float(r.wind_power or 0), 3) for r in rows],
        'pv_power':   [round(float(r.pv_power   or 0), 3) for r in rows],
        'load':       [round(float(r.load        or 0), 3) for r in rows],
        'timestamps': [r.timestamp.strftime('%m-%d %H:%M') for r in rows],
    }


def _get_testset_predictions(predictor, n_steps=24):
    """
    以测试段开始前最后 24 条记录作为上下文，对 2023-11-07 起的
    n_steps 步做逐步预测，与 _get_testset_ground_truth() 形成真正配对。
    """
    context_end = _dt.datetime(2023, 11, 7)

    ctx_rows = (
        NewEnergyData.query
        .filter(NewEnergyData.timestamp < context_end)
        .order_by(NewEnergyData.timestamp.desc())
        .limit(24)
        .all()
    )
    ctx_rows = list(reversed(ctx_rows))   # 时间升序

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

    predictions = {'wind_power': [], 'pv_power': [], 'load': []}
    current_data = ctx_df.copy()

    for step in range(n_steps):
        pred = predictor.predict(current_data)
        for key in predictions:
            predictions[key].append(round(_to_scalar(pred[key]), 3))

        next_ts = current_data.iloc[-1]['timestamp'] + timedelta(hours=1)
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

    return predictions


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

        # ---- 真实值（所有模型共用同一段，保证公平对比）----
        ground_truth = _get_testset_ground_truth(n_steps)

        # 无 DB 测试数据时降级为最新实测数据
        if ground_truth is None:
            recent_data, _ = _build_recent_data_with_padding(required_hours=n_steps)
            if recent_data is not None:
                tail = recent_data.tail(n_steps)
                ground_truth = {
                    'wind_power': [round(float(v), 3) for v in tail['wind_power'].tolist()],
                    'pv_power':   [round(float(v), 3) for v in tail['pv_power'].tolist()],
                    'load':       [round(float(v), 3) for v in tail['load'].tolist()],
                    'timestamps': [
                        (row['timestamp'].strftime('%m-%d %H:%M')
                         if hasattr(row['timestamp'], 'strftime')
                         else str(row['timestamp']))
                        for _, row in tail.iterrows()
                    ],
                }

        results = {}

        for model_type in model_names:
            predictor_instance = get_predictor(model_type)

            # 在测试段同一片段上推理，与真实值真正配对
            predictions = _get_testset_predictions(predictor_instance, n_steps)

            if predictions is None:
                # 降级：DB 上下文不足时用近期数据
                recent_data, _ = _build_recent_data_with_padding(required_hours=n_steps)
                if recent_data is None:
                    continue
                predictions = {'wind_power': [], 'pv_power': [], 'load': []}
                current_data = recent_data.copy()
                for hour in range(n_steps):
                    pred = predictor_instance.predict(current_data)
                    for key in predictions:
                        predictions[key].append(_to_scalar(pred[key]))
                    next_ts = current_data.iloc[-1]['timestamp'] + timedelta(hours=1)
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
                'data_source':    '数据库测试集 2023-11-07~12-31 (1312条)',
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
