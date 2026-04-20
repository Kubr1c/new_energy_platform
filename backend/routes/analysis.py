"""
分析相关API路由
提供模型比较和算法比较功能
"""

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
    """
    将 numpy 标量/单元素数组统一转为 Python float
    
    参数：
        v: 要转换的值
    返回：
        float - 转换后的值
    """
    if hasattr(v, 'item'):
        return v.item()
    if hasattr(v, 'tolist'):
        lst = v.tolist()
        return lst[0] if len(lst) == 1 else float(np.mean(lst))
    return float(v)


def _get_realtime_ground_truth_and_context(n_context=24, n_future=24):
    """
    实时模式：从数据库取最新的连续数据

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
        # 包含完整年月日时分，前端 X 轴直接展示
        'timestamps': [r.timestamp.strftime('%Y-%m-%d %H:%M') for r in future_rows],
        'context_end': ctx_rows[-1].timestamp.strftime('%Y-%m-%d %H:%M'),
        # 方便前端展示的简短日期标签
        'date_label': future_rows[0].timestamp.strftime('%Y-%m-%d'),
    }

    return {'context': ctx_df, 'ground_truth': ground_truth, 'mode': 'realtime'}


def _get_realtime_predictions(predictor, ctx_df: pd.DataFrame, n_future=24) -> dict:
    """
    实时模式：基于上下文 DataFrame 预测后续 n_future 步
    
    参数：
        predictor: 预测器实例
        ctx_df: 上下文数据
        n_future: 预测步数
    返回：
        dict - 预测结果
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
        'timestamps': [r.timestamp.strftime('%Y-%m-%d %H:%M') for r in rows],
        'date_label': rows[0].timestamp.strftime('%Y-%m-%d'),
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
    比较多个预测模型的预测序列与真实值接口
    
    请求参数:
        {
            "models": ["attention_lstm", "cnn_lstm", ...],  # 要比较的模型列表
            "mode":   "realtime" | "testset"  （默认 "realtime"）  # 比较模式
        }
    
    返回值：
        code: 200 - 比较成功
        data: dict - 比较结果
            results: dict - 各模型的预测结果和指标
            ground_truth: dict - 真实值
            mode: str - 比较模式
            context_info: str - 上下文信息
    
    错误处理：
        400 - 数据库中没有足够数据
        500 - 模型比较失败
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
    比较不同优化算法（PSO，AWPSO，GA）对相同预测数据的调度结果接口
    
    请求参数:
        {
            "algorithms": ["awpso", "pso", "ga"],  # 要比较的算法列表
            "ess_params": {}  # 储能参数（可选）
        }
    
    返回值：
        code: 200 - 比较成功
        data: dict - 各算法的调度结果
            每个算法的结果包含：
                charge_plan: list - 充电计划
                discharge_plan: list - 放电计划
                soc_curve: list - 荷电状态曲线
                abandon_rate: float - 弃风弃光率
                total_cost: float - 总成本
                fitness_history: list - 适应度历史
                time_cost: float - 计算时间
    
    错误处理：
        400 - 没有可用的预测数据
        500 - 算法比较失败
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
