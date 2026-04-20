import sys
import os

# 添加backend目录到Python路径
sys.path.append('backend')

# 设置环境变量解决OpenMP冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from app import create_app
from models.train import train_all_models

if __name__ == '__main__':
    print('Creating app...')
    app = create_app()
    print('App created successfully')
    print('Starting training...')
    train_all_models(app, model_types=['attention_lstm'], epochs=10)
    print('Training completed')
