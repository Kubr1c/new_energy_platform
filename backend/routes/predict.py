"""
预测相关API路由
提供新能源发电和负荷预测功能
"""

from flask import Blueprint, request, jsonify, current_app
from models.database import db, PredictResult, NewEnergyData
from models.predict import Predictor
from models.model_registry import list_available_models
from models.metrics import evaluate_model_on_testset, evaluate_model_on_db_testset
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

predict_bp = Blueprint('predict', __name__)

# 多模型预测器缓存：model_type → Predictor 实例
_predictor_cache = {}

# 模型在测试集上的真实指标缓存：model_type → metrics dict
# 只在第一次调用时计算，后续直接复用（避免每次请求重跑 168 步推理）
_metrics_cache = {}


def _get_model_metrics(model_type: str) -> dict:
    """
    获取指定模型在独立测试集（DB 测试段 2023-11-07~12-31）上的真实评估指标。
    结果带进程级缓存，只在第一次调用时计算，后续复用。
    训练完新模型后需调用 clear_metrics_cache() 或 POST /api/predict/reload_models 刷新。
    """
    if model_type not in _metrics_cache:
        try:
            predictor_instance = get_predictor(model_type)
            # 选项 X：使用 DB 测试段（2023-11-07~12-31），与训练集完全隔离，无泄露
            app = current_app._get_current_object()
            result = evaluate_model_on_db_testset(predictor_instance, app)
            overall = result['overall']
            mape = overall['mape']
            accuracy = round(max(0.0, min(100.0, 100.0 - mape)), 2)
            _metrics_cache[model_type] = {
                'model_accuracy': accuracy,
                'mape':           round(mape, 2),
                'rmse':           round(overall['rmse'], 4),
                'mae':            round(overall['mae'],  4),
                'r2':             round(overall['r2'],   4),
                'per_target':     result['per_target'],
                'n_samples':      result['n_samples'],
                'test_range':     result.get('test_range', ''),
                'source':         result.get('source', 'database'),
                'confidence':     round(max(0.0, min(100.0, accuracy * 0.95)), 1),
                'data_quality':   min(5, max(1, round(accuracy / 20))),
                'model_status':   'normal' if mape < 30 else 'warning',
            }
        except Exception as e:
            # 评估失败（如 DB 不可用）时降级到 CSV 版本
            try:
                predictor_instance = get_predictor(model_type)
                result = evaluate_model_on_testset(predictor_instance)
                overall = result['overall']
                mape = overall['mape']
                accuracy = round(max(0.0, min(100.0, 100.0 - mape)), 2)
                _metrics_cache[model_type] = {
                    'model_accuracy': accuracy,
                    'mape':           round(mape, 2),
                    'rmse':           round(overall['rmse'], 4),
                    'mae':            round(overall['mae'],  4),
                    'r2':             round(overall['r2'],   4),
                    'per_target':     result['per_target'],
                    'n_samples':      result['n_samples'],
                    'test_range':     'test_data.csv (fallback)',
                    'source':         'csv_fallback',
                    'confidence':     round(max(0.0, min(100.0, accuracy * 0.95)), 1),
                    'data_quality':   min(5, max(1, round(accuracy / 20))),
                    'model_status':   'normal' if mape < 30 else 'warning',
                }
            except Exception as e2:
                # 两种评估均失败时返回占位符，不影响预测功能
                _metrics_cache[model_type] = {
                    'model_accuracy': None,
                    'mape': None, 'rmse': None, 'mae': None, 'r2': None,
                    'per_target': {}, 'n_samples': 0,
                    'test_range': '', 'source': 'error',
                    'confidence': None, 'data_quality': None,
                    'model_status': 'error',
                    'error': str(e2),
                }
    return _metrics_cache[model_type]


def clear_metrics_cache(model_type=None):
    """
    清除预测器缓存和指标缓存，使下次请求时重新加载权重并重新评估指标。
    训练完新模型后调用，无需重启服务。

    model_type=None : 清除全部模型的缓存
    model_type='xx' : 只清除指定模型
    """
    if model_type:
        _metrics_cache.pop(model_type, None)
        _predictor_cache.pop(model_type, None)
    else:
        _metrics_cache.clear()
        _predictor_cache.clear()

