import sys
import os

# 添加backend目录到Python路径
sys.path.append('backend')

from models.predict import Predictor
import pandas as pd
from datetime import datetime, timedelta

# 创建测试数据
index = pd.date_range('2026-05-20 00:00:00', periods=24, freq='H')
data = {
    'timestamp': index,
    'wind_power': [20.0]*24,
    'pv_power': [0,0,0,0,0,3,8,15,25,35,45,55,60,58,50,40,30,10,2,0,0,0,0,0],
    'load': [25.0]*24,
    'temperature': [20.0]*24,
    'irradiance': [0,0,0,0,0,50,100,200,300,400,500,600,700,650,550,450,350,200,100,0,0,0,0,0],
    'wind_speed': [5.0]*24
}
df = pd.DataFrame(data)

# 测试预测器
predictor = Predictor(model_type='transformer')

# 测试单步预测
print('单步预测结果:')
result = predictor.predict(df)
print(f'PV预测值: {result['pv_power']}')
print(f'Wind预测值: {result['wind_power']}')
print(f'Load预测值: {result['load']}')

# 测试批量预测
print('\n批量预测测试:')
predictions = {'wind_power': [], 'pv_power': [], 'load': []}
current_data = df.copy()

for hour in range(24):
    pred = predictor.predict(current_data)
    print(f'Hour {hour}: PV prediction = {pred['pv_power']}')
    predictions['pv_power'].append(pred['pv_power'])
    
    # 更新数据
    next_timestamp = current_data.iloc[-1]['timestamp'] + timedelta(hours=1)
    next_row = {
        'timestamp': next_timestamp,
        'wind_power': pred['wind_power'],
        'pv_power': pred['pv_power'],
        'load': pred['load'],
        'temperature': current_data.iloc[-1]['temperature'],
        'irradiance': current_data.iloc[-1]['irradiance'],
        'wind_speed': current_data.iloc[-1]['wind_speed']
    }
    current_data = pd.concat([current_data.iloc[1:], pd.DataFrame([next_row])], ignore_index=True)

print('\n批量预测结果:')
print(predictions['pv_power'])