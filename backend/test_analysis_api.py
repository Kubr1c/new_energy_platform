import requests
import json

# 测试分析API
url = 'http://localhost:5000/api/analysis/model_compare'
payload = {
    'models': ['attention_lstm', 'cnn_lstm', 'standard_lstm'],
    'mode': 'realtime'
}

response = requests.post(url, json=payload)
print('状态码:', response.status_code)

if response.status_code == 200:
    data = response.json()
    print('\n返回模式:', data.get('data', {}).get('mode'))
    
    gt = data.get('data', {}).get('ground_truth')
    if gt:
        print('\n真实值时间戳:', gt.get('timestamps', [])[:3])
        print('日期标签:', gt.get('date_label'))
        print('上下文信息:', data.get('data', {}).get('context_info'))
    
    results = data.get('data', {}).get('results', {})
    print('\n模型预测数据:')
    for model_name, model_data in results.items():
        predictions = model_data.get('predictions', {})
        load_data = predictions.get('load', [])
        print(f'{model_name}: 负荷预测数据长度 = {len(load_data)}')
        if load_data:
            print(f'  前3个值: {load_data[:3]}')
else:
    print('API调用失败:', response.text)
