from flask import Blueprint, request, jsonify
from models.database import db, NewEnergyData
import pandas as pd
from datetime import datetime, timedelta
import io

data_bp = Blueprint('data', __name__)

@data_bp.route('/api/data/upload', methods=['POST'])
def upload_data():
    """上传CSV数据文件"""
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
    """查询历史数据"""
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
    获取最新的 24 条小时级数据，用于仪表盘实时功率曲线展示。

    双模式设计：
    - 近期模式（7天内有数据）：返回最新 24 条，附 mode='realtime'
    - 历史回放模式（无近期数据）：返回数据库中最新一整天（00:00~23:00）
      的 24 条，附 mode='history' 和 data_date 字段提示前端显示标注
    """
    try:
        limit = request.args.get('limit', 24, type=int)
        limit = max(1, min(limit, 168))

        # 判断是否有近期数据（7天内）
        from datetime import timezone
        now_utc   = datetime.utcnow()
        week_ago  = now_utc - timedelta(days=7)
        recent_count = NewEnergyData.query.filter(
            NewEnergyData.timestamp >= week_ago
        ).count()

        if recent_count > 0:
            # 近期模式：直接取最新 limit 条
            mode = 'realtime'
            rows = (
                NewEnergyData.query
                .order_by(NewEnergyData.timestamp.desc())
                .limit(limit)
                .all()
            )
            rows = list(reversed(rows))
            data_date = None
        else:
            # 历史回放模式：取数据库最新一天 00:00~23:59 的数据
            mode = 'history'
            last = NewEnergyData.query.order_by(
                NewEnergyData.timestamp.desc()
            ).first()
            if last is None:
                return jsonify({'code': 200, 'data': [], 'mode': 'empty'})

            day_start = last.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end   = day_start + timedelta(hours=24)
            rows = (
                NewEnergyData.query
                .filter(
                    NewEnergyData.timestamp >= day_start,
                    NewEnergyData.timestamp <  day_end,
                )
                .order_by(NewEnergyData.timestamp.asc())
                .limit(limit)
                .all()
            )
            data_date = day_start.strftime('%Y-%m-%d')

        result = [{
            'timestamp':   item.timestamp.isoformat(),
            'wind_power':  item.wind_power,
            'pv_power':    item.pv_power,
            'load':        item.load,
            'temperature': item.temperature,
            'irradiance':  item.irradiance,
            'wind_speed':  item.wind_speed,
        } for item in rows]

        return jsonify({
            'code':      200,
            'data':      result,
            'mode':      mode,
            'data_date': data_date,   # None=realtime, 'YYYY-MM-DD'=history
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询错误: {str(e)}'})

@data_bp.route('/api/data/statistics', methods=['GET'])
def get_statistics():
    """获取数据统计信息"""
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
