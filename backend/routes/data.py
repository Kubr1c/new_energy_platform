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

    策略：取数据库中时间戳最新的 24 条记录（按时间升序返回），
    不依赖系统时钟，确保即使数据未实时更新也能正常显示历史曲线。
    可通过 ?limit=N 参数自定义返回条数（最大 168，即 7 天）。
    """
    try:
        limit = request.args.get('limit', 24, type=int)
        limit = max(1, min(limit, 168))   # 限制在 1-168 之间

        # 取最新 limit 条，再按时间升序排列（用于图表从左到右展示）
        subq = (
            NewEnergyData.query
            .order_by(NewEnergyData.timestamp.desc())
            .limit(limit)
            .subquery()
        )
        from sqlalchemy import select
        from models.database import db
        rows = (
            db.session.execute(
                select(NewEnergyData)
                .where(NewEnergyData.id.in_(
                    select(subq.c.id)
                ))
                .order_by(NewEnergyData.timestamp.asc())
            )
            .scalars()
            .all()
        )

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


@data_bp.route('/api/data/dataset_date', methods=['GET'])
def get_dataset_date():
    """
    返回数据集中的最新日期信息，供前端替代 new Date() 使用。

    返回：
      latest_date      : 数据集最新记录的日期字符串 (YYYY-MM-DD)
      latest_datetime  : 数据集最新记录的完整时间 (ISO 格式)
      latest_hour      : 最新记录的小时数 (0-23)，供 SOC 曲线索引使用
      earliest_date    : 数据集最早记录的日期字符串 (YYYY-MM-DD)
      dispatch_default : 建议用于调度日期选择器的默认日期 (YYYY-MM-DD)
                         取数据集内最后一个完整天（即最新日期往前一天，
                         确保那一天有 24 条完整的小时级数据）
    """
    try:
        latest = NewEnergyData.query.order_by(
            NewEnergyData.timestamp.desc()
        ).first()

        earliest = NewEnergyData.query.order_by(
            NewEnergyData.timestamp.asc()
        ).first()

        if not latest:
            return jsonify({'code': 404, 'message': '数据库中没有数据'})

        latest_date = latest.timestamp.date()
        latest_hour = latest.timestamp.hour

        # 调度默认日期：取最新日期当天，若当天数据不足24条则退一天
        day_count = NewEnergyData.query.filter(
            db.func.date(NewEnergyData.timestamp) == latest_date
        ).count()

        if day_count >= 24:
            dispatch_default = latest_date.isoformat()
        else:
            # 退到前一天
            from datetime import timedelta
            prev_day = latest_date - timedelta(days=1)
            dispatch_default = prev_day.isoformat()

        return jsonify({
            'code': 200,
            'data': {
                'latest_date':     latest_date.isoformat(),
                'latest_datetime': latest.timestamp.isoformat(),
                'latest_hour':     latest_hour,
                'earliest_date':   earliest.timestamp.date().isoformat(),
                'dispatch_default': dispatch_default,
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取数据集日期失败: {str(e)}'})
