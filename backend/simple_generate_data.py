#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta
import random
import numpy as np

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.database import db, NewEnergyData

def generate_data():
    """生成新能源数据"""
    print("Generating new energy data...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 检查现有数据
            count = NewEnergyData.query.count()
            print(f"Current data count: {count}")
            
            if count >= 24:
                print("Data is sufficient")
                return
            
            # 生成24条数据
            base_date = datetime.now() - timedelta(days=1)
            
            for hour in range(24):
                timestamp = base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                # 生成模拟数据
                wind_power = max(0, 20 + 10 * np.sin(2 * np.pi * (hour - 6) / 24) + random.gauss(0, 5))
                
                pv_power = 0
                if 6 <= hour <= 18:
                    pv_power = max(0, 15 * np.sin(np.pi * (hour - 6) / 12) + random.gauss(0, 3))
                
                load = 25 + 8 * np.sin(2 * np.pi * (hour - 3) / 24) + random.gauss(0, 2)
                
                # 创建记录
                record = NewEnergyData(
                    timestamp=timestamp,
                    wind_power=wind_power,
                    pv_power=pv_power,
                    load=load,
                    temperature=20 + 5 * np.sin(2 * np.pi * hour / 24),
                    irradiance=pv_power if pv_power > 0 else 0,
                    wind_speed=5 + 2 * np.sin(2 * np.pi * hour / 24)
                )
                
                db.session.add(record)
            
            db.session.commit()
            print(f"Generated 24 new energy records")
            
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    generate_data()
