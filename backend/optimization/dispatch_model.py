"""
调度模型模块

该模块实现了新能源微电网的调度模型，包括：
- 多目标优化目标函数
- 约束条件处理
- SOC曲线计算
- 电池寿命损耗计算

使用场景：
- 新能源微电网调度优化
- 储能系统运行策略制定
- 需求响应管理
"""
import numpy as np

class DispatchModel:
    """
    调度模型类，用于计算目标函数和约束违反值
    """
    def __init__(self, wind_forecast, pv_forecast, load_forecast, price_buy, price_sell,
                 ess_capacity=40.0, ess_power=20.0, eta_c=0.95, eta_d=0.95, 
                 soc_min=0.1, soc_max=0.9, grid_max=30.0, dr_ratio=0.2):
        """
        初始化调度模型
        
        参数：
        - wind_forecast: 风电预测功率，长度为24的列表 (MW)
        - pv_forecast: 光伏预测功率，长度为24的列表 (MW)
        - load_forecast: 负荷预测，长度为24的列表 (MW)
        - price_buy: 购电价格，长度为24的列表 (元/MWh)
        - price_sell: 售电价格，长度为24的列表 (元/MWh)
        - ess_capacity: 储能容量 (MWh)，默认40.0
        - ess_power: 储能功率 (MW)，默认20.0
        - eta_c: 充电效率，默认0.95
        - eta_d: 放电效率，默认0.95
        - soc_min: 最小荷电状态，默认0.1
        - soc_max: 最大荷电状态，默认0.9
        - grid_max: 电网最大功率 (MW)，默认30.0
        - dr_ratio: 需求响应比例，默认0.2
        """
        self.T = 24  # 时间步数（24小时）
        self.wind = np.array(wind_forecast)  # 风电预测
        self.pv = np.array(pv_forecast)  # 光伏预测
        self.load = np.array(load_forecast)  # 负荷预测
        self.dr_ratio = dr_ratio  # 需求响应比例
        self.base_load = self.load * (1 - self.dr_ratio)  # 基础不可转移负荷
        self.total_shift_energy = np.sum(self.load * self.dr_ratio)  # 总可转移负荷
        self.price_buy = np.array(price_buy)  # 购电价格
        self.price_sell = np.array(price_sell)  # 售电价格
        self.E_rated = ess_capacity   # 储能容量 (MWh)
        self.P_rated = ess_power      # 储能功率 (MW)
        self.eta_c = eta_c  # 充电效率
        self.eta_d = eta_d  # 放电效率
        self.soc_min = soc_min  # 最小荷电状态
        self.soc_max = soc_max  # 最大荷电状态
        self.grid_max = grid_max  # 电网最大功率 (MW)
        
        # 寿命曲线：DOD -> 最大循环次数 (拟合)
        self.dod_cycle = {0.1: 10000, 0.2: 8000, 0.4: 5000, 0.6: 3000, 0.8: 2000}
    
    def get_dod_cycles(self, dod):
        """
        根据放电深度(DOD)获取最大循环次数
        
        参数：
        - dod: 放电深度
        
        返回：
        - 最大循环次数（线性插值）
        """
        # 线性插值
        dod_vals = np.array(list(self.dod_cycle.keys()))
        cycles = np.array(list(self.dod_cycle.values()))
        return np.interp(dod, dod_vals, cycles)
    
    def objective(self, x):
        """
        计算目标函数值
        
        参数：
        - x: 决策变量数组，形状为 (96) = [Pc(24), Pd(24), abandon(24), L_shift_actual(24)]
        
        返回：
        - 目标函数值数组 [成本, 弃电率, 寿命损失]
        """
        # 解析决策变量
        Pc = x[:24]  # 充电功率
        Pd = x[24:48]  # 放电功率
        abandon = x[48:72]  # 弃电量
        L_shift_actual = x[72:96]  # 实际负荷转移量
        
        # 实际参与计算的负荷 = 基础不可转移负荷 + 优化分配的转移负荷
        actual_load = self.base_load + L_shift_actual
        
        # 功率平衡计算
        net_load = actual_load - (self.wind + self.pv - abandon)
        Pgrid = net_load + Pd - Pc   # 正表示购电，负表示售电
        Pbuy = np.maximum(Pgrid, 0)  # 购电量
        Psell = -np.minimum(Pgrid, 0)  # 售电量
        
        # 目标1: 运行成本
        cost_buy = np.sum(self.price_buy * Pbuy)  # 购电成本
        revenue_sell = np.sum(self.price_sell * Psell)  # 售电收入
        cost_om = 500  # 元/天，固定运维成本
        F1 = cost_buy - revenue_sell + cost_om  # 总成本
        
        # 目标2: 弃风弃光率
        total_renewable = self.wind + self.pv  # 总可再生能源
        F2 = np.sum(abandon) / (np.sum(total_renewable) + 1e-6)  # 弃电率
        
        # 目标3: 寿命损耗
        # 计算每个时段的放电深度 DOD
        dt = 1.0  # 时间步长（小时）
        dod = np.zeros(24)  # 放电深度
        soc = np.zeros(24)  # 荷电状态
        soc_init = 0.5  # 初始 SOC
        for t in range(24):
            soc_prev = soc_init if t == 0 else soc[t-1]
            if Pc[t] > 0:
                # 充电时SOC增加
                soc[t] = soc_prev + (Pc[t] * dt * self.eta_c) / self.E_rated
            elif Pd[t] > 0:
                # 放电时SOC减少
                soc[t] = soc_prev - (Pd[t] * dt) / (self.eta_d * self.E_rated)
            else:
                # 无充放电时SOC不变
                soc[t] = soc_prev
            # 计算放电深度：若放电，则 DOD = (1 - soc) 近似
            if Pd[t] > 0:
                dod[t] = 1 - soc[t]
        # 寿命损耗 = 1/N(DOD)，其中N(DOD)是对应放电深度的循环次数
        cycles = self.get_dod_cycles(dod)
        F3 = np.sum(1.0 / (cycles + 1e-6))
        
        return np.array([F1, F2, F3])
    
    def constraints(self, x):
        """
        计算约束违反量
        
        参数：
        - x: 决策变量数组
        
        返回：
        - 约束违反量总和
        """
        # 解析决策变量
        Pc = x[:24]  # 充电功率
        Pd = x[24:48]  # 放电功率
        abandon = x[48:72]  # 弃电量
        L_shift_actual = x[72:96]  # 实际负荷转移量
        
        violations = 0.0  # 约束违反量
        
        # 需求响应能量守恒约束：分配的总转移负荷必须等于设定的总转移负荷
        shift_diff = abs(np.sum(L_shift_actual) - self.total_shift_energy)
        violations += shift_diff * 50  # 施加强惩罚，确保能量守恒
        
        # SOC 动态约束
        soc = np.zeros(24)
        soc_init = 0.5
        for t in range(24):
            soc_prev = soc_init if t == 0 else soc[t-1]
            if Pc[t] > 0:
                delta = (Pc[t] * 1.0 * self.eta_c) / self.E_rated
            elif Pd[t] > 0:
                delta = -(Pd[t] * 1.0) / (self.eta_d * self.E_rated)
            else:
                delta = 0
            soc[t] = soc_prev + delta
            # SOC 上下限约束
            if soc[t] < self.soc_min:
                violations += (self.soc_min - soc[t]) * 10
            if soc[t] > self.soc_max:
                violations += (soc[t] - self.soc_max) * 10
        
        # 充放电功率限制
        violations += np.sum(np.maximum(0, Pc - self.P_rated)) * 1  # 充电功率上限
        violations += np.sum(np.maximum(0, -Pc)) * 1  # 充电功率下限（非负）
        violations += np.sum(np.maximum(0, Pd - self.P_rated)) * 1  # 放电功率上限
        violations += np.sum(np.maximum(0, -Pd)) * 1  # 放电功率下限（非负）
        
        # 电网功率限制
        actual_load = self.base_load + L_shift_actual
        net_load = actual_load - (self.wind + self.pv - abandon)
        Pgrid = net_load + Pd - Pc
        Pbuy = np.maximum(Pgrid, 0)  # 购电量
        Psell = -np.minimum(Pgrid, 0)  # 售电量
        violations += np.sum(np.maximum(0, Pbuy - self.grid_max)) * 0.5  # 购电上限
        violations += np.sum(np.maximum(0, Psell - self.grid_max)) * 0.5  # 售电上限
        
        # 弃电限制
        total_renewable = self.wind + self.pv
        violations += np.sum(np.maximum(0, abandon - total_renewable)) * 1  # 弃电上限
        violations += np.sum(np.maximum(0, -abandon)) * 1  # 弃电下限（非负）
        
        return violations
    
    def calculate_soc_curve(self, Pc, Pd):
        """
        计算SOC曲线
        
        参数：
        - Pc: 充电功率数组
        - Pd: 放电功率数组
        
        返回：
        - SOC曲线数组
        """
        soc = np.zeros(24)
        soc_init = 0.5  # 初始 SOC
        for t in range(24):
            soc_prev = soc_init if t == 0 else soc[t-1]
            if Pc[t] > 0:
                # 充电时SOC增加
                soc[t] = soc_prev + (Pc[t] * 1.0 * self.eta_c) / self.E_rated
            elif Pd[t] > 0:
                # 放电时SOC减少
                soc[t] = soc_prev - (Pd[t] * 1.0) / (self.eta_d * self.E_rated)
            else:
                # 无充放电时SOC不变
                soc[t] = soc_prev
            # 确保SOC在合理范围内
            soc[t] = np.clip(soc[t], self.soc_min, self.soc_max)
        return soc
