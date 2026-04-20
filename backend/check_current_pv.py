"""
检查当前时间的光伏功率数据
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
    
    # 获取当前小时的数据
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    next_hour = current_hour + timedelta(hours=1)
    
    print(f'当前小时: {current_hour}')
    print(f'下一小时: {next_hour}')
    
    # 查询当前小时的数据
    current_data = NewEnergyData.query.filter(
        NewEnergyData.timestamp >= current_hour,
        NewEnergyData.timestamp < next_hour
    ).first()
    
    if current_data:
        print(f'当前小时数据:')
        print(f'  时间: {current_data.timestamp}')
        print(f'  风电功率: {current_data.wind_power:.2f} MW')
        print(f'  光伏功率: {current_data.pv_power:.2f} MW')
        print(f'  负荷: {current_data.load:.2f} MW')
        print(f'  温度: {current_data.temperature:.2f} °C')
        print(f'  辐照度: {current_data.irradiance:.2f} W/m²')
        print(f'  风速: {current_data.wind_speed:.2f} m/s')
    else:
        print('当前小时没有数据')
    
    # 获取最新的24条数据
    latest_data = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).limit(24).all()
    
    print('\n最新24条数据:')
    for i, data in enumerate(latest_data[:10]):
        print(f'{i+1}. {data.timestamp}: 风电={data.wind_power:.2f}, 光伏={data.pv_power:.2f}, 负荷={data.load:.2f}')
    
    # 检查是否有今天的数据
    today = now.date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = today_start + timedelta(days=1)
    
    today_data = NewEnergyData.query.filter(
        NewEnergyData.timestamp >= today_start,
        NewEnergyData.timestamp < today_end
    ).all()
    
    print(f'\n今天的数据条数: {len(today_data)}')
    if today_data:
        print('今天的数据:')
        for data in today_data:
            print(f'  {data.timestamp}: 光伏={data.pv_power:.2f} MW')
