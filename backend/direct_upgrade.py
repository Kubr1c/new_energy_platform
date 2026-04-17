#!/usr/bin/env python3
"""
direct database upgrade script using raw SQL
"""

import os
import subprocess

def run_mysql_commands():
    """run MySQL commands directly"""
    
    # SQL commands to add columns
    sql_commands = [
        "USE energy_db;",
        
        # Check and add email column
        "SET @sql = (SELECT IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'energy_db' AND TABLE_NAME = 'sys_user' AND COLUMN_NAME = 'email') > 0, 'SELECT \"email column already exists\"', 'ALTER TABLE sys_user ADD COLUMN email VARCHAR(120) UNIQUE'));",
        "PREPARE stmt FROM @sql;",
        "EXECUTE stmt;",
        "DEALLOCATE PREPARE stmt;",
        
        # Check and add status column
        "SET @sql = (SELECT IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'energy_db' AND TABLE_NAME = 'sys_user' AND COLUMN_NAME = 'status') > 0, 'SELECT \"status column already exists\"', 'ALTER TABLE sys_user ADD COLUMN status VARCHAR(20) DEFAULT \"active\"'));",
        "PREPARE stmt FROM @sql;",
        "EXECUTE stmt;",
        "DEALLOCATE PREPARE stmt;",
        
        # Check and add last_login column
        "SET @sql = (SELECT IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'energy_db' AND TABLE_NAME = 'sys_user' AND COLUMN_NAME = 'last_login') > 0, 'SELECT \"last_login column already exists\"', 'ALTER TABLE sys_user ADD COLUMN last_login DATETIME'));",
        "PREPARE stmt FROM @sql;",
        "EXECUTE stmt;",
        "DEALLOCATE PREPARE stmt;",
        
        # Update existing users
        "UPDATE sys_user SET status = 'active' WHERE status IS NULL;",
        
        "SELECT 'Database upgrade completed successfully' as message;"
    ]
    
    # Write SQL to file
    with open('upgrade.sql', 'w', encoding='utf-8') as f:
        for command in sql_commands:
            f.write(command + '\n')
    
    print("SQL file created. Please run the following command manually:")
    print("mysql -u root -p < upgrade.sql")
    print("")
    print("Or run each command in MySQL client:")
    print("1. USE energy_db;")
    print("2. ALTER TABLE sys_user ADD COLUMN email VARCHAR(120) UNIQUE;")
    print("3. ALTER TABLE sys_user ADD COLUMN status VARCHAR(20) DEFAULT 'active';")
    print("4. ALTER TABLE sys_user ADD COLUMN last_login DATETIME;")
    print("5. UPDATE sys_user SET status = 'active' WHERE status IS NULL;")

if __name__ == '__main__':
    run_mysql_commands()
