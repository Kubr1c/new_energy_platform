import requests
import json

# 测试TFT模型的预测结果
url = "http://localhost:5000/api/predict/batch"
payload = {
    "model": "tft",
    "predict_type": "综合预测",
    "predict_hours": 24
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

if response.status_code == 200:
    data = response.json()
    print("预测结果:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # 检查光伏预测值是否有负值
    if "data" in data and "predictions" in data["data"]:
        predictions = data["data"]["predictions"]
        pv_predictions = [p["pv_power"] for p in predictions]
        print("\n光伏预测值:")
        for i, pv in enumerate(pv_predictions):
            print(f"小时 {i}: {pv}")
        
        # 检查是否有负值
        negative_pv = [i for i, pv in enumerate(pv_predictions) if pv < 0]
        if negative_pv:
            print(f"\n警告: 发现负值光伏预测值在小时: {negative_pv}")
        else:
            print("\n成功: 所有光伏预测值均为非负")
else:
    print(f"请求失败，状态码: {response.status_code}")
    print(response.text)