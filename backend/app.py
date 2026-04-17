from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from models.database import db
from routes import data_bp, predict_bp, dispatch_bp, auth_bp, analysis_bp
from routes.config import config_bp
from config import Config
import os
import sys
import io

# 强制设置标准输出为 UTF-8 编码，解决 Windows 环境下的乱码问题
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def create_app():
    app = Flask(__name__, 
                 static_folder='../frontend/dist', 
                 static_url_path='/')
    
    # 配置
    app.config.from_object(Config)
    
    # enable CORS with specific configuration
    CORS(app, 
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # 初始化数据库
    db.init_app(app)
    
    # 注册蓝图
    app.register_blueprint(data_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(dispatch_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(analysis_bp)
    
    # 静态文件服务
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(app.static_folder + '/' + path):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'code': 404, 'message': '资源不存在'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'code': 500, 'message': '服务器内部错误'}), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'code': 400, 'message': '请求参数错误'}), 400
    
    return app

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # 创建数据库表
        db.create_all()
        print("数据库表创建完成")
    
    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5000)
