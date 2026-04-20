#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重新创建数据库表并初始化默认用户
"""

from app import create_app
from models.database import db, User, StrategyConfig

app = create_app()

with app.app_context():
    print('=== 重新创建数据库表 ===')
    
    # 删除所有表
    db.drop_all()
    print('所有表已删除')
    
    # 创建所有表
    db.create_all()
    print('所有表已创建')
    
    # 创建默认管理员用户
    admin_user = User(username='admin', role='admin')
    admin_user.set_password('admin123')
    db.session.add(admin_user)
    print('默认管理员用户创建成功 (admin/admin123)')
    
    # 创建默认操作员用户
    operator_user = User(username='operator', role='operator')
    operator_user.set_password('operator123')
    db.session.add(operator_user)
    print('默认操作员用户创建成功 (operator/operator123)')
    
    # 创建默认查看者用户
    viewer_user = User(username='viewer', role='viewer')
    viewer_user.set_password('viewer123')
    db.session.add(viewer_user)
    print('默认查看者用户创建成功 (viewer/viewer123)')
    
    # 初始化默认5阶分时电价与需求响应策略
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
    print('默认分时电价及DR策略创建成功')
    
    try:
        db.session.commit()
        print('\n数据库初始化完成!')
        print('现在可以使用以下账号登录:')
        print('管理员: admin/admin123')
        print('操作员: operator/operator123')
        print('查看者: viewer/viewer123')
    except Exception as e:
        db.session.rollback()
        print(f'数据库初始化失败: {e}')
