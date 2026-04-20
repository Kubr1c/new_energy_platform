#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统启动脚本

功能：
1. 检查Python版本
2. 检查并安装必需的依赖
3. 初始化数据库
4. 启动Flask应用
"""

import sys
import os
import io




def check_dependencies():
    """检查必需的依赖
    
    Returns:
        list: 缺失的依赖包列表
    """
    # 定义必需的依赖模块及其对应的包名
    required_modules = {
        'flask': 'Flask',  # Web框架
        'flask_cors': 'flask-cors',  # 处理跨域请求
        'flask_sqlalchemy': 'flask-sqlalchemy',  # ORM数据库工具
        'pymysql': 'pymysql',  # MySQL数据库驱动
        'jwt': 'PyJWT',  # JSON Web Token库
        'werkzeug': 'Werkzeug'  # Flask的核心工具库
    }
    
    missing = []
    # 检查每个模块是否已安装
    for module, package in required_modules.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    return missing


def install_dependencies(missing):
    """安装缺失的依赖
    
    Args:
        missing: 缺失的依赖包列表
        
    Returns:
        bool: 安装是否成功
    """
    if not missing:
        return True
    
    print(f"检测到缺失的依赖: {', '.join(missing)}")
    print("正在安装...")
    
    # 逐个安装缺失的依赖
    for package in missing:
        print(f"安装 {package}...")
        # 使用系统命令安装依赖
        result = os.system(f'"{sys.executable}" -m pip install "{package}"')
        if result != 0:
            print(f"安装 {package} 失败")
            return False
    
    print("依赖安装完成")
    return True


def main():
    """主函数
    
    执行启动流程：
    1. 检查Python版本
    2. 检查并安装依赖
    3. 初始化数据库
    4. 启动应用
    """
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
    
    # 再次检查依赖是否安装成功
    missing = check_dependencies()
    if missing:
        print(f"仍有依赖缺失: {', '.join(missing)}")
        sys.exit(1)
    
    print("\nAll dependencies checked successfully")
    
    # 跳过数据库初始化，直接启动应用
    print("\n跳过数据库初始化，直接启动应用...")
    
    # 启动应用
    print("\n启动应用...")
    try:
        from app import app
        print("应用启动成功!")
        print("访问地址: http://localhost:5000")
        print("按 Ctrl+C 停止应用")
        # 启动Flask应用
        app.run(
            debug=True,  # 开启调试模式
            host='0.0.0.0',  # 监听所有网络接口
            port=5000  # 服务端口
        )
    except Exception as e:
        print(f"应用启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    """脚本入口
    
    捕获并处理启动过程中的异常
    """
    try:
        main()
    except KeyboardInterrupt:
        # 处理用户中断
        print("\n应用已停止")
    except Exception as e:
        # 处理其他异常
        print(f"\n启动过程中出现错误: {e}")
        input("按回车键退出...")

