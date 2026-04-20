#!/usr/bin/env python3

import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.database import db, NewEnergyData

def check_data():
    """检查数据库中的数据"""
    print("Checking database data...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 检查数据总量
            total_count = NewEnergyData.query.count()
            print(f"Total data count: {total_count}")
            
            if total_count == 0:
                print("No data in database")
                return
            
            # 获取最新24条数据
            data = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).limit(24).all()
            print("\nLatest 24 records:")
            for d in data:
                print(f"{d.timestamp}: Wind={d.wind_power:.2f}, PV={d.pv_power:.2f}, Load={d.load:.2f}")
            
            # 检查光伏功率为0的情况
            zero_pv_count = NewEnergyData.query.filter_by(pv_power=0).count()
            print(f"\nRecords with PV=0: {zero_pv_count}")
            
            # 检查系统状态相关的告警
            print("\nChecking system status...")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_data()
