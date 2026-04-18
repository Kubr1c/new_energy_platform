import torch
import numpy as np
import pandas as pd
from .model_registry import get_model, MODEL_REGISTRY
from preprocessing.data_utils import DataPreprocessor
import os

class Predictor:
    def __init__(self, model_path=None, model_type='attention_lstm', input_len=24, feature_cols=None, target_cols=None):
        self.input_len = input_len
        self.model_type = model_type
        self.feature_cols = feature_cols or ['wind_power', 'pv_power', 'load', 'temperature', 'irradiance', 'wind_speed']
        self.target_cols = target_cols or ['wind_power', 'pv_power', 'load']
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 模型路径：按 model_type 区分
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'models_saved',
                f'{model_type}.pth'
            )
        
        # 通过模型注册表实例化模型
        input_size = len(self.feature_cols)
        output_size = len(self.target_cols)   # 单步预测
        self.model = get_model(model_type, input_size, output_size).to(self.device)
        
        if os.path.exists(model_path):
            # weights_only=True 防止 pickle 任意代码执行（PyTorch >= 1.13）
            try:
                state_dict = torch.load(model_path, map_location=self.device, weights_only=True)
            except TypeError:
                # 旧版 PyTorch 不支持 weights_only 参数
                state_dict = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            print(f"[{model_type}] 模型权重加载成功: {model_path}")
        else:
            print(f"Warning: Model file {model_path} not found for {model_type}. Using untrained model.")
        
        self.model.eval()
        self.preprocessor = DataPreprocessor()
        self.preprocessor.load_scaler()
    
    def predict(self, recent_data):
        """
        recent_data: DataFrame 包含最近 input_len 小时的数据，列包括 feature_cols
        返回: dict, 包含预测的风电、光伏、负荷值（原始量纲）
        """
        # 确保数据长度正确
        if len(recent_data) < self.input_len:
            raise ValueError(f"需要至少 {self.input_len} 个时间步的数据，当前只有 {len(recent_data)} 个")
        
        # 取最近的 input_len 个数据点
        data = recent_data.tail(self.input_len)[self.feature_cols]
        
        # 归一化
        try:
            scaled = self.preprocessor.normalize(data, fit=False)
        except Exception as e:
            print(f"归一化失败，使用简单预测: {e}")
            return self._simple_predict(recent_data)
        
        # 转为tensor (1, input_len, n_features)
        input_tensor = torch.tensor(scaled.values, dtype=torch.float32).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            try:
                pred_norm = self.model(input_tensor).cpu().numpy().flatten()
            except Exception as e:
                print(f"模型预测失败，使用简单预测: {e}")
                return self._simple_predict(recent_data)
        
        # 反归一化：需要分别处理每个目标变量
        pred_original = {}
        for i, col in enumerate(self.target_cols):
            # 为每个目标变量创建单独的反归一化
            try:
                pred_original[col] = self.preprocessor.inverse_transform(pred_norm[i], [col])
            except Exception as e:
                print(f"反归一化失败，使用简单预测: {e}")
                return self._simple_predict(recent_data)
        
        return pred_original
    
    def _simple_predict(self, recent_data):
        """简单的统计预测方法，基于历史数据的趋势和周期性"""
        data = recent_data.tail(self.input_len)
        
        # 获取最近几个小时的平均值和趋势
        recent_wind = data['wind_power'].values
        recent_pv = data['pv_power'].values
        recent_load = data['load'].values
        
        # 风电预测：基于最近值的加权平均，加入随机波动
        wind_avg = np.mean(recent_wind[-6:])  # 最近6小时平均
        wind_trend = recent_wind[-1] - recent_wind[-6] if len(recent_wind) >= 6 else 0
        wind_pred = max(0, wind_avg + wind_trend * 0.3 + np.random.normal(0, 1))
        
        # 光伏预测：基于时间周期性（白天有发电）
        current_hour = data.iloc[-1]['timestamp'].hour
        if 6 <= current_hour < 18:
            # 白天：基于最近光伏值和辐照度
            pv_avg = np.mean(recent_pv[-6:]) if len(recent_pv) >= 6 else np.mean(recent_pv)
            pv_pred = max(0, pv_avg * (0.8 + np.random.uniform(-0.1, 0.1)))
        else:
            # 夜晚：光伏为0
            pv_pred = 0.0
        
        # 负荷预测：基于最近值和时段特征
        load_avg = np.mean(recent_load[-6:]) if len(recent_load) >= 6 else np.mean(recent_load)
        load_trend = recent_load[-1] - recent_load[-6] if len(recent_load) >= 6 else 0
        
        # 根据时段调整负荷预测
        if 7 <= current_hour < 9 or 18 <= current_hour < 21:
            # 高峰时段
            load_pred = load_avg * 1.1 + load_trend * 0.2
        elif 9 <= current_hour < 18:
            # 白天时段
            load_pred = load_avg + load_trend * 0.1
        else:
            # 夜间时段
            load_pred = load_avg * 0.9 + load_trend * 0.1
        
        load_pred = max(0, load_pred)
        
        return {
            'wind_power': wind_pred,
            'pv_power': pv_pred,
            'load': load_pred
        }
    
    def predict_batch(self, data_list):
        """批量预测"""
        results = []
        for data in data_list:
            result = self.predict(data)
            results.append(result)
        return results
