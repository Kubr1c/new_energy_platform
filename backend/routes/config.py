"""
配置相关API路由
提供分时电价及DR策略的管理功能
"""

from flask import Blueprint, request, jsonify
from models.database import db, StrategyConfig

config_bp = Blueprint('config', __name__)

@config_bp.route('/api/config/strategy', methods=['GET'])
def get_strategy():
    """
    获取当前分时电价及DR策略接口
    
    返回值：
        code: 200 - 获取成功
        data: dict - 策略信息
            id: int - 策略ID
            name: str - 策略名称
            extreme_peak_price: float - 尖峰电价
            peak_price: float - 峰时电价
            flat_price: float - 平时电价
            valley_price: float - 谷时电价
            deep_valley_price: float - 深谷电价
            dr_ratio: float - 需求响应比例
            tou_config: dict - 分时电价配置
            updated_at: str - 更新时间
    
    错误处理：
        404 - 尚未配置电价策略
        500 - 查询策略失败
    """
    try:
        strategy = StrategyConfig.query.first()
        if not strategy:
            return jsonify({'code': 404, 'message': '尚未配置电价策略'})
            
        return jsonify({
            'code': 200,
            'data': {
                'id': strategy.id,
                'name': strategy.name,
                'extreme_peak_price': strategy.extreme_peak_price,
                'peak_price': strategy.peak_price,
                'flat_price': strategy.flat_price,
                'valley_price': strategy.valley_price,
                'deep_valley_price': strategy.deep_valley_price,
                'dr_ratio': strategy.dr_ratio,
                'tou_config': strategy.tou_config,
                'updated_at': strategy.updated_at.isoformat() if strategy.updated_at else None
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询策略失败: {str(e)}'})

@config_bp.route('/api/config/strategy', methods=['POST', 'PUT'])
def update_strategy():
    """
    更新策略接口
    
    请求参数：
        name: str - 策略名称（可选）
        extreme_peak_price: float - 尖峰电价（可选）
        peak_price: float - 峰时电价（可选）
        flat_price: float - 平时电价（可选）
        valley_price: float - 谷时电价（可选）
        deep_valley_price: float - 深谷电价（可选）
        dr_ratio: float - 需求响应比例（可选）
        tou_config: dict - 分时电价配置（可选）
    
    返回值：
        code: 200 - 更新成功
        message: str - 操作结果消息
    
    错误处理：
        500 - 更新策略失败
    """
    try:
        data = request.json
        strategy = StrategyConfig.query.first()
        
        if not strategy:
            strategy = StrategyConfig()
            db.session.add(strategy)
            
        strategy.name = data.get('name', strategy.name or '自定义策略')
        strategy.extreme_peak_price = data.get('extreme_peak_price', strategy.extreme_peak_price)
        strategy.peak_price = data.get('peak_price', strategy.peak_price)
        strategy.flat_price = data.get('flat_price', strategy.flat_price)
        strategy.valley_price = data.get('valley_price', strategy.valley_price)
        strategy.deep_valley_price = data.get('deep_valley_price', strategy.deep_valley_price)
        strategy.dr_ratio = data.get('dr_ratio', strategy.dr_ratio)
        strategy.tou_config = data.get('tou_config', strategy.tou_config)
        
        db.session.commit()
        return jsonify({'code': 200, 'message': '策略已更新'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'更新策略失败: {str(e)}'})
