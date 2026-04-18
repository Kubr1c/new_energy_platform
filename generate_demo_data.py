#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 2026-04-12 ~ 2026-05-20 的模拟新能源数据。

生成策略：
  - 基于训练集（1月）的每小时统计规律建立基准模型
  - 4-5月为春末夏初，在1月基础上做季节性调整：
      光伏：日照时间延长、强度更高（irradiance 峰值 +30%）
      温度：整体升高（+15-20°C）
      风电：春季偏多，保持相似水平
      负荷：春季略低，高峰有所下降
  - 在基准值上叠加自相关噪声（AR(1)），模拟真实波动
  - 通过数据库写入数据（与项目现有架构集成）
"""

import sys, os, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# =========================================================
# 每小时基准参数（来自训练数据统计分析）
# =========================================================

# 1月每小时的 irradiance 均值（基准，4-5月将缩放）
HOURLY_IRRADIANCE_BASE = np.array([
    0, 0, 0, 0, 0, 0,
    44.2, 137.4, 323.8, 605.8, 868.4, 994.7,
    884.7, 606.2, 326.7, 136.7, 43.7, 11.1,
    0, 0, 0, 0, 0, 0
])

# 1月每小时负荷均值
HOURLY_LOAD_BASE = np.array([
    24.21, 23.73, 23.84, 23.85, 24.15, 23.78,
    24.39, 40.02, 40.70, 34.55, 35.53, 31.48,
    31.65, 31.58, 37.46, 36.93, 36.61, 36.15,
    44.30, 45.72, 44.96, 33.97, 33.79, 23.87
])

# 1月每小时温度均值（夜间~13°C，白天~30°C）
HOURLY_TEMP_BASE = np.array([
    13.13, 13.05, 13.05, 13.03, 13.06, 12.95,
    18.08, 21.19, 24.13, 26.55, 28.39, 29.53,
    29.95, 29.59, 28.51, 26.60, 23.83, 21.03,
    17.98, 12.84, 12.89, 13.01, 13.05, 13.01
])

# 1月每小时风电均值（波动大，全天分布）
WIND_POWER_MEAN = 25.27
WIND_POWER_STD  = 9.12

# 1月风速均值
WIND_SPEED_MEAN = 11.98
WIND_SPEED_STD  = 0.59


# =========================================================
# 季节性调整系数（4月12日 ~ 5月20日：春末夏初）
# =========================================================

def get_seasonal_factors(date: datetime) -> dict:
    """
    根据日期返回季节性调整系数。
    从 4月12日 到 5月20日 线性过渡（春末 → 初夏）。
    """
    # 4月12日 到 5月20日 共 39 天，progress 从 0 到 1
    start = datetime(2026, 4, 12)
    total_days = 38
    days_in = (date - start).days
    progress = min(1.0, max(0.0, days_in / total_days))

    return {
        # 光伏：日照增强，峰值比1月高20%（4月）到30%（5月中）
        # 1月训练集最大辐照约1100 W/m²，4-5月略高但不超过1400
        'irradiance_scale': 1.15 + 0.10 * progress,
        # 光伏日照时长延长：日出提前到5:00，日落延迟到19:00
        'daylight_extend': progress,
        # 温度：春末夏初，4月均值约23°C，5月约27°C
        # 1月日间均值约20°C（训练集），4月比1月高约3-8°C
        'temp_offset': 3.5 + 4.5 * progress,
        # 负荷：春季稍低于冬季，但空调开始启动
        'load_scale': 0.92 + 0.05 * progress,
        # 风电：4月春季风略强，5月趋于平稳
        'wind_scale': 1.05 - 0.05 * progress,
        # 风速
        'wind_speed_scale': 1.02 - 0.02 * progress,
    }


def get_hourly_irradiance(hour: int, date: datetime, factors: dict) -> float:
    """计算某小时的辐照度，考虑季节性延长日照时间。"""
    base = HOURLY_IRRADIANCE_BASE[hour]

    # 季节性延长：progress=0 时日照 6~17 时，progress=1 时 5~19 时
    ext = factors['daylight_extend']
    # 在5点增加辐照（渐进）
    if hour == 5:
        base = base + ext * 20.0
    # 在18点增加辐照
    elif hour == 18:
        base = base + ext * 8.0
    # 在19点增加辐照（5月有余晖）
    elif hour == 19:
        base = base + ext * 3.0

    return base * factors['irradiance_scale']


# =========================================================
# 单日 24 小时数据生成
# =========================================================

def generate_day(date: datetime, prev_wind: float = None, rng: np.random.Generator = None) -> pd.DataFrame:
    """
    生成单日 24 小时数据，带 AR(1) 噪声模拟时间相关性。
    prev_wind: 前一天最后一小时的风电，用于初始化 AR(1)
    """
    if rng is None:
        rng = np.random.default_rng()

    factors = get_seasonal_factors(date)
    rows = []

    # AR(1) 初始化
    wind_ar = prev_wind if prev_wind is not None else WIND_POWER_MEAN
    # 天气类型：晴天、多云、阴天（影响光伏、温度波动）
    weather_type = rng.choice(['sunny', 'cloudy', 'overcast'], p=[0.55, 0.30, 0.15])
    cloud_factor = {'sunny': 1.0, 'cloudy': 0.6, 'overcast': 0.2}[weather_type]

    for hour in range(24):
        ts = date.replace(hour=hour, minute=0, second=0, microsecond=0)

        # ---- 辐照度 ----
        irr_base = get_hourly_irradiance(hour, date, factors)
        irr_noise = rng.normal(0, irr_base * 0.12) if irr_base > 0 else 0
        irradiance = max(0.0, (irr_base + irr_noise) * cloud_factor)

        # ---- 光伏功率 ----
        # 光伏与辐照度正比，加小噪声
        if irradiance < 5:
            pv_power = 0.0
        else:
            # 训练集1月光伏峰值约53 MW（irradiance~1000 W/m²时）
            # 4-5月日照略强，峰值约60 MW，与训练数据量级保持一致
            pv_scale = irradiance / 1000.0
            pv_mean = pv_scale * 55.0
            pv_noise = rng.normal(0, pv_mean * 0.08)
            pv_power = float(np.clip(pv_mean + pv_noise, 0.0, 62.0))

        # ---- 风电（AR(1) 过程）----
        wind_mean_h = WIND_POWER_MEAN * factors['wind_scale']
        ar_coef = 0.75   # AR(1) 系数，控制时序相关性
        innov = rng.normal(0, WIND_POWER_STD * 0.5)
        wind_ar = ar_coef * wind_ar + (1 - ar_coef) * wind_mean_h + innov
        wind_power = float(np.clip(wind_ar, 0.0, 45.6))

        # ---- 温度 ----
        temp_base = HOURLY_TEMP_BASE[hour] + factors['temp_offset']
        temp_noise = rng.normal(0, 1.5)
        temperature = temp_base + temp_noise

        # ---- 负荷 ----
        # 基础负荷 + 季节因子 + 随机波动
        # 春季空调效应：白天（9-17时）高温时段负荷略增
        ac_boost = 0.0
        if 9 <= hour <= 17:
            ac_boost = max(0, (temperature - 25) * 0.4)
        load_base = HOURLY_LOAD_BASE[hour] * factors['load_scale'] + ac_boost
        load_noise = rng.normal(0, load_base * 0.06)
        load = float(np.clip(load_base + load_noise, 10.0, 55.0))

        # ---- 风速 ----
        ws_mean = WIND_SPEED_MEAN * factors['wind_speed_scale']
        ws_noise = rng.normal(0, WIND_SPEED_STD)
        wind_speed = float(np.clip(ws_mean + ws_noise, 0.0, 22.0))

        rows.append({
            'timestamp':   ts.strftime('%Y-%m-%d %H:%M:%S'),
            'wind_power':  round(wind_power, 6),
            'pv_power':    round(pv_power, 6),
            'load':        round(load, 6),
            'temperature': round(float(temperature), 6),
            'irradiance':  round(float(irradiance), 6),
            'wind_speed':  round(wind_speed, 6),
        })

    return pd.DataFrame(rows), wind_ar   # 返回最后的 wind_ar 供下一天初始化


# =========================================================
# 生成完整日期范围
# =========================================================

def generate_date_range(start_date: datetime, end_date: datetime, seed: int = 42) -> pd.DataFrame:
    """
    生成 start_date ~ end_date（含）每小时的数据。
    使用固定随机种子保证结果可复现。
    """
    rng = np.random.default_rng(seed)
    all_dfs = []
    prev_wind = WIND_POWER_MEAN

    current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end     = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    day_count = 0
    while current <= end:
        day_df, prev_wind = generate_day(current, prev_wind=prev_wind, rng=rng)
        all_dfs.append(day_df)
        current += timedelta(days=1)
        day_count += 1
        if day_count % 10 == 0:
            print(f'  已生成 {day_count} 天 ({current.strftime("%Y-%m-%d")})...')

    df = pd.concat(all_dfs, ignore_index=True)
    print(f'  共生成 {len(df)} 条记录（{day_count} 天）')
    return df


# =========================================================
# 数据质量检查
# =========================================================

def validate(df: pd.DataFrame) -> bool:
    """简单校验数据合理性。"""
    ok = True
    checks = {
        'wind_power':  (0, 46),
        'pv_power':    (0, 90),
        'load':        (10, 60),
        'temperature': (10, 42),
        'irradiance':  (0, 1500),
        'wind_speed':  (0, 22),
    }
    for col, (lo, hi) in checks.items():
        out_of_range = ((df[col] < lo) | (df[col] > hi)).sum()
        if out_of_range > 0:
            print(f'  [WARN] {col}: {out_of_range} 条超出范围 [{lo}, {hi}]')
            ok = False

    # 光伏夜间必须为0
    night_pv = df[(df['timestamp'].str[11:13].astype(int).isin([0,1,2,3,4,19,20,21,22,23])) & (df['pv_power'] > 0)]
    if len(night_pv) > 0:
        print(f'  [WARN] 夜间 pv_power > 0: {len(night_pv)} 条')
        ok = False

    if ok:
        print('  [OK] 数据质量校验通过')
    return ok


# =========================================================
# 写入数据库
# =========================================================

def insert_to_db(df: pd.DataFrame, app) -> int:
    """将 DataFrame 插入数据库，跳过已存在的时间戳。"""
    from models.database import db, NewEnergyData
    from sqlalchemy.exc import IntegrityError

    inserted = 0
    skipped  = 0

    with app.app_context():
        # 批量查询已存在的时间戳
        timestamps = [datetime.strptime(r, '%Y-%m-%d %H:%M:%S') for r in df['timestamp']]
        existing_set = set(
            r.timestamp for r in
            NewEnergyData.query.filter(
                NewEnergyData.timestamp.in_(timestamps)
            ).all()
        )

        batch = []
        for _, row in df.iterrows():
            ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
            if ts in existing_set:
                skipped += 1
                continue

            batch.append(NewEnergyData(
                timestamp   = ts,
                wind_power  = float(row['wind_power']),
                pv_power    = float(row['pv_power']),
                load        = float(row['load']),
                temperature = float(row['temperature']),
                irradiance  = float(row['irradiance']),
                wind_speed  = float(row['wind_speed']),
            ))

            # 每500条提交一次，防止内存溢出
            if len(batch) >= 500:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                inserted += len(batch)
                batch = []

        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()
            inserted += len(batch)

    return inserted, skipped


# =========================================================
# 主程序
# =========================================================

if __name__ == '__main__':
    START_DATE = datetime(2026, 4, 12)
    END_DATE   = datetime(2026, 5, 20)
    CSV_OUTPUT = os.path.join(os.path.dirname(__file__),
                              'backend', 'data', 'raw', 'demo_data_apr_may.csv')

    print('=' * 60)
    print('  新能源模拟数据生成器')
    print(f'  时间范围: {START_DATE.date()} ~ {END_DATE.date()}')
    print('=' * 60)

    # 1. 生成数据
    print('\n[1/4] 生成模拟数据...')
    df = generate_date_range(START_DATE, END_DATE, seed=42)

    # 2. 数据质量校验
    print('\n[2/4] 数据质量校验...')
    validate(df)

    # 3. 统计摘要
    print('\n[3/4] 数据统计摘要:')
    print(f'  时间范围: {df["timestamp"].min()} ~ {df["timestamp"].max()}')
    for col in ['wind_power', 'pv_power', 'load', 'temperature', 'irradiance', 'wind_speed']:
        print(f'  {col:12s}: mean={df[col].mean():.2f}  std={df[col].std():.2f}'
              f'  min={df[col].min():.2f}  max={df[col].max():.2f}')

    # 4. 保存 CSV
    df.to_csv(CSV_OUTPUT, index=False)
    print(f'\n[4/4] CSV 已保存: {CSV_OUTPUT}')
    print(f'      共 {len(df)} 条记录')

    # 5. 写入数据库
    print('\n[5/4] 写入数据库...')
    try:
        from app import create_app
        app = create_app()
        inserted, skipped = insert_to_db(df, app)
        print(f'  插入: {inserted} 条  跳过(已存在): {skipped} 条')

        # 验证写入结果
        with app.app_context():
            from models.database import NewEnergyData
            total = NewEnergyData.query.count()
            from sqlalchemy import func
            latest = NewEnergyData.query.order_by(NewEnergyData.timestamp.desc()).first()
            print(f'  数据库当前总记录: {total} 条')
            print(f'  最新记录时间戳:   {latest.timestamp}')

    except Exception as e:
        import traceback
        print(f'  [ERROR] 数据库写入失败: {e}')
        traceback.print_exc()
        print('  数据已保存到 CSV，可手动通过数据管理页面上传')

    print('\n完成！')
    print('=' * 60)
    print('演示建议：')
    print('  1. 访问 仪表盘 -> 实时功率曲线 查看最新数据')
    print('  2. 访问 预测分析 -> 执行预测 对新数据做预测')
    print('  3. 访问 优化调度 -> 执行调度优化')
    print('  4. 访问 对比分析 -> 运行全维对比 查看真实vs预测')
    print('=' * 60)
