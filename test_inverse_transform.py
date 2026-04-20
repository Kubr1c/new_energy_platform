import sys
import os

# 添加backend目录到Python路径
sys.path.append('backend')

from preprocessing.data_utils import DataPreprocessor
import numpy as np

# 测试反归一化功能
preprocessor = DataPreprocessor()

# 测试标量反归一化
print('测试标量反归一化:')
test_value = 0.5
result = preprocessor.inverse_transform(test_value, ['pv_power'])
print(f'输入: {test_value}')
print(f'输出: {result}')
print(f'类型: {type(result)}')

# 测试数组反归一化
print('\n测试数组反归一化:')
test_array = np.array([0.5])
result = preprocessor.inverse_transform(test_array, ['pv_power'])
print(f'输入: {test_array}')
print(f'输出: {result}')
print(f'类型: {type(result)}')

# 测试预测器的反归一化
print('\n测试预测器的反归一化:')
from models.predict import Predictor
predictor = Predictor(model_type='attention_lstm')

# 创建测试数据
import pandas as pd
from datetime import datetime, timedelta

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

# 测试预测
result = predictor.predict(df)
print(f'预测结果:')
print(f'PV预测值: {result['pv_power']}')
print(f'类型: {type(result['pv_power'])}')
print(f'Wind预测值: {result['wind_power']}')
print(f'类型: {type(result['wind_power'])}')
print(f'Load预测值: {result['load']}')
print(f'类型: {type(result['load'])}')
