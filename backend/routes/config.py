from flask import Blueprint, request, jsonify
from models.database import db, StrategyConfig

config_bp = Blueprint('config', __name__)

@config_bp.route('/api/config/strategy', methods=['GET'])
def get_strategy():
    """获取当前分时电价及DR策略"""
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
    """更新策略"""
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
