#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models.database import db, NewEnergyData, DispatchResult
from datetime import datetime, date
import json

try:
    app = create_app()
    with app.app_context():
        print("=== Before import ===", flush=True)
        dispatch_count = DispatchResult.query.count()
        new_energy_count = NewEnergyData.query.count()
        print(f"DispatchResult: {dispatch_count}", flush=True)
        print(f"NewEnergyData: {new_energy_count}", flush=True)

    sql_file = os.path.join(os.path.dirname(__file__), '..', 'energy_db.sql')
    sql_file = os.path.abspath(sql_file)
    print(f"\nSQL file: {sql_file}", flush=True)

    from import_sql_data import parse_sql_file, parse_dispatch_insert, parse_new_energy_insert
    dispatch_records_sql, new_energy_records_sql = parse_sql_file(sql_file)
    print(f"Parsed: dispatch={len(dispatch_records_sql)}, new_energy={len(new_energy_records_sql)}", flush=True)

    print("\n=== Testing dispatch parse ===", flush=True)
    if dispatch_records_sql:
        test_result = parse_dispatch_insert(dispatch_records_sql[0])
        print(f"First dispatch record: {test_result}", flush=True)

    print("\n=== Importing dispatch records ===", flush=True)
    with app.app_context():
        dispatch_imported = 0
        dispatch_errors = []
        for i, sql in enumerate(dispatch_records_sql):
            try:
                record = parse_dispatch_insert(sql)
                if record:
                    existing = DispatchResult.query.filter_by(id=record['id']).first()
                    if existing:
                        print(f"  Record {record['id']} exists, skipping", flush=True)
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
                        dispatch_imported += 1
                        if dispatch_imported % 10 == 0:
                            print(f"  Added {dispatch_imported} records...", flush=True)
                            db.session.commit()
            except Exception as e:
                dispatch_errors.append((i, str(e)))
                print(f"  Error at index {i}: {e}", flush=True)

        db.session.commit()
        print(f"Dispatch imported: {dispatch_imported}, errors: {len(dispatch_errors)}", flush=True)

    print("\n=== Importing new_energy records ===", flush=True)
    with app.app_context():
        new_energy_imported = 0
        new_energy_errors = []
        for i, sql in enumerate(new_energy_records_sql):
            try:
                record = parse_new_energy_insert(sql)
                if record:
                    timestamp = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
                    existing = NewEnergyData.query.filter_by(timestamp=timestamp).first()
                    if existing:
                        pass  # Skip existing
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
                        new_energy_imported += 1
                        if new_energy_imported % 1000 == 0:
                            print(f"  Added {new_energy_imported} records...", flush=True)
                            db.session.commit()
            except Exception as e:
                new_energy_errors.append((i, str(e)))

        db.session.commit()
        print(f"NewEnergy imported: {new_energy_imported}, errors: {len(new_energy_errors)}", flush=True)
        if new_energy_errors:
            print(f"First 5 errors: {new_energy_errors[:5]}", flush=True)

    with app.app_context():
        print("\n=== After import ===", flush=True)
        dispatch_count = DispatchResult.query.count()
        new_energy_count = NewEnergyData.query.count()
        print(f"DispatchResult: {dispatch_count}", flush=True)
        print(f"NewEnergyData: {new_energy_count}", flush=True)

except Exception as e:
    import traceback
    print(f"Error: {e}", flush=True)
    traceback.print_exc()