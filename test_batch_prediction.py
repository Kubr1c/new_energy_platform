import sys
import os

# 添加backend目录到Python路径
sys.path.append('backend')

from models.predict import Predictor
import pandas as pd
from datetime import datetime, timedelta

# 创建测试数据
index = pd.date_range('2026-05-20 00:00:00', periods=24, freq='h')
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

# 测试批量预测
print('批量预测测试:')
predictions = {'wind_power': [], 'pv_power': [], 'load': []}
current_data = df.copy()

for hour in range(24):
    next_timestamp = current_data.iloc[-1]['timestamp'] + timedelta(hours=1)
    predict_hour = next_timestamp.hour
    
    pred = predictor.predict(current_data, predict_hour)
    print(f'Hour {hour} ({predict_hour}:00): PV prediction = {pred['pv_power']}')
    predictions['pv_power'].append(pred['pv_power'])
    
    # 更新数据
    next_row = {
        'timestamp': next_timestamp,
        'wind_power': pred['wind_power'],
        'pv_power': pred['pv_power'],
        'load': pred['load'],
        'temperature': current_data.iloc[-1]['temperature'],
        'irradiance': 500.0 if 6 <= predict_hour < 18 else 0.0,
        'wind_speed': current_data.iloc[-1]['wind_speed']
    }
    current_data = pd.concat([current_data.iloc[1:], pd.DataFrame([next_row])], ignore_index=True)

print('\n批量预测结果 (PV):')
for i, val in enumerate(predictions['pv_power']):
    print(f'{i}:00: {val}')

# 统计分析
pv_values = predictions['pv_power']
non_zero_pv = [v for v in pv_values if v > 0]
print('\n统计分析:')
print(f'总预测点数: {len(pv_values)}')
print(f'非零预测点数: {len(non_zero_pv)}')
if non_zero_pv:
    print(f'最大光伏预测值: {max(non_zero_pv):.2f}')
    print(f'最小光伏预测值: {min(non_zero_pv):.2f}')
    print(f'平均光伏预测值: {sum(non_zero_pv)/len(non_zero_pv):.2f}')
else:
    print('所有光伏预测值均为0')