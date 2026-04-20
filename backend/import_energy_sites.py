#!/usr/bin/env python3
"""
储能站点数据导入脚本
用于将CSV文件中的储能站点数据导入到数据库
"""

import os
import sys
import csv
import argparse
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.models.database import db, EnergyStorageSite
from backend.app import create_app

def validate_coordinate(lng, lat):
    """验证坐标是否在中国境内"""
    # 中国大致经纬度范围
    if not (73 <= lng <= 135 and 3 <= lat <= 54):
        raise ValueError(f"坐标超出中国范围: ({lng}, {lat})")
    return True

def validate_capacity(capacity):
    """验证容量范围"""
    if not (0.1 <= capacity <= 1000):
        raise ValueError(f"容量超出合理范围: {capacity} MWh")
    return True

def validate_power(power):
    """验证功率范围"""
    if not (0.1 <= power <= 500):
        raise ValueError(f"功率超出合理范围: {power} MW")
    return True

def validate_soh(soh):
    """验证健康度范围"""
    if not (0.1 <= soh <= 1):
        raise ValueError(f"健康度超出范围: {soh}")
    return True

def parse_csv_file(filepath, dry_run=False, update_existing=False):
    """
    解析CSV文件并导入数据
    
    Args:
        filepath: CSV文件路径
        dry_run: 是否仅验证不导入
        update_existing: 是否更新已存在的记录（基于名称和坐标）
    
    Returns:
        tuple: (成功数量, 失败数量, 错误列表)
    """
    successes = 0
    failures = 0
    errors = []
    
    if not os.path.exists(filepath):
        print(f"错误: 文件不存在: {filepath}")
        return 0, 1, [f"文件不存在: {filepath}"]
    
    print(f"正在解析CSV文件: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        print(f"找到 {len(rows)} 条记录")
        
        # 创建Flask应用上下文
        app = create_app()
        
        with app.app_context():
            for i, row in enumerate(rows, 1):
                try:
                    # 提取和验证数据
                    name = row['name'].strip()
                    province = row.get('province', '').strip()
                    city = row.get('city', '').strip()
                    
                    # 解析数值字段
                    try:
                        longitude = float(row['longitude'])
                        latitude = float(row['latitude'])
                        capacity = float(row['capacity'])
                        power = float(row['power'])
                        soh = float(row['soh'])
                    except (ValueError, KeyError) as e:
                        raise ValueError(f"数值字段格式错误: {e}")
                    
                    address = row.get('address', '').strip()
                    status = row.get('status', 'active').strip().lower()
                    description = row.get('description', '').strip()
                    
                    # 验证数据
                    validate_coordinate(longitude, latitude)
                    validate_capacity(capacity)
                    validate_power(power)
                    validate_soh(soh)
                    
                    if status not in ['active', 'inactive', 'maintenance', 'planned']:
                        status = 'active'
                    
                    # 检查是否已存在
                    existing = EnergyStorageSite.query.filter_by(
                        name=name,
                        longitude=longitude,
                        latitude=latitude
                    ).first()
                    
                    if existing:
                        if update_existing:
                            # 更新现有记录
                            existing.capacity = capacity
                            existing.power = power
                            existing.soh = soh
                            existing.address = address
                            existing.status = status
                            existing.description = description
                            existing.updated_at = datetime.utcnow()
                            print(f"  更新记录: {name}")
                        else:
                            print(f"  跳过已存在记录: {name}")
                            successes += 1
                            continue
                    else:
                        # 创建新记录
                        site = EnergyStorageSite(
                            name=name,
                            province=province,
                            city=city,
                            longitude=longitude,
                            latitude=latitude,
                            capacity=capacity,
                            power=power,
                            soh=soh,
                            address=address,
                            status=status,
                            description=description,
                            created_by=1  # 默认管理员ID
                        )
                        db.session.add(site)
                        print(f"  添加记录: {name}")
                    
                    if not dry_run:
                        db.session.commit()
                    
                    successes += 1
                    
                except Exception as e:
                    failures += 1
                    error_msg = f"第{i}行处理失败: {str(e)}"
                    errors.append(error_msg)
                    print(f"  {error_msg}")
                    
    except Exception as e:
        error_msg = f"文件处理失败: {str(e)}"
        errors.append(error_msg)
        print(f"  {error_msg}")
        failures += len(rows)
    
    return successes, failures, errors

def main():
    parser = argparse.ArgumentParser(description='导入储能站点数据')
    parser.add_argument('file', help='CSV文件路径')
    parser.add_argument('--dry-run', action='store_true', help='仅验证不导入')
    parser.add_argument('--update', action='store_true', help='更新已存在的记录')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("储能站点数据导入工具")
    print("=" * 60)
    
    if args.dry_run:
        print("模式: 仅验证（不导入）")
    else:
        print("模式: 验证并导入")
    
    if args.update:
        print("操作: 更新已存在记录")
    else:
        print("操作: 跳过已存在记录")
    
    successes, failures, errors = parse_csv_file(
        args.file, 
        dry_run=args.dry_run,
        update_existing=args.update
    )
    
    print("=" * 60)
    print("导入结果:")
    print(f"  成功: {successes}")
    print(f"  失败: {failures}")
    print(f"  总计: {successes + failures}")
    
    if errors:
        print("\n错误详情:")
        for error in errors[:10]:  # 只显示前10个错误
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors) - 10} 个错误")
    
    if failures == 0:
        print("\n状态: 全部成功 ✓")
        return 0
    else:
        print("\n状态: 存在失败 ×")
        return 1

if __name__ == '__main__':
    sys.exit(main())