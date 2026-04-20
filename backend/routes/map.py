"""
储能站点地图API
提供储能站点的CRUD操作和地图数据查询
"""

from flask import Blueprint, request, jsonify, current_app
from models.database import db, EnergyStorageSite, User
from routes.auth import token_required
import math

map_bp = Blueprint('map', __name__)

# 地球半径（千米）
EARTH_RADIUS = 6371.0

@map_bp.route('/api/map/sites', methods=['GET'])
# @token_required
def get_sites():
    current_user = None  # 模拟用户
    """
    获取储能站点列表接口
    
    查询参数：
        adcode: str - 行政区划代码（可选）
        level: str - 站点级别（可选）
        status: str - 站点状态（可选，默认为 'active'）
    
    返回值：
        code: 200 - 获取成功
        message: str - 操作结果消息
        data: list - 站点列表
            每个元素为站点信息字典
                id: int - 站点ID
                name: str - 站点名称
                adcode: str - 行政区划代码
                level: str - 站点级别
                longitude: float - 经度
                latitude: float - 纬度
                address: str - 地址
                capacity_mwh: float - 容量（MWh）
                power_mw: float - 功率（MW）
                soh_percent: float - 健康状态百分比
                status: str - 站点状态
                current_soc: float - 当前荷电状态
                charge_power: float - 充电功率
                discharge_power: float - 放电功率
                owner: str - 所有者
                operator: str - 运营者
                created_at: str - 创建时间
                updated_at: str - 更新时间
        total: int - 站点总数
    
    错误处理：
        500 - 获取站点列表失败
    """
    try:
        # 查询参数
        adcode = request.args.get('adcode')
        level = request.args.get('level')
        status = request.args.get('status', 'active')
        
        # 构建查询
        query = EnergyStorageSite.query
        
        if adcode:
            query = query.filter_by(adcode=adcode)
        if level:
            query = query.filter_by(level=level)
        if status:
            query = query.filter_by(status=status)
        
        # 执行查询
        sites = query.order_by(EnergyStorageSite.created_at.desc()).all()
        
        # 转换为字典列表
        sites_data = []
        for site in sites:
            site_data = {
                'id': site.id,
                'name': site.name,
                'adcode': site.adcode,
                'level': site.level,
                'longitude': site.longitude,
                'latitude': site.latitude,
                'address': site.address,
                'capacity_mwh': site.capacity_mwh,
                'power_mw': site.power_mw,
                'soh_percent': site.soh_percent,
                'status': site.status,
                'current_soc': site.current_soc,
                'charge_power': site.charge_power,
                'discharge_power': site.discharge_power,
                'owner': site.owner,
                'operator': site.operator,
                'created_at': site.created_at.isoformat() if site.created_at else None,
                'updated_at': site.updated_at.isoformat() if site.updated_at else None
            }
            sites_data.append(site_data)
        
        return jsonify({
            'code': 200,
            'message': '成功获取站点列表',
            'data': sites_data,
            'total': len(sites_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"获取站点列表失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取站点列表失败: {str(e)}'
        }), 500

@map_bp.route('/api/map/sites/nearby', methods=['GET'])
@token_required
def get_nearby_sites(current_user):
    """
    获取附近的储能站点接口（基于经纬度）
    
    查询参数：
        lng: float - 经度
        lat: float - 纬度
        radius: float - 搜索半径（可选，默认为50公里）
        limit: int - 返回数量（可选，默认为20）
    
    返回值：
        code: 200 - 获取成功
        message: str - 操作结果消息
        data: list - 附近站点列表
            每个元素为站点信息字典
                id: int - 站点ID
                name: str - 站点名称
                longitude: float - 经度
                latitude: float - 纬度
                distance_km: float - 距离（公里）
                capacity_mwh: float - 容量（MWh）
                power_mw: float - 功率（MW）
                current_soc: float - 当前荷电状态
        total: int - 附近站点总数
    
    错误处理：
        400 - 缺少经纬度参数
        500 - 获取附近站点失败
    """
    try:
        # 获取参数
        longitude = request.args.get('lng', type=float)
        latitude = request.args.get('lat', type=float)
        radius = request.args.get('radius', type=float, default=50.0)  # 默认50公里
        limit = request.args.get('limit', type=int, default=20)
        
        if longitude is None or latitude is None:
            return jsonify({
                'code': 400,
                'message': '缺少经纬度参数'
            }), 400
        
        # 获取所有站点
        all_sites = EnergyStorageSite.query.filter_by(status='active').all()
        
        # 计算距离并筛选
        nearby_sites = []
        for site in all_sites:
            # 计算大圆距离（Haversine公式简化版）
            dlat = math.radians(site.latitude - latitude)
            dlng = math.radians(site.longitude - longitude)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(latitude)) * math.cos(math.radians(site.latitude)) * math.sin(dlng/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = EARTH_RADIUS * c
            
            if distance <= radius:
                site_data = {
                    'id': site.id,
                    'name': site.name,
                    'longitude': site.longitude,
                    'latitude': site.latitude,
                    'distance_km': round(distance, 2),
                    'capacity_mwh': site.capacity_mwh,
                    'power_mw': site.power_mw,
                    'current_soc': site.current_soc
                }
                nearby_sites.append(site_data)
        
        # 按距离排序
        nearby_sites.sort(key=lambda x: x['distance_km'])
        
        # 限制数量
        nearby_sites = nearby_sites[:limit]
        
        return jsonify({
            'code': 200,
            'message': '成功获取附近站点',
            'data': nearby_sites,
            'total': len(nearby_sites)
        })
        
    except Exception as e:
        current_app.logger.error(f"获取附近站点失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取附近站点失败: {str(e)}'
        }), 500

