# 导入必要的库
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from models.database import db  # 导入数据库实例
from routes import data_bp, predict_bp, dispatch_bp, auth_bp, analysis_bp, map_bp  # 导入各功能模块的蓝图
from routes.config import config_bp  # 导入配置模块的蓝图
from config import Config  # 导入应用配置类
import os
import sys
import io

# 强制设置标准输出为 UTF-8 编码，解决 Windows 环境下的乱码问题
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def create_app():
    """创建并配置 Flask 应用实例
    
    Returns:
        Flask: 配置完成的 Flask 应用实例
    """
    # 创建 Flask 应用实例，设置静态文件目录为前端构建产物
    app = Flask(__name__, 
                 static_folder='../frontend/dist',  # 静态文件目录
                 static_url_path='/')  # 静态文件 URL 路径
    
    # 从配置类加载配置
    app.config.from_object(Config)
    
    # 配置 CORS（跨域资源共享）
    CORS(app, 
         supports_credentials=True,  # 支持携带凭证
         allow_headers=['Content-Type', 'Authorization'],  # 允许的请求头
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])  # 允许的 HTTP 方法
    
    # 初始化数据库
    db.init_app(app)
    
    # 注册各功能模块的蓝图
    app.register_blueprint(data_bp)  # 数据模块
    app.register_blueprint(predict_bp)  # 预测模块
    app.register_blueprint(dispatch_bp)  # 调度模块
    app.register_blueprint(auth_bp)  # 认证模块
    app.register_blueprint(analysis_bp)  # 分析模块
    app.register_blueprint(config_bp)  # 配置模块
    app.register_blueprint(map_bp)  # 地图模块
    
    # 静态文件服务路由
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        """提供静态文件服务
        
        Args:
            path: 请求的文件路径
            
        Returns:
            文件内容或 index.html
        """
        if path != "" and os.path.exists(app.static_folder + '/' + path):
            # 如果请求的文件存在，返回该文件
            return send_from_directory(app.static_folder, path)
        else:
            # 否则返回 index.html，支持单页应用路由
            return send_from_directory(app.static_folder, 'index.html')
    
    # 404 错误处理
    @app.errorhandler(404)
    def not_found(error):
        """处理 404 错误
        
        Args:
            error: 错误对象
            
        Returns:
            JSON 格式的错误信息
        """
        return jsonify({'code': 404, 'message': '资源不存在'}), 404
    
    # 500 错误处理
    @app.errorhandler(500)
    def internal_error(error):
        """处理 500 错误
        
        Args:
            error: 错误对象
            
        Returns:
            JSON 格式的错误信息
        """
        return jsonify({'code': 500, 'message': '服务器内部错误'}), 500
    
    # 400 错误处理
    @app.errorhandler(400)
    def bad_request(error):
        """处理 400 错误
        
        Args:
            error: 错误对象
            
        Returns:
            JSON 格式的错误信息
        """
        return jsonify({'code': 400, 'message': '请求参数错误'}), 400
    
    return app


# 创建应用实例
app = create_app()


if __name__ == '__main__':
    """应用入口函数
    
    在应用启动时执行以下操作：
    1. 创建数据库表
    2. 启动 Flask 应用
    """
    with app.app_context():
        # 创建数据库表
        db.create_all()
        print("数据库表创建完成")
    
    # 启动应用
    app.run(
        debug=True,  # 开启调试模式
        host='0.0.0.0',  # 监听所有网络接口
        port=5000  # 服务端口
    )