def serialize_prediction_data(data):
    """
    将numpy数组转换为Python列表，以便JSON序列化
    
    参数：
        data: 要序列化的数据
    返回：
        序列化后的数据
    """
    if isinstance(data, dict):
        serialized = {}
        for key, value in data.items():
            if hasattr(value, 'tolist'):
                serialized[key] = value.tolist()
            elif isinstance(value, dict):
                serialized[key] = serialize_prediction_data(value)
            elif isinstance(value, (list, tuple)):
                serialized[key] = [serialize_prediction_data(item) if hasattr(item, 'tolist') else item for item in value]
            else:
                serialized[key] = value
        return serialized
    elif hasattr(data, 'tolist'):
        return data.tolist()
    else:
        return data

def get_predictor(model_type='attention_lstm'):
    """
    获取预测器实例（按 model_type 缓存）
    
    参数：
        model_type: 模型类型，默认为 'attention_lstm'
    返回：
        Predictor 实例
    """
    global _predictor_cache
    if model_type not in _predictor_cache:
        _predictor_cache[model_type] = Predictor(model_type=model_type)
    return _predictor_cache[model_type]

def _build_recent_data_with_padding(required_hours=24):
    """
    获取数据库最新数据，不足 required_hours 时使用现有数据
    
    参数：
        required_hours: 需要的小时数，默认为24
    返回：
        (DataFrame, int) - 数据和实际数据条数
    """
    # 获取数据库中最新的数据
    db_data = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).limit(required_hours).all()
    
    if len(db_data) == 0:
        return None, 0
    
    # 按时间升序排列
    db_data = sorted(db_data, key=lambda x: x.timestamp)

    rows = [{
        'timestamp': item.timestamp,
        'wind_power': item.wind_power,
        'pv_power': item.pv_power,
        'load': item.load,
        'temperature': item.temperature,
        'irradiance': item.irradiance,
        'wind_speed': item.wind_speed
    } for item in db_data]

    return pd.DataFrame(rows), len(db_data)

@predict_bp.route('/api/predict/models', methods=['GET'])
def get_available_models():
    """
    获取所有可用的预测模型列表
    
    返回值：
        code: 200 - 获取成功
        data: list - 模型列表
    
    错误处理：
        500 - 获取模型列表失败
    """
    try:
        models = list_available_models()
        return jsonify({'code': 200, 'data': models})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取模型列表失败: {str(e)}'})

