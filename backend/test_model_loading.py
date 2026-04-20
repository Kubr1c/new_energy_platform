from app import create_app
from models.predict import Predictor
from models.database import db, NewEnergyData
import pandas as pd
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # 获取最近24小时的数据作为输入
    rows = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).limit(24).all()
    rows = list(reversed(rows))  # 时间升序
    
    if len(rows) < 24:
        print('数据不足24小时，无法测试模型')
        exit()
    
    # 构建输入数据
    data = pd.DataFrame([{
        'timestamp': r.timestamp,
        'wind_power': r.wind_power or 0.0,
        'pv_power': r.pv_power or 0.0,
        'load': r.load or 0.0,
        'temperature': r.temperature or 0.0,
        'irradiance': r.irradiance or 0.0,
        'wind_speed': r.wind_speed or 0.0,
    } for r in rows])
    
    print(f'输入数据时间范围: {data.timestamp.min()} 到 {data.timestamp.max()}')
    print(f'输入数据长度: {len(data)}')
    
    # 测试不同模型
    model_types = ['attention_lstm', 'cnn_lstm', 'standard_lstm', 'gru', 'transformer']
    
    for model_type in model_types:
        print(f'\n=== 测试模型: {model_type} ===')
        try:
            predictor = Predictor(model_type=model_type)
            print(f'模型类型: {predictor.model_type}')
            print(f'模型是否加载: {predictor.model is not None}')
            print(f'预处理器是否加载: {predictor.preprocessor is not None}')
            
            # 进行预测
            prediction = predictor.predict(data)
            print(f'预测结果:')
            print(f'  风电: {prediction.get("wind_power", "N/A")}')
            print(f'  光伏: {prediction.get("pv_power", "N/A")}')
            print(f'  负荷: {prediction.get("load", "N/A")}')
            
        except Exception as e:
            print(f'测试失败: {e}')
