import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
from numbers import Number
from datetime import datetime

class DataPreprocessor:
    """数据预处理类
    
    该类提供了一系列数据预处理功能，包括：
    - 缺失值处理
    - 异常值检测与修复
    - 数据归一化与反归一化
    - 序列数据创建
    - 特征工程
    
    主要用于新能源发电预测系统中的数据预处理环节，确保模型输入数据的质量和一致性。
    """
    
    def __init__(self, scaler_path=None):
        """初始化数据预处理器
        
        Args:
            scaler_path (str, optional): 归一化器保存路径。如果不指定，默认保存到 backend/data/scaler.pkl
        """
        self.scaler = None
        # __file__ 位于 backend/preprocessing/data_utils.py
        # scaler 位于 backend/data/scaler.pkl，故向上一级再进入 data/
        self.scaler_path = scaler_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'data', 'scaler.pkl'
        )

    def handle_missing(self, df, method='spline'):
        """缺失值处理：多种插值方法
        
        Args:
            df (pd.DataFrame): 包含缺失值的DataFrame
            method (str, optional): 缺失值处理方法，可选值：'linear', 'spline', 'polynomial'
            
        Returns:
            pd.DataFrame: 处理后的数据
        """
        if method == 'spline':
            # 使用样条插值，更适合非线性数据
            df = df.interpolate(method='spline', order=3, limit=5)
        elif method == 'polynomial':
            # 使用多项式插值
            df = df.interpolate(method='polynomial', order=2, limit=5)
        else:
            # 默认使用线性插值
            df = df.interpolate(method='linear', limit=5)
        
        # 对于连续大段缺失（>5），使用前向填充和后向填充的组合方法
        # 先后向填充，再前向填充，确保边缘数据也能被填充
        df = df.bfill().ffill()
        
        return df

    def detect_outliers(self, series, method='iqr', threshold=1.5):
        """异常值检测
        
        Args:
            series (pd.Series): 待检测的序列数据
            method (str, optional): 异常值检测方法，可选值：'zscore', 'iqr'
            threshold (float, optional): 异常值检测阈值
            
        Returns:
            pd.Series: 布尔型序列，标记异常值位置
        """
        if method == 'zscore':
            # 使用Z-score方法
            mean = series.mean()
            std = series.std()
            return (series < mean - threshold*std) | (series > mean + threshold*std)
        else:
            # 默认使用IQR方法
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            return (series < lower_bound) | (series > upper_bound)

    def detect_outliers_isolation_forest(self, df, columns, contamination=0.01):
        """使用孤立森林检测异常值
        
        Args:
            df (pd.DataFrame): 输入数据
            columns (list): 需要检测异常值的列名列表
            contamination (float, optional): 异常值比例，默认为0.01
            
        Returns:
            pd.DataFrame: 包含异常值标记的布尔矩阵
        """
        from sklearn.ensemble import IsolationForest
        
        # 提取需要检测的列
        data = df[columns]
        
        # 初始化孤立森林
        iso_forest = IsolationForest(contamination=contamination, random_state=42)
        
        # 拟合模型并预测
        outliers = iso_forest.fit_predict(data)
        
        # 将预测结果转换为布尔值（-1表示异常）
        outlier_mask = outliers == -1
        
        # 创建异常值标记矩阵
        outlier_df = pd.DataFrame(False, index=df.index, columns=columns)
        for col in columns:
            outlier_df[col] = outlier_mask
        
        return outlier_df

    def fix_outliers(self, df, columns, method='median'):
        """智能修复异常值
        
        Args:
            df (pd.DataFrame): 包含异常值的数据
            columns (list): 需要检测和修复异常值的列名列表
            method (str, optional): 修复方法，可选值：'median', 'mean', 'interpolate'
            
        Returns:
            pd.DataFrame: 修复异常值后的数据
        """
        for col in columns:
            # 检测当前列的异常值
            outliers = self.detect_outliers(df[col])
            
            if outliers.any():
                if method == 'interpolate':
                    # 使用插值方法修复异常值
                    # 先标记异常值为NaN
                    df.loc[outliers, col] = np.nan
                    # 然后进行插值
                    df[col] = df[col].interpolate(method='spline', order=3)
                elif method == 'mean':
                    # 使用均值修复异常值
                    mean_val = df.loc[~outliers, col].mean()
                    df.loc[outliers, col] = mean_val
                else:
                    # 默认使用中位数修复异常值
                    median_val = df.loc[~outliers, col].median()
                    df.loc[outliers, col] = median_val
        
        return df

    def add_outlier_flags(self, df, columns):
        """添加异常值标记
        
        Args:
            df (pd.DataFrame): 输入数据
            columns (list): 需要检测异常值的列名列表
            
        Returns:
            pd.DataFrame: 添加异常值标记后的数据
        """
        for col in columns:
            # 检测异常值
            outliers = self.detect_outliers(df[col])
            # 添加异常值标记列
            df[f'{col}_is_outlier'] = outliers.astype(int)
        
        return df

    def quality_check(self, df):
        """数据质量检查
        
        Args:
            df (pd.DataFrame): 输入数据
            
        Returns:
            dict: 数据质量报告
        """
        report = {}
        
        # 检查缺失值
        report['missing_values'] = df.isnull().sum().to_dict()
        
        # 检查异常值
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        outlier_report = {}
        for col in numeric_cols:
            outliers = self.detect_outliers(df[col])
            outlier_report[col] = {
                'count': outliers.sum(),
                'percentage': (outliers.sum() / len(df)) * 100
            }
        report['outliers'] = outlier_report
        
        # 检查数据范围
        range_report = {}
        for col in numeric_cols:
            range_report[col] = {
                'min': df[col].min(),
                'max': df[col].max(),
                'mean': df[col].mean(),
                'std': df[col].std()
            }
        report['range'] = range_report
        
        return report
    
    def calculate_correlation(self, df, target_col):
        """计算特征与目标变量的相关系数
        
        Args:
            df (pd.DataFrame): 输入数据
            target_col (str): 目标变量列名
            
        Returns:
            pd.Series: 各特征与目标变量的相关系数
        """
        # 选择数值型特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # 计算相关系数
        correlations = df[numeric_cols].corr()[target_col].sort_values(ascending=False)
        
        return correlations
    
    def feature_importance(self, df, target_col, n_estimators=100):
        """使用随机森林评估特征重要性
        
        Args:
            df (pd.DataFrame): 输入数据
            target_col (str): 目标变量列名
            n_estimators (int, optional): 随机森林 estimators 数量
            
        Returns:
            pd.Series: 特征重要性排序
        """
        from sklearn.ensemble import RandomForestRegressor
        
        # 准备特征和目标变量
        X = df.drop(target_col, axis=1)
        y = df[target_col]
        
        # 选择数值型特征
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        X = X[numeric_cols]
        
        # 处理缺失值
        X = X.fillna(X.mean())
        
        # 训练随机森林
        rf = RandomForestRegressor(n_estimators=n_estimators, random_state=42)
        rf.fit(X, y)
        
        # 获取特征重要性
        importances = pd.Series(rf.feature_importances_, index=X.columns)
        importances = importances.sort_values(ascending=False)
        
        return importances
    
    def select_features(self, df, target_col, method='correlation', threshold=0.1):
        """特征选择
        
        Args:
            df (pd.DataFrame): 输入数据
            target_col (str): 目标变量列名
            method (str, optional): 选择方法，可选值：'correlation', 'importance'
            threshold (float, optional): 选择阈值
            
        Returns:
            list: 选择的特征列表
        """
        if method == 'importance':
            # 使用特征重要性选择
            importances = self.feature_importance(df, target_col)
            selected_features = importances[importances > threshold].index.tolist()
        else:
            # 默认使用相关性选择
            correlations = self.calculate_correlation(df, target_col)
            # 排除目标变量自身
            correlations = correlations.drop(target_col, errors='ignore')
            selected_features = correlations[abs(correlations) > threshold].index.tolist()
        
        # 确保目标变量不在特征列表中
        if target_col in selected_features:
            selected_features.remove(target_col)
        
        return selected_features
    
    def feature_selection_pipeline(self, df, target_col, correlation_threshold=0.1, importance_threshold=0.01):
        """特征选择 pipeline
        
        Args:
            df (pd.DataFrame): 输入数据
            target_col (str): 目标变量列名
            correlation_threshold (float, optional): 相关性阈值
            importance_threshold (float, optional): 重要性阈值
            
        Returns:
            dict: 特征选择结果
        """
        # 计算相关性
        correlations = self.calculate_correlation(df, target_col)
        
        # 计算特征重要性
        importances = self.feature_importance(df, target_col)
        
        # 基于相关性选择
        corr_selected = correlations[abs(correlations) > correlation_threshold].index.tolist()
        if target_col in corr_selected:
            corr_selected.remove(target_col)
        
        # 基于重要性选择
        imp_selected = importances[importances > importance_threshold].index.tolist()
        
        # 取交集
        final_selected = list(set(corr_selected) & set(imp_selected))
        
        # 结果报告
        result = {
            'correlation_selection': corr_selected,
            'importance_selection': imp_selected,
            'final_selection': final_selected,
            'correlations': correlations.to_dict(),
            'importances': importances.to_dict()
        }
        
        return result
    
    def reduce_dimension_pca(self, df, n_components=0.95):
        """使用PCA进行特征降维
        
        Args:
            df (pd.DataFrame): 输入数据
            n_components (float or int, optional): 主成分数量或方差解释率
            
        Returns:
            tuple: (降维后的数据, 解释方差比)
        """
        from sklearn.decomposition import PCA
        
        # 选择数值型特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        X = df[numeric_cols]
        
        # 处理缺失值
        X = X.fillna(X.mean())
        
        # 初始化PCA
        pca = PCA(n_components=n_components, random_state=42)
        
        # 拟合并转换
        X_reduced = pca.fit_transform(X)
        
        # 解释方差比
        explained_variance_ratio = pca.explained_variance_ratio_
        
        return X_reduced, explained_variance_ratio

    def normalize(self, df, fit=True):
        """Min-Max归一化
        
        将数据缩放到[0, 1]区间，适用于需要统一量纲的模型输入
        
        Args:
            df (pd.DataFrame): 待归一化的数据
            fit (bool, optional): 是否拟合新的归一化器，默认为True
            
        Returns:
            pd.DataFrame: 归一化后的数据
        """
        if fit:
            # 初始化MinMaxScaler并拟合数据
            self.scaler = MinMaxScaler()
            scaled = self.scaler.fit_transform(df)
            # 保存归一化器，以便后续使用
            joblib.dump(self.scaler, self.scaler_path)
        else:
            # 加载已保存的归一化器
            self.scaler = joblib.load(self.scaler_path)
            # 使用加载的归一化器转换数据
            scaled = self.scaler.transform(df)
        # 将结果转换回DataFrame格式
        return pd.DataFrame(scaled, columns=df.columns, index=df.index)

    def inverse_transform(self, data, columns):
        """反归一化
        
        将归一化的数据转换回原始尺度
        
        Args:
            data: 归一化的数据，可以是标量、1维数组或2维数组
            columns (list): 需要反归一化的列名列表
            
        Returns:
            np.ndarray: 反归一化后的数据
        """
        # 如果归一化器未加载，则从文件加载
        if self.scaler is None:
            self.scaler = joblib.load(self.scaler_path)

        # 统一转成二维数组，兼容 python 标量 / numpy 标量 / 1D / 2D
        if isinstance(data, Number) or np.isscalar(data):
            # 处理标量情况
            data_2d = np.array([[float(data)]], dtype=float)
        else:
            # 处理数组情况
            arr = np.array(data, dtype=float)
            if arr.ndim == 1:
                # 1维数组转换为2维
                data_2d = arr.reshape(1, -1)
            elif arr.ndim == 2:
                # 保持2维数组不变
                data_2d = arr
            else:
                # 不支持高于2维的数据
                raise ValueError(f"inverse_transform 仅支持标量、1维或2维数据，当前维度: {arr.ndim}")
        
        # 创建一个与原始scaler相同维度的dummy数组
        n_features = len(self.scaler.feature_names_in_)
        dummy = np.zeros((data_2d.shape[0], n_features))
        
        # 找到目标列在原始数据中的索引位置
        feature_names = list(self.scaler.feature_names_in_)
        target_indices = [feature_names.index(col) for col in columns if col in feature_names]
        
        # 填充目标数据到对应位置
        for i, idx in enumerate(target_indices):
            if i < data_2d.shape[1]:
                dummy[:, idx] = data_2d[:, i]
        
        # 反归一化
        result = self.scaler.inverse_transform(dummy)
        
        # 提取目标列的结果
        if len(target_indices) == 1:
            # 如果只反归一化一列，返回1维数组
            return result[:, target_indices[0]]
        else:
            # 如果反归一化多列，返回2维数组
            return result[:, target_indices]

    def create_sequences(self, data, input_len=24, output_len=1):
        """滑动窗口构造监督学习样本
        
        将时间序列数据转换为监督学习所需的输入输出对
        
        Args:
            data: 输入数据，可以是DataFrame或numpy数组
            input_len (int, optional): 输入序列长度，默认为24（例如24小时）
            output_len (int, optional): 输出序列长度，默认为1（例如预测1小时）
            
        Returns:
            tuple: (X, y)，其中X是输入序列，y是输出序列
        """
        X, y = [], []
        # 计算可生成的样本数
        for i in range(len(data) - input_len - output_len + 1):
            # 提取输入序列
            X.append(data[i:i+input_len])
            # 提取输出序列
            y.append(data[i+input_len:i+input_len+output_len])
        # 转换为numpy数组并返回
        return np.array(X), np.array(y)

    def load_scaler(self):
        """加载归一化器
        
        从指定路径加载保存的归一化器
        
        Returns:
            MinMaxScaler: 加载的归一化器对象
        """
        if os.path.exists(self.scaler_path):
            self.scaler = joblib.load(self.scaler_path)
        return self.scaler
        
    def add_time_features(self, df):
        """添加时间特征
        
        Args:
            df (pd.DataFrame): 包含timestamp列的数据
            
        Returns:
            pd.DataFrame: 添加时间特征后的数据
        """
        # 确保timestamp列是datetime类型
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 基本时间特征
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_month'] = df['timestamp'].dt.day
        df['month'] = df['timestamp'].dt.month
        df['quarter'] = df['timestamp'].dt.quarter
        
        # 周期性特征（使用正弦和余弦变换）
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # 工作日/周末特征
        df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
        
        return df
    
    def add_derived_features(self, df, window=24):
        """添加衍生特征
        
        Args:
            df (pd.DataFrame): 输入数据
            window (int, optional): 滚动窗口大小，默认为24
            
        Returns:
            pd.DataFrame: 添加衍生特征后的数据
        """
        # 负荷变化率
        df['load_change'] = df['load'].diff()
        df['load_change_rate'] = df['load'].pct_change()
        
        # 滚动统计特征
        df['load_rolling_mean'] = df['load'].rolling(window=window).mean()
        df['load_rolling_std'] = df['load'].rolling(window=window).std()
        df['load_rolling_max'] = df['load'].rolling(window=window).max()
        df['load_rolling_min'] = df['load'].rolling(window=window).min()
        
        # 滞后特征
        for i in [1, 2, 3, 6, 12, 24]:
            df[f'load_lag_{i}'] = df['load'].shift(i)
            df[f'wind_power_lag_{i}'] = df['wind_power'].shift(i)
            df[f'pv_power_lag_{i}'] = df['pv_power'].shift(i)
        
        # 温度相关特征
        if 'temperature' in df.columns:
            df['temperature_change'] = df['temperature'].diff()
            df['temperature_rolling_mean'] = df['temperature'].rolling(window=window).mean()
        
        # 填充缺失值
        df = self.handle_missing(df)
        
        return df
    
    def add_external_features(self, df):
        """添加外部特征
        
        Args:
            df (pd.DataFrame): 输入数据
            
        Returns:
            pd.DataFrame: 添加外部特征后的数据
        """
        # 天气舒适度指数（简化版）
        if 'temperature' in df.columns and 'wind_speed' in df.columns:
            # 简化的舒适度指数计算
            df['comfort_index'] = df['temperature'] - 0.5 * (df['wind_speed'] - 10)
        
        # 日照时间特征
        if 'irradiance' in df.columns:
            # 计算日照时间（辐照度大于阈值的时间）
            df['is_daylight'] = df['irradiance'].apply(lambda x: 1 if x > 10 else 0)
        
        return df
    
    def engineer_features(self, df):
        """综合特征工程
        
        Args:
            df (pd.DataFrame): 输入数据
            
        Returns:
            pd.DataFrame: 完成特征工程后的数据
        """
        # 添加时间特征
        df = self.add_time_features(df)
        
        # 添加外部特征
        df = self.add_external_features(df)
        
        # 添加衍生特征
        df = self.add_derived_features(df)
        
        # 移除原始timestamp列（如果不需要）
        if 'timestamp' in df.columns:
            df = df.drop('timestamp', axis=1)
        
        return df
