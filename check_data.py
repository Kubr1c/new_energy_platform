import sys
import os

# 添加backend目录到Python路径
sys.path.append('backend')

from models.database import db, NewEnergyData
from app import create_app

# 创建应用实例
app = create_app()

with app.app_context():
    # 查询最近24条数据
    data = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).limit(24).all()
    
    print('最近24条数据:')
    for item in data:
        print(f'Time: {item.timestamp}, PV: {item.pv_power}, Wind: {item.wind_power}, Load: {item.load}')
    
    print('\n光伏数据统计:')
    pv_values = [item.pv_power for item in data if item.pv_power is not None]
    print(f'非空值数量: {len(pv_values)}')
    if pv_values:
        print(f'平均值: {sum(pv_values)/len(pv_values):.2f}')
        print(f'最大值: {max(pv_values):.2f}')
    else:
        print('平均值: 0')
        print('最大值: 0')
    
    # 检查所有光伏数据
    all_pv_data = NewEnergyData.query.with_entities(NewEnergyData.pv_power).all()
    all_pv_values = [item[0] for item in all_pv_data if item[0] is not None]
    print('\n所有光伏数据统计:')
    print(f'总记录数: {len(all_pv_data)}')
    print(f'非空值数量: {len(all_pv_values)}')
    if all_pv_values:
        print(f'平均值: {sum(all_pv_values)/len(all_pv_values):.2f}')
        print(f'最大值: {max(all_pv_values):.2f}')
    else:
        print('平均值: 0')
        print('最大值: 0')