@map_bp.route('/api/map/sites/<int:site_id>', methods=['GET'])
@token_required
def get_site(current_user, site_id):
    """
    获取单个站点详情接口
    
    路径参数：
        site_id: int - 站点ID
    
    返回值：
        code: 200 - 获取成功
        message: str - 操作结果消息
        data: dict - 站点详情
            id: int - 站点ID
            name: str - 站点名称
            adcode: str - 行政区划代码
            level: str - 站点级别
            longitude: float - 经度
            latitude: float - 纬度
            address: str - 地址
            capacity_mwh: float - 容量（MWh）
            power_mw: float - 功率（MW）
            soh_percent: float - 健康状态百分比
            status: str - 站点状态
            current_soc: float - 当前荷电状态
            charge_power: float - 充电功率
            discharge_power: float - 放电功率
            owner: str - 所有者
            operator: str - 运营者
            created_at: str - 创建时间
            updated_at: str - 更新时间
    
    错误处理：
        404 - 站点不存在
        500 - 获取站点详情失败
    """
    try:
        site = db.session.get(EnergyStorageSite, site_id)
        
        if not site:
            return jsonify({
                'code': 404,
                'message': '站点不存在'
            }), 404
        
        site_data = {
            'id': site.id,
            'name': site.name,
            'adcode': site.adcode,
            'level': site.level,
            'longitude': site.longitude,
            'latitude': site.latitude,
            'address': site.address,
            'capacity_mwh': site.capacity_mwh,
            'power_mw': site.power_mw,
            'soh_percent': site.soh_percent,
            'status': site.status,
            'current_soc': site.current_soc,
            'charge_power': site.charge_power,
            'discharge_power': site.discharge_power,
            'owner': site.owner,
            'operator': site.operator,
            'created_at': site.created_at.isoformat() if site.created_at else None,
            'updated_at': site.updated_at.isoformat() if site.updated_at else None
        }
        
        return jsonify({
            'code': 200,
            'message': '成功获取站点详情',
            'data': site_data
        })
        
    except Exception as e:
        current_app.logger.error(f"获取站点详情失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取站点详情失败: {str(e)}'
        }), 500

