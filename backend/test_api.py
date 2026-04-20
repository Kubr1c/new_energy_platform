#!/usr/bin/env python3

import os
import sys
import requests

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_api():
    """测试 /api/data/latest 接口"""
    print("Testing /api/data/latest API...")
    
    try:
        # 启动后端服务器
        import subprocess
        import time
        
        # 启动服务器
        server = subprocess.Popen([sys.executable, 'start.py'], cwd=os.path.dirname(os.path.abspath(__file__)))
        time.sleep(2)  # 等待服务器启动
        
        # 测试 API
        response = requests.get('http://localhost:5000/api/data/latest')
        print('API响应状态码:', response.status_code)
        print('API响应内容:', response.json())
        
        # 停止服务器
        server.terminate()
        server.wait()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
