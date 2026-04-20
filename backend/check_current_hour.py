#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.database import db, NewEnergyData

def check_current_hour():
    """检查当前小时的数据，验证修复是否生效"""
    print("Checking current hour data...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 获取当前时间
            now = datetime.now()
            current_hour = now.replace(minute=0, second=0, microsecond=0)
            print(f"Current time: {now}")
            print(f"Current hour: {current_hour}")
            
            # 查询当前小时的数据
            current_data = NewEnergyData.query.filter(
                NewEnergyData.timestamp >= current_hour,
                NewEnergyData.timestamp < current_hour + timedelta(hours=1)
            ).first()
            
            if current_data:
                print(f"Current hour data: Wind={current_data.wind_power:.2f}, PV={current_data.pv_power:.2f}, Load={current_data.load:.2f}")
            else:
                print("No data for current hour")
                # 查询前一个小时的数据
                prev_hour = current_hour - timedelta(hours=1)
                prev_data = NewEnergyData.query.filter(
                    NewEnergyData.timestamp >= prev_hour,
                    NewEnergyData.timestamp < current_hour
                ).first()
                if prev_data:
                    print(f"Previous hour data: Wind={prev_data.wind_power:.2f}, PV={prev_data.pv_power:.2f}, Load={prev_data.load:.2f}")
                else:
                    print("No data for previous hour")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_current_hour()
