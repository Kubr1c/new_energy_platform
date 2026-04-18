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


def _get_realtime_ground_truth_and_context(n_context=24, n_future=24):
    """
    实时模式：从数据库取最新的连续数据。

    策略：
      - 从数据库取最新的 (n_context + n_future) 条连续小时级记录
      - 前 n_context 条作为预测输入上下文
      - 后 n_future 条作为真实值（与模型预测配对）

    返回：
      {
        'context':      DataFrame (n_context 行，用于模型预测输入)
        'ground_truth': dict {wind_power, pv_power, load, timestamps}  (n_future 行)
        'mode':         'realtime'
      }
      或 None（数据不足时）
    """
    needed = n_context + n_future
    rows = (
        NewEnergyData.query
        .order_by(NewEnergyData.timestamp.desc())
        .limit(needed)
        .all()
    )
    rows = list(reversed(rows))   # 时间升序

    if len(rows) < needed:
        return None

    ctx_rows    = rows[:n_context]
    future_rows = rows[n_context:]

    ctx_df = pd.DataFrame([{
        'timestamp':   r.timestamp,
        'wind_power':  r.wind_power  or 0.0,
        'pv_power':    r.pv_power    or 0.0,
        'load':        r.load        or 0.0,
        'temperature': r.temperature or 0.0,
        'irradiance':  r.irradiance  or 0.0,
        'wind_speed':  r.wind_speed  or 0.0,
    } for r in ctx_rows])

    ground_truth = {
        'wind_power': [round(float(r.wind_power or 0), 3) for r in future_rows],
        'pv_power':   [round(float(r.pv_power   or 0), 3) for r in future_rows],
        'load':       [round(float(r.load        or 0), 3) for r in future_rows],
        'timestamps': [r.timestamp.strftime('%m-%d %H:%M') for r in future_rows],
        'context_end': ctx_rows[-1].timestamp.strftime('%Y-%m-%d %H:%M'),
    }

    return {'context': ctx_df, 'ground_truth': ground_truth, 'mode': 'realtime'}


def _get_realtime_predictions(predictor, ctx_df: pd.DataFrame, n_future=24) -> dict:
    """
    实时模式：基于上下文 DataFrame 预测后续 n_future 步。
    """
    predictions = {'wind_power': [], 'pv_power': [], 'load': []}
    current_data = ctx_df.copy()

    for step in range(n_future):
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
    比较多个预测模型的预测序列与真实值，支持两种模式：

    请求参数:
        {
            "models": ["attention_lstm", "cnn_lstm", ...],
            "mode":   "realtime" | "testset"  （默认 "realtime"）
        }

    realtime: 用最新 24h 作上下文，预测后续 24h，与数据库真实录入值配对
    testset : 固定 2023-11-07 历史片段，用于模型横向对比
    """
    try:
        req       = request.json or {}
        model_names = req.get('models', ['attention_lstm'])
        mode        = req.get('mode', 'realtime')
        n_steps     = 24

        def _build_metrics(model_type):
            m = _get_model_metrics(model_type)
            return {
                'mape': m.get('mape'), 'rmse': m.get('rmse'),
                'mae':  m.get('mae'),  'r2':   m.get('r2'),
                'model_accuracy': m.get('model_accuracy'),
                'per_target':     m.get('per_target', {}),
                'n_samples':      m.get('n_samples', 0),
                'data_source':    '数据库测试集 2023-11-07~12-31 (1312条)',
            }

        # ============================================================
        # 实时模式
        # ============================================================
        if mode == 'realtime':
            rt = _get_realtime_ground_truth_and_context(n_context=24, n_future=n_steps)

            if rt is not None:
                ctx_df       = rt['context']
                ground_truth = rt['ground_truth']
                ctx_start    = ctx_df['timestamp'].iloc[0].strftime('%m-%d %H:%M')
                ctx_end      = ctx_df['timestamp'].iloc[-1].strftime('%m-%d %H:%M')
                pred_start   = ground_truth['timestamps'][0]
                pred_end     = ground_truth['timestamps'][-1]
                context_info = (f'上下文: {ctx_start}~{ctx_end} | '
                                f'预测时段: {pred_start}~{pred_end}')

                results = {}
                for mt in model_names:
                    p = _get_realtime_predictions(get_predictor(mt), ctx_df, n_steps)
                    results[mt] = {
                        'predictions': serialize_prediction_data(p),
                        'metrics':     _build_metrics(mt),
                    }

                return jsonify({'code': 200, 'data': {
                    'results': results, 'ground_truth': ground_truth,
                    'mode': 'realtime', 'context_info': context_info,
                }})

            # 实时数据不足，自动降级
            mode = 'testset'

        # ============================================================
        # 历史测试集模式
        # ============================================================
        ground_truth = _get_testset_ground_truth(n_steps)
        if ground_truth is None:
            return jsonify({'code': 400, 'message': '数据库中没有足够数据'})

        context_info = '历史测试集 2023-11-07 起，24步'
        results = {}
        for mt in model_names:
            p = _get_testset_predictions(get_predictor(mt), n_steps)
            if p is None:
                continue
            results[mt] = {
                'predictions': serialize_prediction_data(p),
                'metrics':     _build_metrics(mt),
            }

        return jsonify({'code': 200, 'data': {
            'results': results, 'ground_truth': ground_truth,
            'mode': mode, 'context_info': context_info,
        }})

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
