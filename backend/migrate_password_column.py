#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库迁移脚本
将 password_hash 列重命名为 password（移除密码加密）
"""

from app import create_app
from models.database import db
import sys

def migrate_password_column():
    """迁移密码列"""
    app = create_app()
    
    with app.app_context():
        print("正在迁移密码列...")
        
        try:
            # 检查列是否存在
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('sys_user')]
            
            if 'password_hash' in columns:
                # 重命名列
                with db.engine.connect() as conn:
                    # MySQL 语法
                    if db.engine.dialect.name == 'mysql':
                        conn.execute(db.text("ALTER TABLE sys_user CHANGE password_hash password VARCHAR(128) NOT NULL"))
                        print("OK: Password column renamed (password_hash -> password)")
                    # SQLite 语法
                    elif db.engine.dialect.name == 'sqlite':
                        conn.execute(db.text("ALTER TABLE sys_user RENAME COLUMN password_hash TO password"))
                        print("OK: Password column renamed (password_hash -> password)")
                    else:
                        print(f"ERROR: Unsupported database type: {db.engine.dialect.name}")
                        return False
                    
                    conn.commit()
                
                # 重置所有用户密码为默认值（因为旧的哈希密码无法解密）
                print("\n注意：由于移除了密码加密，所有用户的密码需要重置。")
                print("建议运行 init_db.py 重新初始化数据库，或手动更新用户密码。")
                
                return True
            elif 'password' in columns:
                print("OK: Password column already exists, no migration needed")
                return True
            else:
                print("ERROR: Password column not found")
                return False
                
        except Exception as e:
            print(f"ERROR: Migration failed: {e}")
            return False

if __name__ == '__main__':
    success = migrate_password_column()
    sys.exit(0 if success else 1)
