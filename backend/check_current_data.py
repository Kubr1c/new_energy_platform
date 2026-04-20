#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.database import db, NewEnergyData

def check_current_data():
    """检查当前时间的数据"""
    print("Checking current data...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 获取当前时间
            now = datetime.now()
            print(f"Current time: {now}")
            print(f"Current hour: {now.hour}")
            
            # 获取当前小时的数据
            current_hour_start = now.replace(minute=0, second=0, microsecond=0)
            current_hour_end = current_hour_start + timedelta(hours=1)
            
            data = NewEnergyData.query.filter(
                NewEnergyData.timestamp >= current_hour_start,
                NewEnergyData.timestamp < current_hour_end
            ).first()
            
            if data:
                print(f"Current hour data: Wind={data.wind_power:.2f}, PV={data.pv_power:.2f}, Load={data.load:.2f}")
            else:
                print("No data for current hour")
            
            # 获取最新24条数据
            latest_data = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).limit(24).all()
            print("\nLatest 24 records:")
            for d in latest_data[:10]:
                print(f"{d.timestamp}: Wind={d.wind_power:.2f}, PV={d.pv_power:.2f}, Load={d.load:.2f}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_current_data()
