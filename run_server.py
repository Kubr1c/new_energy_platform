#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化启动脚本 - 直接启动 Flask 应用
"""

import sys
import os

# 添加后端目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 导入应用和数据库
from app import app
from models.database import db

def main():
    """启动应用"""
    print("="*50)
    print("新能源储能系统启动中...")
    print("="*50)
    
    # 在应用上下文中创建表
    with app.app_context():
        print("\n初始化数据库表...")
        try:
            db.create_all()
            print("✓ 数据库表创建/检查完成")
        except Exception as e:
            print(f"✗ 数据库初始化失败: {e}")
            return False
    
    # 启动应用
    print("\n启动Flask应用服务器...")
    print("-"*50)
    print("后端服务地址: http://localhost:5000")
    print("按 Ctrl+C 停止应用")
    print("-"*50)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        print(f"应用启动失败: {e}")
        return False
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n应用已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n启动过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
