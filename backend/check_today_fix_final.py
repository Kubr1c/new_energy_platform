#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.database import db, NewEnergyData

def check_today_fix():
    """检查今天的数据，验证修复是否生效"""
    print("Checking today's data...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 获取当前日期
            today = datetime.now().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = today_start + timedelta(days=1)
            print(f"Today: {today}")
            print(f"Today start: {today_start}")
            print(f"Today end: {today_end}")
            
            # 查询今天的数据
            data = NewEnergyData.query.filter(
                NewEnergyData.timestamp >= today_start,
                NewEnergyData.timestamp < today_end
            ).order_by(NewEnergyData.timestamp.asc()).all()
            
            print(f"Today's data count: {len(data)}")
            
            if len(data) == 0:
                print("No data for today")
                return
            
            print("\nToday's records:")
            for d in data:
                print(f"{d.timestamp}: Wind={d.wind_power:.2f}, PV={d.pv_power:.2f}, Load={d.load:.2f}")
            
            # 检查最新的光伏功率
            latest = data[-1]
            print(f"\nLatest data: Wind={latest.wind_power:.2f}, PV={latest.pv_power:.2f}, Load={latest.load:.2f}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_today_fix()
