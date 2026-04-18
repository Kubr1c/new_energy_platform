#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API 健康检查脚本
"""

import requests
import time
import sys

def test_api():
    """测试 API 端点"""
    base_url = "http://localhost:5000"
    
    print("="*60)
    print("OpenCode 后端 API 健康检查")
    print("="*60)
    print()
    
    # 等待服务启动
    print("正在连接到服务器...")
    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{base_url}/", timeout=2)
            print(f"✓ 服务器已连接 (状态码: {response.status_code})")
            break
        except requests.ConnectionError:
            if attempt < max_retries - 1:
                print(f"  重试 {attempt + 1}/{max_retries}...")
                time.sleep(1)
            else:
                print("✗ 无法连接到服务器，请确保后端已启动")
                return False
    
    print()
    print("测试 API 端点:")
    print("-"*60)
    
    # 测试各个端点
    endpoints = [
        ("GET", "/"),
        ("GET", "/data"),
        ("GET", "/config"),
    ]
    
    for method, endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, timeout=5)
            
            status_code = response.status_code
            status_symbol = "✓" if 200 <= status_code < 500 else "✗"
            print(f"{status_symbol} {method:6} {endpoint:30} -> HTTP {status_code}")
            
        except Exception as e:
            print(f"✗ {method:6} {endpoint:30} -> 错误: {str(e)[:40]}")
    
    print()
    print("-"*60)
    print("✓ 健康检查完成")
    print()
    print("后端服务可以通过以下地址访问:")
    print(f"  - 主页: http://localhost:5000/")
    print(f"  - API 文档: http://localhost:5000/api/docs (如果有)")
    print()
    
    return True

if __name__ == '__main__':
    try:
        success = test_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n检查已中止")
        sys.exit(0)
    except Exception as e:
        print(f"检查过程中出现错误: {e}")
        sys.exit(1)
