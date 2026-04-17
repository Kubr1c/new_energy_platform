#!/usr/bin/env python3

import sqlite3
import os
from datetime import datetime, timedelta
import random
import numpy as np

def insert_data():
    """直接插入新能源数据到SQLite数据库"""
    print("Inserting new energy data...")
    
    # 数据库路径
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查现有数据
        cursor.execute("SELECT COUNT(*) FROM new_energy_data")
        count = cursor.fetchone()[0]
        print(f"Current data count: {count}")
        
        if count >= 24:
            print("Data is sufficient")
            conn.close()
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
            
            # 插入记录
            cursor.execute("""
                INSERT INTO new_energy_data 
                (timestamp, wind_power, pv_power, load, temperature, irradiance, wind_speed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp.isoformat(),
                wind_power,
                pv_power,
                load,
                20 + 5 * np.sin(2 * np.pi * hour / 24),
                pv_power if pv_power > 0 else 0,
                5 + 2 * np.sin(2 * np.pi * hour / 24)
            ))
        
        conn.commit()
        conn.close()
        print(f"Successfully inserted 24 new energy records")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    insert_data()
