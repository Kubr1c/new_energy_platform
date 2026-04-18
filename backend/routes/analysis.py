from flask import Blueprint, request, jsonify
from models.database import db, PredictResult, StrategyConfig
from optimization.solver import solve_dispatch
from routes.predict import (
    _build_recent_data_with_padding, get_predictor,
    serialize_prediction_data, _get_model_metrics
)
from models.metrics import evaluate_model_on_testset
import numpy as np
from datetime import datetime
import pandas as pd
from datetime import timedelta
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


@analysis_bp.route('/api/analysis/model_compare', methods=['POST'])
def model_compare():
    """
    比较多个预测模型在测试集上的真实性能，同时返回最近 24 小时的预测序列。

    请求参数:
        {"models": ["attention_lstm", "cnn_lstm", ...]}

    返回:
        各模型的预测序列（基于最新历史数据滚动预测 24 步）
        + 在 CSV 测试集上计算的真实 MAPE / RMSE / MAE / R²
    """
    try:
        data = request.json or {}
        model_names = data.get('models', ['attention_lstm'])

        # 获取最新历史数据，用于生成演示用的 24 步预测序列（供前端图表展示）
        recent_data, _ = _build_recent_data_with_padding(required_hours=24)
        if recent_data is None:
            return jsonify({'code': 400, 'message': '没有足够数据进行预测'})

        results = {}

        for model_type in model_names:
            predictor_instance = get_predictor(model_type)

            # ---- 1. 生成未来 24 小时预测序列（用于前端折线图展示） ----
            predictions = {'wind_power': [], 'pv_power': [], 'load': []}
            current_data = recent_data.copy()

            for hour in range(24):
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

            # ---- 2. 获取该模型在测试集上的真实指标（带缓存） ----
            m = _get_model_metrics(model_type)
            metrics = {
                'mape':           m.get('mape'),
                'rmse':           m.get('rmse'),
                'mae':            m.get('mae'),
                'r2':             m.get('r2'),
                'model_accuracy': m.get('model_accuracy'),
                'per_target':     m.get('per_target', {}),
                'n_samples':      m.get('n_samples', 0),
                'data_source':    'test_data.csv (168 samples, 2023-02-01~07)',
            }

            results[model_type] = {
                'predictions': serialize_prediction_data(predictions),
                'metrics':     metrics,
            }

        return jsonify({'code': 200, 'data': results})

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
