import sys
import os
import traceback

# 添加backend目录到Python路径
sys.path.append('backend')

# 设置环境变量解决OpenMP冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

try:
    from app import create_app
    from models.train import load_split_from_database, train_model_on_db
    print('Modules imported successfully')
    
    app = create_app()
    print('App created successfully')
    
    with app.app_context():
        print('Loading data from database...')
        df_train, df_val, df_test = load_split_from_database(app)
        print('Data loaded successfully')
        print(f'Train shape: {df_train.shape}')
        print(f'Val shape: {df_val.shape}')
        print(f'Test shape: {df_test.shape}')
        
        print('Starting training...')
        model, history, metrics = train_model_on_db(
            df_train, df_val, df_test,
            model_type='attention_lstm',
            fit_scaler=True,
            epochs=5,
            batch_size=32,
            lr=0.001
        )
        print('Training completed successfully')
        print(f'History: {history}')
        print(f'Metrics: {metrics}')
        
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()
