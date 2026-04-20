from app import create_app
from models.database import db, NewEnergyData
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # 查询最新的100条数据
    rows = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).limit(100).all()
    
    print(f'查询到 {len(rows)} 条数据')
    
    if rows:
        # 按时间升序排序
        rows_sorted = sorted(rows, key=lambda x: x.timestamp)
        
        # 显示时间范围
        earliest = rows_sorted[0].timestamp
        latest = rows_sorted[-1].timestamp
        print(f'数据时间范围: {earliest} 到 {latest}')
        
        # 检查是否有今天的数据
        today = datetime.now().date()
        today_data = [r for r in rows if r.timestamp.date() == today]
        print(f'今天 ({today}) 数据条数: {len(today_data)}')
        
        # 显示最近10条数据
        print('\n最近10条数据:')
        for i, row in enumerate(rows[:10]):
            print(f'{i+1}. {row.timestamp}: 负荷={row.load:.2f}')
    else:
        print('数据库中没有数据')
