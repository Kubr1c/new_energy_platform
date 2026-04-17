#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统启动脚本
检查依赖并启动应用
"""

import sys
import os

def check_dependencies():
    """检查必需的依赖"""
    required_modules = {
        'flask': 'Flask',
        'flask_cors': 'flask-cors',
        'flask_sqlalchemy': 'flask-sqlalchemy',
        'pymysql': 'pymysql',
        'jwt': 'PyJWT',
        'werkzeug': 'Werkzeug'
    }
    
    missing = []
    for module, package in required_modules.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    return missing

def install_dependencies(missing):
    """安装缺失的依赖"""
    if not missing:
        return True
    
    print(f"检测到缺失的依赖: {', '.join(missing)}")
    print("正在安装...")
    
    for package in missing:
        print(f"安装 {package}...")
        result = os.system(f'"{sys.executable}" -m pip install "{package}"')
        if result != 0:
            print(f"安装 {package} 失败")
            return False
    
    print("依赖安装完成")
    return True

def main():
    """主函数"""
    print("=== 新能源储能系统启动脚本 ===\n")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("错误: 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 检查并安装依赖
    missing = check_dependencies()
    if missing:
        if not install_dependencies(missing):
            print("\n依赖安装失败，请手动运行:")
            print(f"pip install {' '.join(missing)}")
            sys.exit(1)
    
    # 再次检查
    missing = check_dependencies()
    if missing:
        print(f"仍有依赖缺失: {', '.join(missing)}")
        sys.exit(1)
    
    print("\n✓ 所有依赖检查通过")
    
    # 初始化数据库
    print("\n初始化数据库...")
    try:
        from init_db import init_database
        init_database()
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        print("请检查数据库配置")
        sys.exit(1)
    
    # 启动应用
    print("\n启动应用...")
    try:
        from app import app
        print("应用启动成功!")
        print("访问地址: http://localhost:5000")
        print("按 Ctrl+C 停止应用")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"应用启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n应用已停止")
    except Exception as e:
        print(f"\n启动过程中出现错误: {e}")
        input("按回车键退出...")
