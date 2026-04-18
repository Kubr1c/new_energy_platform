import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
from numbers import Number

class DataPreprocessor:
    def __init__(self, scaler_path=None):
        self.scaler = None
        # __file__ 位于 backend/preprocessing/data_utils.py
        # scaler 位于 backend/data/scaler.pkl，故向上一级再进入 data/
        self.scaler_path = scaler_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'data', 'scaler.pkl'
        )

    def handle_missing(self, df, method='linear'):
        """缺失值处理：线性插值或同期均值"""
        if method == 'linear':
            df = df.interpolate(method='linear', limit=3)
        # 对于连续大段缺失（>3），可用同期均值填充，此处简化
        return df.ffill().bfill()

    def detect_outliers(self, series, threshold=3):
        """3σ 异常检测"""
        mean = series.mean()
        std = series.std()
        return (series < mean - threshold*std) | (series > mean + threshold*std)

    def fix_outliers(self, df, columns):
        """用中位数替换异常值"""
        for col in columns:
            outliers = self.detect_outliers(df[col])
            median = df[col].median()
            df.loc[outliers, col] = median
        return df

    def normalize(self, df, fit=True):
        """Min-Max归一化"""
        if fit:
            self.scaler = MinMaxScaler()
            scaled = self.scaler.fit_transform(df)
            joblib.dump(self.scaler, self.scaler_path)
        else:
            self.scaler = joblib.load(self.scaler_path)
            scaled = self.scaler.transform(df)
        return pd.DataFrame(scaled, columns=df.columns, index=df.index)

    def inverse_transform(self, data, columns):
        """反归一化"""
        if self.scaler is None:
            self.scaler = joblib.load(self.scaler_path)

        # 统一转成二维数组，兼容 python 标量 / numpy 标量 / 1D / 2D
        if isinstance(data, Number) or np.isscalar(data):
            data_2d = np.array([[float(data)]], dtype=float)
        else:
            arr = np.array(data, dtype=float)
            if arr.ndim == 1:
                data_2d = arr.reshape(1, -1)
            elif arr.ndim == 2:
                data_2d = arr
            else:
                raise ValueError(f"inverse_transform 仅支持标量、1维或2维数据，当前维度: {arr.ndim}")
        
        # 创建一个与原始scaler相同维度的dummy数组
        n_features = len(self.scaler.feature_names_in_)
        dummy = np.zeros((data_2d.shape[0], n_features))
        
        # 找到目标列在原始数据中的索引位置
        feature_names = list(self.scaler.feature_names_in_)
        target_indices = [feature_names.index(col) for col in columns if col in feature_names]
        
        # 填充目标数据
        for i, idx in enumerate(target_indices):
            if i < data_2d.shape[1]:
                dummy[:, idx] = data_2d[:, i]
        
        # 反归一化
        result = self.scaler.inverse_transform(dummy)
        
        # 提取目标列的结果
        if len(target_indices) == 1:
            return result[:, target_indices[0]]
        else:
            return result[:, target_indices]

    def create_sequences(self, data, input_len=24, output_len=1):
        """滑动窗口构造监督学习样本"""
        X, y = [], []
        for i in range(len(data) - input_len - output_len + 1):
            X.append(data[i:i+input_len])
            y.append(data[i+input_len:i+input_len+output_len])
        return np.array(X), np.array(y)

    def load_scaler(self):
        """加载归一化器"""
        if os.path.exists(self.scaler_path):
            self.scaler = joblib.load(self.scaler_path)
        return self.scaler
