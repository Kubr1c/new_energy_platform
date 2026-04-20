#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查数据库中的用户数据
"""

from app import create_app
from models.database import db, User

app = create_app()

with app.app_context():
    print('=== 检查数据库用户 ===')
    user_count = User.query.count()
    print(f'用户总数: {user_count}')
    
    users = User.query.all()
    for user in users:
        print(f'用户名: {user.username}, 角色: {user.role}, 密码哈希: {user.password_hash}')
    
    if user_count == 0:
        print('\n=== 数据库中没有用户，创建默认用户 ===')
        # 创建默认管理员用户
        admin_user = User(username='admin', role='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        
        # 创建默认操作员用户
        operator_user = User(username='operator', role='operator')
        operator_user.set_password('operator123')
        db.session.add(operator_user)
        
        # 创建默认查看者用户
        viewer_user = User(username='viewer', role='viewer')
        viewer_user.set_password('viewer123')
        db.session.add(viewer_user)
        
        try:
            db.session.commit()
            print('默认用户创建成功!')
            print('管理员: admin/admin123')
            print('操作员: operator/operator123')
            print('查看者: viewer/viewer123')
        except Exception as e:
            db.session.rollback()
            print(f'创建用户失败: {e}')