@predict_bp.route('/api/predict/single', methods=['POST'])
def predict_single():
    """
    单步预测接口
    
    请求参数：
        model_type: str - 模型类型（可选，默认为 'attention_lstm'）
        data: list - 输入数据（可选，若不提供则使用数据库最新数据）
    
    返回值：
        code: 200 - 预测成功
        data: dict - 预测结果
            prediction: dict - 预测值
            timestamp: str - 预测时间
            id: int - 预测记录ID
            model_type: str - 使用的模型类型
            input_count: int - 输入数据条数
            original_count: int - 原始数据条数
            metrics: dict - 模型评估指标
    
    错误处理：
        400 - 没有可用数据
        500 - 预测错误
    """
    try:
        # handle empty JSON request
        try:
            data = request.json or {}
        except Exception as e:
            print(f"JSON parsing error: {e}")
            data = {}
        
        # 获取模型类型（默认 attention_lstm）
        model_type = data.get('model_type', 'attention_lstm')
        
        # 获取预测器
        predictor_instance = get_predictor(model_type)
        
        # 获取最近24小时数据
        if 'data' in data:
            # 使用提供的数据
            recent_data = pd.DataFrame(data['data'])
            recent_data['timestamp'] = pd.to_datetime(recent_data['timestamp'])
        else:
            recent_data, original_count = _build_recent_data_with_padding(required_hours=24)
            if recent_data is None:
                return jsonify({'code': 400, 'message': '没有可用数据，无法执行预测'})
        
        # 执行预测
        prediction = predictor_instance.predict(recent_data)
        
        # convert numpy arrays to Python lists for JSON serialization
        serializable_prediction = serialize_prediction_data(prediction)
        
        # 获取模型在测试集上的真实评估指标（含缓存）
        model_metrics = _get_model_metrics(model_type)

        # 保存预测结果到数据库（含模型类型和真实 MAPE）
        predict_record = PredictResult(
            predict_type='multi',
            model_type=model_type,
            start_time=datetime.utcnow(),
            horizon=1,
            data=serializable_prediction,
            mape=model_metrics.get('mape')
        )
        db.session.add(predict_record)
        db.session.commit()
        
        return jsonify({
            'code': 200, 
            'data': {
                'prediction': serializable_prediction,
                'timestamp': datetime.utcnow().isoformat(),
                'id': predict_record.id,
                'model_type': model_type,
                'input_count': 24,
                'original_count': original_count if 'original_count' in locals() else len(recent_data),
                'metrics': model_metrics
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'预测错误: {str(e)}'})

@predict_bp.route('/api/predict/batch', methods=['POST'])
def predict_batch():
    """
    批量预测接口（未来24小时）
    
    请求参数：
        model_type: str - 模型类型（可选，默认为 'attention_lstm'）
    
    返回值：
        code: 200 - 预测成功
        data: dict - 预测结果
            predictions: dict - 未来24小时的预测值
            start_time: str - 预测开始时间
            horizon: int - 预测时长（24小时）
            id: int - 预测记录ID
            model_type: str - 使用的模型类型
            input_count: int - 输入数据条数
            original_count: int - 原始数据条数
            metrics: dict - 模型评估指标
    
    错误处理：
        400 - 没有可用数据
        500 - 批量预测错误
    """
    try:
        # handle empty JSON request
        try:
            data = request.json or {}
        except Exception as e:
            print(f"JSON parsing error: {e}")
            data = {}
        
        # 获取模型类型
        model_type = data.get('model_type', 'attention_lstm')
        
        # 获取预测器
        predictor_instance = get_predictor(model_type)
        
        recent_data, original_count = _build_recent_data_with_padding(required_hours=24)
        if recent_data is None:
            return jsonify({'code': 400, 'message': '没有可用数据，无法执行批量预测'})
        
        # 递归预测未来24小时
        predictions = {'wind_power': [], 'pv_power': [], 'load': []}
        current_data = recent_data.copy()
        
        for hour in range(24):
            # 计算预测的小时数
            next_timestamp = current_data.iloc[-1]['timestamp'] + timedelta(hours=1)
            predict_hour = next_timestamp.hour
            
            # execute single step prediction with predict_hour
            pred = predictor_instance.predict(current_data, predict_hour)
            
            # save prediction results
            for key in predictions.keys():
                pred_value = pred[key]
                # ensure we append scalar value, not array
                if hasattr(pred_value, 'item'):
                    # numpy scalar
                    predictions[key].append(pred_value.item())
                elif hasattr(pred_value, 'tolist') and len(pred_value.tolist()) == 1:
                    # numpy array with single element
                    predictions[key].append(pred_value.tolist()[0])
                else:
                    # already a scalar or list
                    predictions[key].append(pred_value)
            
            # 更新数据集，将预测值作为新的数据点
            # 这里需要构造下一个时间步的特征数据
            # 简化处理：使用预测值，其他特征使用最近值或简单外推
            
            # get scalar values for next_row
            wind_power_val = pred['wind_power']
            pv_power_val = pred['pv_power'] 
            load_val = pred['load']
            
            # convert to scalar if needed
            if hasattr(wind_power_val, 'item'):
                wind_power_val = wind_power_val.item()
            elif hasattr(wind_power_val, 'tolist') and len(wind_power_val.tolist()) == 1:
                wind_power_val = wind_power_val.tolist()[0]
                
            if hasattr(pv_power_val, 'item'):
                pv_power_val = pv_power_val.item()
            elif hasattr(pv_power_val, 'tolist') and len(pv_power_val.tolist()) == 1:
                pv_power_val = pv_power_val.tolist()[0]
                
            if hasattr(load_val, 'item'):
                load_val = load_val.item()
            elif hasattr(load_val, 'tolist') and len(load_val.tolist()) == 1:
                load_val = load_val.tolist()[0]
            
            # 为了更好的光伏预测，我们需要根据时间调整辐照度
            # 白天辐照度高，夜间辐照度为0
            if 6 <= predict_hour < 18:
                # 白天：根据时间调整辐照度
                irradiance_val = current_data.iloc[-1]['irradiance']
                if irradiance_val == 0:
                    # 如果当前辐照度为0，设置一个合理的白天值
                    irradiance_val = 500.0
            else:
                # 夜间：辐照度为0
                irradiance_val = 0.0
            
            next_row = {
                'timestamp': next_timestamp,
                'wind_power': wind_power_val,
                'pv_power': pv_power_val,
                'load': load_val,
                'temperature': current_data.iloc[-1]['temperature'],  # keep unchanged
                'irradiance': irradiance_val,    # 根据时间调整辐照度
                'wind_speed': current_data.iloc[-1]['wind_speed']      # keep unchanged
            }
            
            # 添加到数据集
            current_data = pd.concat([current_data.iloc[1:], pd.DataFrame([next_row])], ignore_index=True)
        
        # convert numpy arrays to Python lists for JSON serialization
        serializable_predictions = serialize_prediction_data(predictions)
        
        # 获取模型在测试集上的真实评估指标（含缓存，首次调用较慢）
        model_metrics = _get_model_metrics(model_type)

        # 保存预测结果到数据库（含模型类型和真实 MAPE）
        predict_record = PredictResult(
            predict_type='multi',
            model_type=model_type,
            start_time=datetime.utcnow(),
            horizon=24,
            data=serializable_predictions,
            mape=model_metrics.get('mape')
        )
        db.session.add(predict_record)
        db.session.commit()
        
        return jsonify({
            'code': 200, 
            'data': {
                'predictions': serializable_predictions,
                'start_time': datetime.utcnow().isoformat(),
                'horizon': 24,
                'id': predict_record.id,
                'model_type': model_type,
                'input_count': 24,
                'original_count': original_count,
                'metrics': model_metrics
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'批量预测错误: {str(e)}'})

@predict_bp.route('/api/predict/history', methods=['GET'])
def get_predict_history():
    """
    获取预测历史接口
    
    查询参数：
        limit: int - 返回记录数（可选，默认为10）
        type: str - 预测类型（可选，默认为'multi'）
    
    返回值：
        code: 200 - 获取成功
        data: list - 预测历史记录
            每个元素为预测记录字典
                id: int - 预测记录ID
                predict_type: str - 预测类型
                model_type: str - 模型类型
                start_time: str - 预测开始时间
                horizon: int - 预测时长
                data: dict - 预测数据
                mape: float - 平均绝对百分比误差
                created_at: str - 创建时间
    
    错误处理：
        500 - 查询错误
    """
    try:
        # 获取查询参数
        limit = request.args.get('limit', 10, type=int)
        predict_type = request.args.get('type', 'multi')
        
        # 查询预测历史
        predictions = PredictResult.query.filter_by(
            predict_type=predict_type
        ).order_by(PredictResult.created_at.desc()).limit(limit).all()
        
        result = []
        for pred in predictions:
            result.append({
                'id': pred.id,
                'predict_type': pred.predict_type,
                'model_type': pred.model_type or 'attention_lstm',
                'start_time': pred.start_time.isoformat(),
                'horizon': pred.horizon,
                'data': pred.data,
                'mape': pred.mape,
                'created_at': pred.created_at.isoformat()
            })
        
        return jsonify({'code': 200, 'data': result})
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询错误: {str(e)}'})

@predict_bp.route('/api/predict/evaluate', methods=['POST'])
def evaluate_prediction():
    """
    评估预测准确性接口
    
    请求参数：
        predict_id: int - 预测记录ID
    
    返回值：
        code: 200 - 评估成功
        data: dict - 评估结果
            mape: dict - 各指标的平均绝对百分比误差
            overall_mape: float - 总体平均绝对百分比误差
    
    错误处理：
        400 - 缺少预测ID或实际数据不足
        404 - 预测结果不存在
        500 - 评估错误
    """
    try:
        data = request.json
        predict_id = data.get('predict_id')
        
        if not predict_id:
            return jsonify({'code': 400, 'message': '缺少预测ID'})
        
        # 获取预测结果
        prediction = PredictResult.query.get(predict_id)
        if not prediction:
            return jsonify({'code': 404, 'message': '预测结果不存在'})
        
        # 获取对应时间的实际数据
        start_time = prediction.start_time
        end_time = start_time + timedelta(hours=prediction.horizon)
        
        actual_data = NewEnergyData.query.filter(
            NewEnergyData.timestamp >= start_time,
            NewEnergyData.timestamp <= end_time
        ).order_by(NewEnergyData.timestamp.asc()).all()
        
        if len(actual_data) != prediction.horizon:
            return jsonify({'code': 400, 'message': '实际数据不足，无法评估'})
        
        # 计算MAPE
        pred_data = prediction.data
        actual_values = {
            'wind_power': [item.wind_power for item in actual_data],
            'pv_power': [item.pv_power for item in actual_data],
            'load': [item.load for item in actual_data]
        }
        
        mape_values = {}
        for key in pred_data.keys():
            if key in actual_values:
                pred_vals = np.array(pred_data[key])
                actual_vals = np.array(actual_values[key])
                mape = np.mean(np.abs((actual_vals - pred_vals) / (actual_vals + 1e-6))) * 100
                mape_values[key] = mape
        
        # 更新预测结果的MAPE
        prediction.mape = np.mean(list(mape_values.values()))
        db.session.commit()
        
        return jsonify({
            'code': 200, 
            'data': {
                'mape': mape_values,
                'overall_mape': prediction.mape
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'评估错误: {str(e)}'})

@predict_bp.route('/api/predict/<int:predict_id>', methods=['DELETE'])
def delete_prediction(predict_id):
    """
    删除预测结果接口
    
    路径参数：
        predict_id: int - 预测记录ID
    
    返回值：
        code: 200 - 删除成功
        message: str - 操作结果消息
    
    错误处理：
        404 - 预测结果不存在
        500 - 删除错误
    """
    try:
        # get prediction result
        prediction = PredictResult.query.get(predict_id)
        if not prediction:
            return jsonify({'code': 404, 'message': '预测结果不存在'})
        
        # delete prediction
        db.session.delete(prediction)
        db.session.commit()
        
        return jsonify({'code': 200, 'message': '预测结果删除成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'删除错误: {str(e)}'})

@predict_bp.route('/api/predict/batch_delete', methods=['POST'])
def batch_delete_predictions():
    """
    批量删除预测结果接口
    
    请求参数：
        predict_ids: list - 预测记录ID列表
    
    返回值：
        code: 200 - 删除成功
        message: str - 操作结果消息
    
    错误处理：
        400 - 缺少预测ID列表
        404 - 没有找到预测结果
        500 - 批量删除错误
    """
    try:
        data = request.json
        predict_ids = data.get('predict_ids', [])
        
        if not predict_ids:
            return jsonify({'code': 400, 'message': '缺少预测ID列表'})
        
        # get predictions to delete
        predictions = PredictResult.query.filter(PredictResult.id.in_(predict_ids)).all()
        
        if not predictions:
            return jsonify({'code': 404, 'message': '没有找到预测结果'})
        
        # delete predictions
        for prediction in predictions:
            db.session.delete(prediction)
        
        db.session.commit()
        
        return jsonify({
            'code': 200, 
            'message': f'成功删除 {len(predictions)} 条预测结果'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'批量删除错误: {str(e)}'})


@predict_bp.route('/api/predict/reload_models', methods=['POST'])
def reload_models():
    """
    清除预测器缓存和指标缓存，令服务在下次请求时自动重新加载
    新的 .pth 权重文件并重新计算测试集指标。训练完成后调用，无需重启服务。

    请求体（可选）:
        {"model_type": "attention_lstm"}   -- 只刷新指定模型
        {}                                 -- 刷新全部模型（默认）
    
    返回值：
        code: 200 - 缓存清除成功
        message: str - 操作结果消息
    
    错误处理：
        500 - 缓存清除失败
    """
    try:
        data = request.json or {}
        model_type = data.get('model_type', None)
        clear_metrics_cache(model_type)
        target = model_type or '全部'
        return jsonify({
            'code': 200,
            'message': f'已清除 [{target}] 模型缓存，下次请求时将重新加载权重并评估指标'
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'缓存清除失败: {str(e)}'})
