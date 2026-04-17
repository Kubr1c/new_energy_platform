import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
import os
import sys

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models.model_registry import get_model
from preprocessing.data_utils import DataPreprocessor
from models.database import db, NewEnergyData

def resolve_data_path(data_path):
    """解析训练数据路径，支持绝对路径和常见相对路径。"""
    if os.path.isabs(data_path) and os.path.exists(data_path):
        return data_path

    # 优先按当前工作目录解析
    cwd_path = os.path.abspath(data_path)
    if os.path.exists(cwd_path):
        return cwd_path

    # 再按 backend 根目录解析
    backend_root = os.path.dirname(os.path.dirname(__file__))
    backend_path = os.path.join(backend_root, data_path)
    if os.path.exists(backend_path):
        return backend_path

    # 常见候选路径
    candidates = [
        os.path.join(backend_root, 'data', 'processed', 'train.csv'),
        os.path.join(backend_root, 'data', 'raw', 'training_data.csv'),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError(
        f"未找到训练数据文件: {data_path}。可用候选路径: {candidates}"
    )

def load_data_from_database(app, limit=None):
    """从数据库获取训练数据"""
    with app.app_context():
        query = NewEnergyData.query.order_by(NewEnergyData.timestamp.asc())
        if limit:
            query = query.limit(limit)
        data_records = query.all()
        
        if not data_records:
            raise ValueError("数据库中没有训练数据")
        
        # 转换为DataFrame
        data = []
        for record in data_records:
            data.append({
                'timestamp': record.timestamp,
                'wind_power': record.wind_power,
                'pv_power': record.pv_power,
                'load': record.load,
                'temperature': record.temperature,
                'irradiance': record.irradiance,
                'wind_speed': record.wind_speed
            })
        
        df = pd.DataFrame(data)
        print(f"从数据库获取了 {len(df)} 条训练数据")
        return df

def train_model(data_path=None, input_len=24, output_len=1, epochs=100, batch_size=32, lr=0.001, app=None, model_type='attention_lstm'):
    # 1. 加载并预处理数据
    if data_path and data_path == 'database':
        # 从数据库获取数据
        if app is None:
            raise ValueError("从数据库获取数据需要提供Flask app实例")
        df = load_data_from_database(app)
    elif data_path:
        # 从CSV文件获取数据
        data_path = resolve_data_path(data_path)
        print(f"使用训练数据: {data_path}")
        df = pd.read_csv(data_path, parse_dates=['timestamp'])
    else:
        raise ValueError("请提供数据路径或指定使用数据库")
    features = ['wind_power', 'pv_power', 'load', 'temperature', 'irradiance', 'wind_speed']
    target = ['wind_power', 'pv_power', 'load']   # 多输出
    
    preprocessor = DataPreprocessor()
    # 缺失/异常处理（目标变量是特征子集，避免重复列）
    model_df = df[features].copy()
    model_df = preprocessor.handle_missing(model_df)
    model_df = preprocessor.fix_outliers(model_df, features)
    # 归一化
    scaled_df = preprocessor.normalize(model_df, fit=True)

    # 构造监督样本：X 用全部特征，y 仅用目标列
    target_indices = [features.index(col) for col in target]
    values = scaled_df.values
    X, y = [], []
    for i in range(len(values) - input_len - output_len + 1):
        X.append(values[i:i + input_len, :])
        y.append(values[i + input_len:i + input_len + output_len, target_indices])
    X = np.array(X)
    y = np.array(y).reshape(len(X), -1)  # (样本, output_len * n_targets)

    if len(X) == 0:
        raise ValueError(
            f"可训练样本不足：需要至少 {input_len + output_len} 条记录，当前 {len(values)} 条"
        )
    
    # 2. 划分训练/验证集 (7:2:1 在外部已做，这里简单取前80%训练)
    split = int(0.8 * len(X))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    
    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32),
                                  torch.tensor(y_train, dtype=torch.float32))
    val_dataset = TensorDataset(torch.tensor(X_val, dtype=torch.float32),
                                torch.tensor(y_val, dtype=torch.float32))
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    
    # 3. 模型初始化（通过注册表获取对应模型）
    input_size = len(features)
    output_size = len(target) * output_len   # 预测三个变量的未来 output_len 个值
    model = get_model(model_type, input_size, output_size)
    print(f"使用模型: {model_type}, 参数量: {sum(p.numel() for p in model.parameters())}")
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=5, factor=0.5)
    
    # 4. 训练循环
    best_val_loss = float('inf')
    patience_counter = 0
    train_history = {'train_loss': [], 'val_loss': []}  # 记录训练历史
    for epoch in range(epochs):
        model.train()
        train_loss = 0
        for Xb, yb in train_loader:
            optimizer.zero_grad()
            pred = model(Xb)
            loss = criterion(pred, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        avg_train_loss = train_loss / max(len(train_loader), 1)
        
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for Xb, yb in val_loader:
                pred = model(Xb)
                loss = criterion(pred, yb)
                val_loss += loss.item()
        
        avg_val_loss = val_loss / max(len(val_loader), 1)
        scheduler.step(avg_val_loss)
        
        # 记录训练历史
        train_history['train_loss'].append(avg_train_loss)
        train_history['val_loss'].append(avg_val_loss)
        
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            # 确保模型保存目录存在
            model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models_saved')
            os.makedirs(model_dir, exist_ok=True)
            torch.save(model.state_dict(), os.path.join(model_dir, f'{model_type}.pth'))
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= 10:
                print(f"Early stopping at epoch {epoch}")
                break
        
        if epoch % 10 == 0:
            print(f"Epoch {epoch}, Train Loss: {avg_train_loss:.6f}, Val Loss: {avg_val_loss:.6f}")
    
    return model, preprocessor, train_history

if __name__ == '__main__':
    # 使用数据库训练
    from app import create_app
    app = create_app()
    
    # 默认训练 attention_lstm
    train_model('database', app=app, model_type='attention_lstm')
    
    # 训练其他模型示例：
    # train_model('database', app=app, model_type='standard_lstm')
    # train_model('database', app=app, model_type='gru')
    # train_model('database', app=app, model_type='cnn_lstm')
    # train_model('database', app=app, model_type='transformer')
