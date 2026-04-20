#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库初始化脚本

功能：
1. 创建数据库表结构
2. 创建默认用户（管理员、操作员、查看者）
3. 初始化默认分时电价与需求响应策略
4. 提供数据库重置功能
"""

from app import create_app  # 导入应用创建函数
from models.database import db, User, StrategyConfig  # 导入数据库实例和模型
import sys
import io

# 强制设置标准输出为 UTF-8 编码，解决 Windows 环境下的乱码问题
if sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except ValueError:
        # 忽略 I/O 操作错误，使用默认编码
        pass


def init_database():
    """初始化数据库
    
    执行以下操作：
    1. 创建数据库表结构
    2. 创建默认用户
    3. 初始化默认策略配置
    """
    # 创建应用实例
    app = create_app()
    
    # 在应用上下文中执行数据库操作
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
            # 24小时映射表 - 定义每个小时对应的电价时段
            tou_mapping = {}
            for h in range(24):
                if 11 <= h < 14:
                    tou_mapping[str(h)] = 'deep_valley'  # 深谷时段
                elif (10 <= h < 11) or (14 <= h < 15):
                    tou_mapping[str(h)] = 'valley'  # 谷时段
                elif 17 <= h < 20:
                    tou_mapping[str(h)] = 'extreme_peak'  # 尖峰时段
                elif 20 <= h < 22:
                    tou_mapping[str(h)] = 'peak'  # 峰时段
                else:
                    tou_mapping[str(h)] = 'flat'  # 平时段
                    
            # 创建默认策略配置
            default_strategy = StrategyConfig(
                name='山东春秋典型鸭子曲线',  # 策略名称
                extreme_peak_price=1200.0,  # 尖峰电价 (元/MWh)
                peak_price=1020.0,  # 峰电价 (元/MWh)
                flat_price=600.0,  # 平电价 (元/MWh)
                valley_price=180.0,  # 谷电价 (元/MWh)
                deep_valley_price=60.0,  # 深谷电价 (元/MWh)
                dr_ratio=0.2,  # 需求响应比例
                tou_config=tou_mapping  # 分时电价配置
            )
            db.session.add(default_strategy)
            print("✓ 默认分时电价及DR策略创建成功")

        try:
            # 提交事务
            db.session.commit()
            print("✓ 数据库初始化完成")
        except Exception as e:
            # 发生错误时回滚事务
            db.session.rollback()
            print(f"✗ 数据库初始化失败: {e}")
            sys.exit(1)


def reset_database():
    """重置数据库（删除所有数据）
    
    执行以下操作：
    1. 提示用户确认
    2. 删除所有数据库表
    3. 重新初始化数据库
    """
    # 创建应用实例
    app = create_app()
    
    # 在应用上下文中执行数据库操作
    with app.app_context():
        print("警告: 即将删除所有数据库数据!")
        confirm = input("确认继续? (yes/no): ")
        
        if confirm.lower() == 'yes':
            # 删除所有表
            db.drop_all()
            print("✓ 所有数据库表已删除")
            # 重新初始化数据库
            init_database()
        else:
            print("操作已取消")


if __name__ == '__main__':
    """脚本入口
    
    用法：
    - 执行 `python init_db.py` 初始化数据库
    - 执行 `python init_db.py reset` 重置数据库
    """
    if len(sys.argv) > 1 and sys.argv[1] == 'reset':
        # 重置数据库
        reset_database()
    else:
        # 初始化数据库
        init_database()

