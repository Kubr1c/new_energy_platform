"""
数据相关API路由
提供数据上传、查询和统计功能
"""

from flask import Blueprint, request, jsonify
from models.database import db, NewEnergyData
import pandas as pd
from datetime import datetime, timedelta
import io

data_bp = Blueprint('data', __name__)

@data_bp.route('/api/data/upload', methods=['POST'])
def upload_data():
    """
    上传CSV数据文件接口
    
    请求参数：
        file: file - CSV数据文件
    
    返回值：
        code: 200 - 上传成功
        message: str - 操作结果消息
    
    错误处理：
        400 - 没有文件、没有选择文件、不支持的文件格式或缺少必需的列
        500 - 数据处理错误
    """
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '没有文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 400, 'message': '没有选择文件'})
    
    if file and file.filename.endswith('.csv'):
        try:
            # 读取CSV文件
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            df = pd.read_csv(stream)
            
            # 验证必需的列
            required_columns = ['timestamp', 'wind_power', 'pv_power', 'load', 
                              'temperature', 'irradiance', 'wind_speed']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return jsonify({'code': 400, 'message': f'缺少必需的列: {missing_columns}'})
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 保存到数据库
            saved_count = 0
            for _, row in df.iterrows():
                # 检查是否已存在
                existing = NewEnergyData.query.filter_by(timestamp=row['timestamp']).first()
                if existing:
                    # 更新现有记录
                    existing.wind_power = row['wind_power']
                    existing.pv_power = row['pv_power']
                    existing.load = row['load']
                    existing.temperature = row['temperature']
                    existing.irradiance = row['irradiance']
                    existing.wind_speed = row['wind_speed']
                else:
                    # 创建新记录
                    new_data = NewEnergyData(
                        timestamp=row['timestamp'],
                        wind_power=row['wind_power'],
                        pv_power=row['pv_power'],
                        load=row['load'],
                        temperature=row['temperature'],
                        irradiance=row['irradiance'],
                        wind_speed=row['wind_speed']
                    )
                    db.session.add(new_data)
                    saved_count += 1
            
            db.session.commit()
            return jsonify({
                'code': 200, 
                'message': f'数据上传成功，新增{saved_count}条记录'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'code': 500, 'message': f'数据处理错误: {str(e)}'})
    
    return jsonify({'code': 400, 'message': '不支持的文件格式'})

@data_bp.route('/api/data/query', methods=['GET'])
def query_data():
    """
    查询历史数据接口
    
    查询参数：
        start_time: str - 开始时间（可选，格式：ISO 8601）
        end_time: str - 结束时间（可选，格式：ISO 8601）
        limit: int - 返回记录数（可选，默认为100）
    
    返回值：
        code: 200 - 查询成功
        data: list - 数据列表
            每个元素为数据记录字典
                timestamp: str - 时间戳
                wind_power: float - 风力发电量
                pv_power: float - 光伏发电量
                load: float - 负荷
                temperature: float - 温度
                irradiance: float - 辐照度
                wind_speed: float - 风速
    
    错误处理：
        500 - 查询错误
    """
    try:
        # 获取查询参数
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        limit = request.args.get('limit', 100, type=int)
        
        # 构建查询
        query = NewEnergyData.query
        
        if start_time:
            query = query.filter(NewEnergyData.timestamp >= datetime.fromisoformat(start_time))
        if end_time:
            query = query.filter(NewEnergyData.timestamp <= datetime.fromisoformat(end_time))
        
        # 执行查询
        data = query.order_by(NewEnergyData.timestamp.desc()).limit(limit).all()
        
        # 转换为JSON格式
        result = []
        for item in data:
            result.append({
                'timestamp': item.timestamp.isoformat(),
                'wind_power': item.wind_power,
                'pv_power': item.pv_power,
                'load': item.load,
                'temperature': item.temperature,
                'irradiance': item.irradiance,
                'wind_speed': item.wind_speed
            })
        
        return jsonify({'code': 200, 'data': result})
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询错误: {str(e)}'})

