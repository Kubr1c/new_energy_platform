#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从SQL文件导入数据到数据库
"""

import re
import sys
from datetime import datetime

from app import create_app
from models.database import db, NewEnergyData, DispatchResult


def parse_sql_file(sql_file_path):
    """解析SQL文件并提取INSERT语句"""
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    dispatch_records = []
    new_energy_records = []

    lines = content.split('\n')
    current_table = None

    for line in lines:
        line = line.strip()

        if '-- Records of' in line:
            if 'dispatch_result' in line:
                current_table = 'dispatch_result'
            elif 'new_energy_data' in line:
                current_table = 'new_energy_data'
            else:
                current_table = None
        elif line.startswith('INSERT INTO'):
            if current_table == 'dispatch_result':
                dispatch_records.append(line)
            elif current_table == 'new_energy_data':
                new_energy_records.append(line)

    return dispatch_records, new_energy_records


def parse_dispatch_insert(sql):
    """解析dispatch_result的INSERT语句"""
    pattern = r"INSERT INTO `dispatch_result` VALUES\s*\((.*)\);?"
    match = re.search(pattern, sql, re.DOTALL)
    if not match:
        return None

    values_str = match.group(1)
    parts = []
    current = ''
    in_json = False
    in_string = False
    paren_depth = 0

    i = 0
    while i < len(values_str):
        char = values_str[i]

        if char == '[' and not in_string:
            in_json = True
            paren_depth += 1
            current += char
        elif char == ']' and not in_string:
            paren_depth -= 1
            if paren_depth == 0:
                in_json = False
            current += char
        elif char == "'" and not in_json:
            in_string = not in_string
            current += char
        elif char == ',' and not in_string and not in_json:
            part = current.strip()
            if part.startswith("'") and part.endswith("'"):
                part = part[1:-1]
            parts.append(part)
            current = ''
        else:
            current += char

        i += 1

    if current.strip():
        part = current.strip()
        if part.startswith("'") and part.endswith("'"):
            part = part[1:-1]
        parts.append(part)

    if len(parts) < 7:
        return None

    record = {
        'id': int(parts[0]) if parts[0] else None,
        'schedule_date': parts[1],
        'charge_plan': parts[2],
        'discharge_plan': parts[3],
        'soc_curve': parts[4],
        'abandon_rate': float(parts[5]) if parts[5] else None,
        'cost': float(parts[6]) if parts[6] else None,
        'created_at': parts[7] if len(parts) > 7 else None
    }

    return record


def parse_new_energy_insert(sql):
    """解析new_energy_data的INSERT语句"""
    pattern = r"INSERT INTO `new_energy_data` VALUES\s*\((.*)\);?"
    match = re.search(pattern, sql, re.DOTALL)
    if not match:
        return None

    values_str = match.group(1)
    parts = [p.strip() for p in values_str.split(',')]

    if len(parts) < 8:
        return None

    record = {
        'id': int(parts[0]) if parts[0] else None,
        'timestamp': parts[1].strip("'"),
        'wind_power': float(parts[2]) if parts[2] else 0,
        'pv_power': float(parts[3]) if parts[3] else 0,
        'load': float(parts[4]) if parts[4] else 0,
        'temperature': float(parts[5]) if parts[5] else 0,
        'irradiance': float(parts[6]) if parts[6] else 0,
        'wind_speed': float(parts[7]) if parts[7] else 0
    }

    return record


def import_data(sql_file_path):
    """导入数据到数据库"""
    app = create_app()

    with app.app_context():
        print(f"正在读取SQL文件: {sql_file_path}", flush=True)
        dispatch_records_sql, new_energy_records_sql = parse_sql_file(sql_file_path)
        print(f"找到 {len(dispatch_records_sql)} 条 dispatch_result 记录", flush=True)
        print(f"找到 {len(new_energy_records_sql)} 条 new_energy_data 记录", flush=True)

        dispatch_count = 0
        for sql in dispatch_records_sql:
            record = parse_dispatch_insert(sql)
            if record:
                try:
                    existing = DispatchResult.query.filter_by(id=record['id']).first()
                    if existing:
                        existing.schedule_date = datetime.strptime(record['schedule_date'], '%Y-%m-%d').date()
                        existing.charge_plan = record['charge_plan']
                        existing.discharge_plan = record['discharge_plan']
                        existing.soc_curve = record['soc_curve']
                        existing.abandon_rate = record['abandon_rate']
                        existing.cost = record['cost']
                        existing.created_at = datetime.strptime(record['created_at'], '%Y-%m-%d %H:%M:%S') if record['created_at'] else None
                    else:
                        new_record = DispatchResult(
                            id=record['id'],
                            schedule_date=datetime.strptime(record['schedule_date'], '%Y-%m-%d').date(),
                            charge_plan=record['charge_plan'],
                            discharge_plan=record['discharge_plan'],
                            soc_curve=record['soc_curve'],
                            abandon_rate=record['abandon_rate'],
                            cost=record['cost'],
                            created_at=datetime.strptime(record['created_at'], '%Y-%m-%d %H:%M:%S') if record['created_at'] else None
                        )
                        db.session.add(new_record)
                    dispatch_count += 1
                except Exception as e:
                    print(f"导入 dispatch 记录 {record.get('id')} 时出错: {e}")

        print(f"正在导入 {dispatch_count} 条 dispatch_result 记录...")

        new_energy_count = 0
        for sql in new_energy_records_sql:
            record = parse_new_energy_insert(sql)
            if record:
                try:
                    timestamp = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
                    existing = NewEnergyData.query.filter_by(timestamp=timestamp).first()
                    if existing:
                        existing.wind_power = record['wind_power']
                        existing.pv_power = record['pv_power']
                        existing.load = record['load']
                        existing.temperature = record['temperature']
                        existing.irradiance = record['irradiance']
                        existing.wind_speed = record['wind_speed']
                    else:
                        new_record = NewEnergyData(
                            timestamp=timestamp,
                            wind_power=record['wind_power'],
                            pv_power=record['pv_power'],
                            load=record['load'],
                            temperature=record['temperature'],
                            irradiance=record['irradiance'],
                            wind_speed=record['wind_speed']
                        )
                        db.session.add(new_record)
                    new_energy_count += 1
                except Exception as e:
                    print(f"导入 new_energy_data 记录 {record.get('id')} 时出错: {e}")

        print(f"正在导入 {new_energy_count} 条 new_energy_data 记录...")

        try:
            db.session.commit()
            print(f"✓ 数据导入成功!")
            print(f"  - dispatch_result: {dispatch_count} 条")
            print(f"  - new_energy_data: {new_energy_count} 条")
        except Exception as e:
            db.session.rollback()
            print(f"✗ 数据导入失败: {e}")
            sys.exit(1)


if __name__ == '__main__':
    import os
    sql_file = os.path.join(os.path.dirname(__file__), '..', 'energy_db.sql')
    sql_file = os.path.abspath(sql_file)

    try:
        import_data(sql_file)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()