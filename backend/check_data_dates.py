"""
检查数据库中的日期数据，找出问题所在
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import db, NewEnergyData
from datetime import datetime, timedelta

# 导入Flask应用
from app import app

with app.app_context():
    # 获取当前时间
    now = datetime.now()
    print(f'当前时间: {now}')
    
    # 获取数据库中最新的10条数据
    latest_data = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).limit(10).all()
    
    print('\n数据库中最新的10条数据:')
    for i, data in enumerate(latest_data):
        print(f'{i+1}. 时间: {data.timestamp}, 风电={data.wind_power:.2f}, 光伏={data.pv_power:.2f}, 负荷={data.load:.2f}')
    
    # 检查是否有未来日期的数据
    future_data = NewEnergyData.query.filter(NewEnergyData.timestamp > now).all()
    
    print(f'\n未来日期的数据条数: {len(future_data)}')
    if future_data:
        print('未来日期的数据:')
        for data in future_data[:10]:
            print(f'  时间: {data.timestamp}, 光伏={data.pv_power:.2f} MW')
    
    # 检查今天的数据
    today = now.date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = today_start + timedelta(days=1)
    
    today_data = NewEnergyData.query.filter(
        NewEnergyData.timestamp >= today_start,
        NewEnergyData.timestamp < today_end
    ).order_by(NewEnergyData.timestamp.asc()).all()
    
    print(f'\n今天({today})的数据:')
    for data in today_data:
        print(f'  时间: {data.timestamp}, 光伏={data.pv_power:.2f} MW')
    
    # 测试API逻辑
    print('\n测试API逻辑:')
    limit = 24
    
    # 先查询今天的数据是否存在
    today_data_count = NewEnergyData.query.filter(
        NewEnergyData.timestamp >= today_start,
        NewEnergyData.timestamp < today_end
    ).count()
    
    print(f'今天的数据条数: {today_data_count}')
    
    # 根据是否有今天的数据，选择不同的查询方式
    if today_data_count > 0:
        # 查询今天的数据，按时间降序排列，取最新的limit条
        subq = (
            NewEnergyData.query
            .filter(
                NewEnergyData.timestamp >= today_start,
                NewEnergyData.timestamp < today_end
            )
            .order_by(NewEnergyData.timestamp.desc())
            .limit(limit)
            .subquery()
        )
        print('使用今天的数据')
    else:
        # 如果今天没有数据，使用所有数据中的最新记录
        subq = (
            NewEnergyData.query
            .order_by(NewEnergyData.timestamp.desc())
            .limit(limit)
            .subquery()
        )
        print('使用所有数据中的最新记录')
    
    # 执行查询
    from sqlalchemy import select
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
    
    print('\nAPI返回的数据:')
    for i, data in enumerate(rows[:10]):
        print(f'{i+1}. 时间: {data.timestamp}, 光伏={data.pv_power:.2f} MW')