@data_bp.route('/api/data/latest', methods=['GET'])
def get_latest_data():
    """
    获取最新的小时级数据接口
    
    功能：获取数据库中时间戳最新的记录，用于仪表盘实时功率曲线展示
    
    查询参数：
        limit: int - 返回记录数（可选，默认为24，最大为168）
    
    返回值：
        code: 200 - 获取成功
        data: list - 数据列表（按时间升序排列）
            每个元素为数据记录字典
                timestamp: str - 时间戳
                wind_power: float - 风力发电量
                pv_power: float - 光伏发电量
                load: float - 负荷
                temperature: float - 温度
                irradiance: float - 辐照度
                wind_speed: float - 风速
    
    错误处理：
        500 - 查询错误
    """
    try:
        limit = request.args.get('limit', 24, type=int)
        limit = max(1, min(limit, 168))   # 限制在 1-168 之间

        # 获取当前时间
        from datetime import datetime, timedelta
        now = datetime.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # 查询当前小时及之前的数据
        # 首先尝试获取当前小时的数据
        current_hour_data = NewEnergyData.query.filter(
            NewEnergyData.timestamp >= current_hour,
            NewEnergyData.timestamp < current_hour + timedelta(hours=1)
        ).first()
        
        # 如果当前小时没有数据，获取前一个小时的数据
        if not current_hour_data:
            current_hour = current_hour - timedelta(hours=1)
            current_hour_data = NewEnergyData.query.filter(
                NewEnergyData.timestamp >= current_hour,
                NewEnergyData.timestamp < current_hour + timedelta(hours=1)
            ).first()
        
        # 确定要查询的时间范围
        if current_hour_data:
            # 从当前小时往前推 limit-1 小时
            start_time = current_hour - timedelta(hours=limit-1)
            end_time = current_hour + timedelta(hours=1)
            
            # 查询这个时间范围内的数据
            rows = NewEnergyData.query.filter(
                NewEnergyData.timestamp >= start_time,
                NewEnergyData.timestamp < end_time
            ).order_by(NewEnergyData.timestamp.asc()).all()
        else:
            # 如果没有找到任何数据，返回空列表
            rows = []

        result = [{
            'timestamp':   item.timestamp.isoformat(),
            'wind_power':  item.wind_power,
            'pv_power':    item.pv_power,
            'load':        item.load,
            'temperature': item.temperature,
            'irradiance':  item.irradiance,
            'wind_speed':  item.wind_speed,
        } for item in rows]

        return jsonify({'code': 200, 'data': result})

    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询错误: {str(e)}'})

@data_bp.route('/api/data/statistics', methods=['GET'])
def get_statistics():
    """
    获取数据统计信息接口
    
    返回值：
        code: 200 - 获取成功
        data: dict - 统计信息
            total_count: int - 数据总量
            date_range: dict - 时间范围
                start: str - 开始时间
                end: str - 结束时间
            statistics: dict - 统计数据
                wind_power: dict - 风力发电统计
                    avg: float - 平均值
                    max: float - 最大值
                pv_power: dict - 光伏发电统计
                    avg: float - 平均值
                    max: float - 最大值
                load: dict - 负荷统计
                    avg: float - 平均值
                    max: float - 最大值
    
    错误处理：
        500 - 统计错误
    """
    try:
        # 获取数据总量
        total_count = NewEnergyData.query.count()
        
        if total_count == 0:
            return jsonify({'code': 200, 'data': {
                'total_count': 0,
                'date_range': None,
                'statistics': None
            }})
        
        # 获取时间范围
        first_record = NewEnergyData.query.order_by(NewEnergyData.timestamp.asc()).first()
        last_record = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).first()
        
        # 获取基本统计信息
        stats = db.session.query(
            db.func.avg(NewEnergyData.wind_power).label('avg_wind'),
            db.func.max(NewEnergyData.wind_power).label('max_wind'),
            db.func.avg(NewEnergyData.pv_power).label('avg_pv'),
            db.func.max(NewEnergyData.pv_power).label('max_pv'),
            db.func.avg(NewEnergyData.load).label('avg_load'),
            db.func.max(NewEnergyData.load).label('max_load')
        ).first()
        
        return jsonify({'code': 200, 'data': {
            'total_count': total_count,
            'date_range': {
                'start': first_record.timestamp.isoformat(),
                'end': last_record.timestamp.isoformat()
            },
            'statistics': {
                'wind_power': {'avg': float(stats.avg_wind), 'max': float(stats.max_wind)},
                'pv_power': {'avg': float(stats.avg_pv), 'max': float(stats.max_pv)},
                'load': {'avg': float(stats.avg_load), 'max': float(stats.max_load)}
            }
        }})
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'统计错误: {str(e)}'})
