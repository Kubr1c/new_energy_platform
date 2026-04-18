#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库初始化脚本
创建数据库表和默认用户
"""

from app import create_app
from models.database import db, User, StrategyConfig
import sys
import io

# 强制设置标准输出为 UTF-8 编码，解决 Windows 环境下的乱码问题
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        print("正在创建数据库表...")
        
        # 创建所有表
        db.create_all()
        print("✓ 数据库表创建成功")
        
        # 创建默认管理员用户（密码使用哈希存储）
        admin_exists = User.query.filter_by(username='admin').first()
        if not admin_exists:
            admin_user = User(username='admin', role='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            print("✓ 默认管理员用户创建成功 (admin/admin123)")
        
        # 创建默认操作员用户
        operator_exists = User.query.filter_by(username='operator').first()
        if not operator_exists:
            operator_user = User(username='operator', role='operator')
            operator_user.set_password('operator123')
            db.session.add(operator_user)
            print("✓ 默认操作员用户创建成功 (operator/operator123)")
        
        # 创建默认查看者用户
        viewer_exists = User.query.filter_by(username='viewer').first()
        if not viewer_exists:
            viewer_user = User(username='viewer', role='viewer')
            viewer_user.set_password('viewer123')
            db.session.add(viewer_user)
            print("✓ 默认查看者用户创建成功 (viewer/viewer123)")
        
        # 初始化默认5阶分时电价与需求响应策略 (山东鸭子曲线)
        strategy_exists = StrategyConfig.query.first()
        if not strategy_exists:
            # 24小时映射表
            tou_mapping = {}
            for h in range(24):
                if 11 <= h < 14:
                    tou_mapping[str(h)] = 'deep_valley'
                elif (10 <= h < 11) or (14 <= h < 15):
                    tou_mapping[str(h)] = 'valley'
                elif 17 <= h < 20:
                    tou_mapping[str(h)] = 'extreme_peak'
                elif 20 <= h < 22:
                    tou_mapping[str(h)] = 'peak'
                else:
                    tou_mapping[str(h)] = 'flat'
                    
            default_strategy = StrategyConfig(
                name='山东春秋典型鸭子曲线',
                extreme_peak_price=1200.0,
                peak_price=1020.0,
                flat_price=600.0,
                valley_price=180.0,
                deep_valley_price=60.0,
                dr_ratio=0.2,
                tou_config=tou_mapping
            )
            db.session.add(default_strategy)
            print("✓ 默认分时电价及DR策略创建成功")

        try:
            db.session.commit()
            print("✓ 数据库初始化完成")
        except Exception as e:
            db.session.rollback()
            print(f"✗ 数据库初始化失败: {e}")
            sys.exit(1)

def reset_database():
    """重置数据库（删除所有数据）"""
    app = create_app()
    
    with app.app_context():
        print("警告: 即将删除所有数据库数据!")
        confirm = input("确认继续? (yes/no): ")
        
        if confirm.lower() == 'yes':
            db.drop_all()
            print("✓ 所有数据库表已删除")
            init_database()
        else:
            print("操作已取消")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'reset':
        reset_database()
    else:
        init_database()
