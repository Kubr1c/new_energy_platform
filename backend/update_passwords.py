#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
更新数据库中用户的密码
"""

from app import create_app
from models.database import db, User

app = create_app()

with app.app_context():
    print('=== 更新用户密码 ===')
    
    # 更新管理员密码
    admin = User.query.filter_by(username='admin').first()
    if admin:
        admin.set_password('admin123')
        print('管理员密码已更新为: admin123')
    
    # 更新操作员密码
    operator = User.query.filter_by(username='operator').first()
    if operator:
        operator.set_password('operator123')
        print('操作员密码已更新为: operator123')
    
    # 更新查看者密码
    viewer = User.query.filter_by(username='viewer').first()
    if viewer:
        viewer.set_password('viewer123')
        print('查看者密码已更新为: viewer123')
    
    try:
        db.session.commit()
        print('\n密码更新成功!')
        print('现在可以使用以下账号登录:')
        print('管理员: admin/admin123')
        print('操作员: operator/operator123')
        print('查看者: viewer/viewer123')
    except Exception as e:
        db.session.rollback()
        print(f'更新密码失败: {e}')