@map_bp.route('/api/map/sites', methods=['POST'])
@token_required
def create_site(current_user):
    """
    创建新的储能站点接口（需要管理员权限）
    
    请求参数：
        name: str - 站点名称
        adcode: str - 行政区划代码
        longitude: float - 经度
        latitude: float - 纬度
        capacity_mwh: float - 容量（MWh）
        power_mw: float - 功率（MW）
        level: str - 站点级别（可选，默认为 'province'）
        address: str - 地址（可选）
        soh_percent: float - 健康状态百分比（可选，默认为 100.0）
        status: str - 站点状态（可选，默认为 'active'）
        current_soc: float - 当前荷电状态（可选，默认为 50.0）
        charge_power: float - 充电功率（可选，默认为 0.0）
        discharge_power: float - 放电功率（可选，默认为 0.0）
        owner: str - 所有者（可选）
        operator: str - 运营者（可选）
    
    返回值：
        code: 201 - 创建成功
        message: str - 操作结果消息
        data: dict - 站点信息
            id: int - 站点ID
            name: str - 站点名称
            adcode: str - 行政区划代码
            level: str - 站点级别
            longitude: float - 经度
            latitude: float - 纬度
            capacity_mwh: float - 容量（MWh）
            power_mw: float - 功率（MW）
            status: str - 站点状态
    
    错误处理：
        403 - 只有管理员可以创建站点
        400 - 缺少必需字段
        500 - 创建站点失败
    """
    try:
        # 检查权限
        if current_user.role != 'admin':
            return jsonify({
                'code': 403,
                'message': '只有管理员可以创建站点'
            }), 403
        
        # 获取请求数据
        data = request.json
        
        # 验证必需字段
        required_fields = ['name', 'adcode', 'longitude', 'latitude', 'capacity_mwh', 'power_mw']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'code': 400,
                    'message': f'缺少必需字段: {field}'
                }), 400
        
        # 创建新站点
        new_site = EnergyStorageSite(
            name=data['name'],
            adcode=data['adcode'],
            level=data.get('level', 'province'),
            longitude=float(data['longitude']),
            latitude=float(data['latitude']),
            address=data.get('address', ''),
            capacity_mwh=float(data['capacity_mwh']),
            power_mw=float(data['power_mw']),
            soh_percent=float(data.get('soh_percent', 100.0)),
            status=data.get('status', 'active'),
            current_soc=float(data.get('current_soc', 50.0)),
            charge_power=float(data.get('charge_power', 0.0)),
            discharge_power=float(data.get('discharge_power', 0.0)),
            owner=data.get('owner', ''),
            operator=data.get('operator', ''),
            created_by=current_user.id
        )
        
        # 保存到数据库
        db.session.add(new_site)
        db.session.commit()
        
        # 返回创建结果
        site_data = {
            'id': new_site.id,
            'name': new_site.name,
            'adcode': new_site.adcode,
            'level': new_site.level,
            'longitude': new_site.longitude,
            'latitude': new_site.latitude,
            'capacity_mwh': new_site.capacity_mwh,
            'power_mw': new_site.power_mw,
            'status': new_site.status
        }
        
        return jsonify({
            'code': 201,
            'message': '站点创建成功',
            'data': site_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建站点失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'创建站点失败: {str(e)}'
        }), 500

@map_bp.route('/api/map/sites/<int:site_id>', methods=['PUT'])
@token_required
def update_site(current_user, site_id):
    """
    更新储能站点接口（需要管理员权限）
    
    路径参数：
        site_id: int - 站点ID
    
    请求参数：
        name: str - 站点名称（可选）
        adcode: str - 行政区划代码（可选）
        level: str - 站点级别（可选）
        longitude: float - 经度（可选）
        latitude: float - 纬度（可选）
        address: str - 地址（可选）
        capacity_mwh: float - 容量（MWh）（可选）
        power_mw: float - 功率（MW）（可选）
        soh_percent: float - 健康状态百分比（可选）
        status: str - 站点状态（可选）
        current_soc: float - 当前荷电状态（可选）
        charge_power: float - 充电功率（可选）
        discharge_power: float - 放电功率（可选）
        owner: str - 所有者（可选）
        operator: str - 运营者（可选）
    
    返回值：
        code: 200 - 更新成功
        message: str - 操作结果消息
        data: dict - 站点信息
            id: int - 站点ID
            name: str - 站点名称
            updated_at: str - 更新时间
    
    错误处理：
        403 - 只有管理员可以更新站点
        404 - 站点不存在
        500 - 更新站点失败
    """
    try:
        # 检查权限
        if current_user.role != 'admin':
            return jsonify({
                'code': 403,
                'message': '只有管理员可以更新站点'
            }), 403
        
        # 查找站点
        site = db.session.get(EnergyStorageSite, site_id)
        
        if not site:
            return jsonify({
                'code': 404,
                'message': '站点不存在'
            }), 404
        
        # 获取更新数据
        data = request.json
        
        # 更新字段
        updatable_fields = [
            'name', 'adcode', 'level', 'longitude', 'latitude', 'address',
            'capacity_mwh', 'power_mw', 'soh_percent', 'status',
            'current_soc', 'charge_power', 'discharge_power',
            'owner', 'operator'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(site, field, data[field])
        
        # 保存更改
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '站点更新成功',
            'data': {
                'id': site.id,
                'name': site.name,
                'updated_at': site.updated_at.isoformat() if site.updated_at else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新站点失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'更新站点失败: {str(e)}'
        }), 500

