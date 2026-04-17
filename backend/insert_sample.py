import sqlite3
import os
from datetime import datetime, timedelta
import random

def insert_sample_data():
    print("Inserting sample data...")
    
    db_path = r"E:\Accept_orders\4.8\new_energy\backend\instance\app.db"
    
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查现有数据
        cursor.execute("SELECT COUNT(*) FROM new_energy_data")
        count = cursor.fetchone()[0]
        print(f"Current data count: {count}")
        
        if count < 24:
            print("Adding 24 sample records...")
            
            # 生成24条数据
            base_date = datetime.now() - timedelta(days=1)
            
            for hour in range(24):
                timestamp = base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                # 简单的模拟数据
                wind_power = 10 + random.uniform(-5, 15)
                pv_power = 8 + random.uniform(-3, 10) if 6 <= hour <= 18 else 0
                load = 15 + random.uniform(-3, 8)
                
                cursor.execute("""
                    INSERT INTO new_energy_data 
                    (timestamp, wind_power, pv_power, load, temperature, irradiance, wind_speed)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    timestamp.isoformat(),
                    wind_power,
                    pv_power,
                    load,
                    20 + random.uniform(-2, 5),
                    pv_power if pv_power > 0 else 0,
                    5 + random.uniform(-1, 3)
                ))
            
            conn.commit()
            print("Successfully inserted 24 sample records!")
        else:
            print("Data already exists")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    insert_sample_data()
