#!/usr/bin/env python3

import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.database import db, NewEnergyData

def check_today_data():
    """检查今天的数据"""
    print("Checking today's data...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 获取今天的日期
            today = datetime.now().strftime('%Y-%m-%d')
            print(f"Today: {today}")
            
            # 查询今天的数据
            data = NewEnergyData.query.filter(
                NewEnergyData.timestamp >= today
            ).order_by(NewEnergyData.timestamp.asc()).all()
            
            print(f"Today's data count: {len(data)}")
            
            if len(data) == 0:
                print("No data for today")
                return
            
            print("\nToday's records:")
            for d in data:
                print(f"{d.timestamp}: Wind={d.wind_power:.2f}, PV={d.pv_power:.2f}, Load={d.load:.2f}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_today_data()
