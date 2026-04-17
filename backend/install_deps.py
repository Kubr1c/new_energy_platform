#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
依赖安装脚本
自动安装所有必需的Python包
"""

import subprocess
import sys
import os

def install_package(package):
    """安装单个包"""
    try:
        print(f"正在安装 {package}...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", package], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {package} 安装成功")
            return True
        else:
            print(f"✗ {package} 安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ 安装 {package} 时出错: {e}")
        return False

def check_package_import(package_name, import_name=None):
    """检查包是否可以导入"""
    if import_name is None:
        import_name = package_name.lower()
    
    try:
        __import__(import_name)
        print(f"✓ {package_name} 已安装")
        return True
    except ImportError:
        print(f"✗ {package_name} 未安装")
        return False

def main():
    """主函数"""
    print("=== 新能源储能系统 - 依赖安装脚本 ===\n")
    
    # 必需的包列表
    required_packages = [
        ("Flask", "flask"),
        ("flask-cors", "flask_cors"),
        ("flask-sqlalchemy", "flask_sqlalchemy"),
        ("pymysql", "pymysql"),
        ("torch", "torch"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("scikit-learn", "sklearn"),
        ("joblib", "joblib"),
        ("PyJWT", "jwt"),
        ("Werkzeug", "werkzeug")
    ]
    
    print("1. 检查已安装的包...")
    missing_packages = []
    
    for package_name, import_name in required_packages:
        if not check_package_import(package_name, import_name):
            missing_packages.append(package_name)
    
    if not missing_packages:
        print("\n✓ 所有必需的包都已安装！")
        return
    
    print(f"\n2. 安装缺失的包 ({len(missing_packages)} 个)...")
    
    # 升级pip
    print("升级pip...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                   capture_output=True, text=True)
    
    # 安装缺失的包
    failed_packages = []
    for package in missing_packages:
        if not install_package(package):
            failed_packages.append(package)
    
    # 验证安装
    print("\n3. 验证安装...")
    still_missing = []
    
    for package_name, import_name in required_packages:
        if not check_package_import(package_name, import_name):
            still_missing.append(package_name)
    
    if still_missing:
        print(f"\n✗ 以下包安装失败: {', '.join(still_missing)}")
        print("\n可能的解决方案:")
        print("1. 手动安装: pip install <package_name>")
        print("2. 使用管理员权限运行")
        print("3. 检查网络连接")
        print("4. 更新pip: python -m pip install --upgrade pip")
        return False
    else:
        print("\n✓ 所有依赖包安装成功！")
        print("\n现在可以运行:")
        print("python init_db.py  # 初始化数据库")
        print("python app.py      # 启动应用")
        return True

if __name__ == '__main__':
    try:
        success = main()
        if success:
            input("\n按回车键退出...")
    except KeyboardInterrupt:
        print("\n\n安装已取消")
    except Exception as e:
        print(f"\n安装过程中出现错误: {e}")
        input("按回车键退出...")