@map_bp.route('/api/map/sites/<int:site_id>', methods=['DELETE'])
@token_required
def delete_site(current_user, site_id):
    """
    删除储能站点接口（需要管理员权限）
    
    路径参数：
        site_id: int - 站点ID
    
    返回值：
        code: 200 - 删除成功
        message: str - 操作结果消息
        data: dict - 站点信息
            id: int - 站点ID
            name: str - 站点名称
            status: str - 站点状态
    
    错误处理：
        403 - 只有管理员可以删除站点
        404 - 站点不存在
        500 - 删除站点失败
    """
    try:
        # 检查权限
        if current_user.role != 'admin':
            return jsonify({
                'code': 403,
                'message': '只有管理员可以删除站点'
            }), 403
        
        # 查找站点
        site = db.session.get(EnergyStorageSite, site_id)
        
        if not site:
            return jsonify({
                'code': 404,
                'message': '站点不存在'
            }), 404
        
        # 软删除（标记为inactive）或物理删除
        # 这里选择软删除以保留历史记录
        site.status = 'inactive'
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '站点已标记为 inactive',
            'data': {
                'id': site.id,
                'name': site.name,
                'status': site.status
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除站点失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'删除站点失败: {str(e)}'
        }), 500

@map_bp.route('/api/map/stats', methods=['GET'])
@token_required
def get_map_stats(current_user):
    """
    获取地图统计信息接口
    
    返回值：
        code: 200 - 获取成功
        message: str - 操作结果消息
        data: dict - 统计信息
            total_sites: int - 站点总数
            total_capacity_mwh: float - 总容量（MWh）
            total_power_mw: float - 总功率（MW）
            avg_soc_percent: float - 平均荷电状态百分比
            province_stats: list - 按省份统计
                每个元素为省份统计字典
                    adcode: str - 行政区划代码
                    site_count: int - 站点数量
                    total_capacity_mwh: float - 总容量（MWh）
                    total_power_mw: float - 总功率（MW）
    
    错误处理：
        500 - 获取地图统计失败
    """
    try:
        # 统计站点总数
        total_sites = EnergyStorageSite.query.filter_by(status='active').count()
        
        # 按省份统计
        province_stats = db.session.query(
            EnergyStorageSite.adcode,
            db.func.count(EnergyStorageSite.id).label('count'),
            db.func.sum(EnergyStorageSite.capacity_mwh).label('total_capacity'),
            db.func.sum(EnergyStorageSite.power_mw).label('total_power')
        ).filter_by(status='active').group_by(EnergyStorageSite.adcode).all()
        
        # 转换为字典
        province_data = []
        for stat in province_stats:
            province_data.append({
                'adcode': stat.adcode,
                'site_count': stat.count,
                'total_capacity_mwh': float(stat.total_capacity) if stat.total_capacity else 0,
                'total_power_mw': float(stat.total_power) if stat.total_power else 0
            })
        
        # 总体统计
        total_capacity = db.session.query(
            db.func.sum(EnergyStorageSite.capacity_mwh)
        ).filter_by(status='active').scalar() or 0
        
        total_power = db.session.query(
            db.func.sum(EnergyStorageSite.power_mw)
        ).filter_by(status='active').scalar() or 0
        
        avg_soc = db.session.query(
            db.func.avg(EnergyStorageSite.current_soc)
        ).filter_by(status='active').scalar() or 50.0
        
        stats_data = {
            'total_sites': total_sites,
            'total_capacity_mwh': float(total_capacity),
            'total_power_mw': float(total_power),
            'avg_soc_percent': round(float(avg_soc), 2),
            'province_stats': province_data
        }
        
        return jsonify({
            'code': 200,
            'message': '成功获取地图统计',
            'data': stats_data
        })
        
    except Exception as e:
        current_app.logger.error(f"获取地图统计失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取地图统计失败: {str(e)}'
        }), 500