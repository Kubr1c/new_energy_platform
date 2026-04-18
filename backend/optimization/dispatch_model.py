import numpy as np

class DispatchModel:
    def __init__(self, wind_forecast, pv_forecast, load_forecast, price_buy, price_sell,
                 ess_capacity=40.0, ess_power=20.0, eta_c=0.95, eta_d=0.95, 
                 soc_min=0.1, soc_max=0.9, grid_max=30.0, dr_ratio=0.2):
        """
        wind_forecast, pv_forecast, load_forecast: list of length 24 (MW)
        price_buy, price_sell: list of length 24 (元/MWh)
        """
        self.T = 24
        self.wind = np.array(wind_forecast)
        self.pv = np.array(pv_forecast)
        self.load = np.array(load_forecast)
        self.dr_ratio = dr_ratio
        self.base_load = self.load * (1 - self.dr_ratio)
        self.total_shift_energy = np.sum(self.load * self.dr_ratio)
        self.price_buy = np.array(price_buy)
        self.price_sell = np.array(price_sell)
        self.E_rated = ess_capacity   # MWh
        self.P_rated = ess_power      # MW
        self.eta_c = eta_c
        self.eta_d = eta_d
        self.soc_min = soc_min
        self.soc_max = soc_max
        self.grid_max = grid_max      # MW
        
        # 寿命曲线：DOD -> 最大循环次数 (拟合)
        self.dod_cycle = {0.1: 10000, 0.2: 8000, 0.4: 5000, 0.6: 3000, 0.8: 2000}
    
    def get_dod_cycles(self, dod):
        # 线性插值
        dod_vals = np.array(list(self.dod_cycle.keys()))
        cycles = np.array(list(self.dod_cycle.values()))
        return np.interp(dod, dod_vals, cycles)
    
    def objective(self, x):
        """
        x: 决策变量数组 shape (96) = [Pc(24), Pd(24), abandon(24), L_shift_actual(24)]
        """
        Pc = x[:24]
        Pd = x[24:48]
        abandon = x[48:72]
        L_shift_actual = x[72:96]
        
        # 实际参与计算的负荷 = 基础不可转移负荷 + 优化分配的转移负荷
        actual_load = self.base_load + L_shift_actual
        
        # 功率平衡约束由外部惩罚处理，这里计算目标值
        net_load = actual_load - (self.wind + self.pv - abandon)
        Pgrid = net_load + Pd - Pc   # 正表示购电，负表示售电
        Pbuy = np.maximum(Pgrid, 0)
        Psell = -np.minimum(Pgrid, 0)
        
        # 目标1: 运行成本
        cost_buy = np.sum(self.price_buy * Pbuy)
        revenue_sell = np.sum(self.price_sell * Psell)
        cost_om = 500  # 元/天，固定值
        F1 = cost_buy - revenue_sell + cost_om
        
        # 目标2: 弃风弃光率
        total_renewable = self.wind + self.pv
        F2 = np.sum(abandon) / (np.sum(total_renewable) + 1e-6)
        
        # 目标3: 寿命损耗
        # 需要计算每个时段的放电深度 DOD
        dt = 1.0
        dod = np.zeros(24)
        soc = np.zeros(24)
        soc_init = 0.5  # 初始 SOC
        for t in range(24):
            soc_prev = soc_init if t == 0 else soc[t-1]
            if Pc[t] > 0:
                soc[t] = soc_prev + (Pc[t] * dt * self.eta_c) / self.E_rated
            elif Pd[t] > 0:
                soc[t] = soc_prev - (Pd[t] * dt) / (self.eta_d * self.E_rated)
            else:
                soc[t] = soc_prev
            # 计算放电深度：若放电，则 DOD = (1 - soc) 近似
            if Pd[t] > 0:
                dod[t] = 1 - soc[t]
        # 寿命损耗 = 1/N(DOD)
        cycles = self.get_dod_cycles(dod)
        F3 = np.sum(1.0 / (cycles + 1e-6))
        
        return np.array([F1, F2, F3])
    
    def constraints(self, x):
        """返回约束违反量"""
        Pc = x[:24]
        Pd = x[24:48]
        abandon = x[48:72]
        L_shift_actual = x[72:96]
        
        violations = 0.0
        
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
            # SOC 上下限 - 降低惩罚系数
            if soc[t] < self.soc_min:
                violations += (self.soc_min - soc[t]) * 10
            if soc[t] > self.soc_max:
                violations += (soc[t] - self.soc_max) * 10
        
        # 充放电功率限制 - 降低惩罚系数
        violations += np.sum(np.maximum(0, Pc - self.P_rated)) * 1
        violations += np.sum(np.maximum(0, -Pc)) * 1
        violations += np.sum(np.maximum(0, Pd - self.P_rated)) * 1
        violations += np.sum(np.maximum(0, -Pd)) * 1
        
        # 电网功率限制 - 降低惩罚系数
        actual_load = self.base_load + L_shift_actual
        net_load = actual_load - (self.wind + self.pv - abandon)
        Pgrid = net_load + Pd - Pc
        Pbuy = np.maximum(Pgrid, 0)
        Psell = -np.minimum(Pgrid, 0)
        violations += np.sum(np.maximum(0, Pbuy - self.grid_max)) * 0.5
        violations += np.sum(np.maximum(0, Psell - self.grid_max)) * 0.5
        
        # 弃电限制 - 降低惩罚系数
        total_renewable = self.wind + self.pv
        violations += np.sum(np.maximum(0, abandon - total_renewable)) * 1
        violations += np.sum(np.maximum(0, -abandon)) * 1
        
        return violations
    
    def calculate_soc_curve(self, Pc, Pd):
        """计算SOC曲线"""
        soc = np.zeros(24)
        soc_init = 0.5  # 初始 SOC
        for t in range(24):
            soc_prev = soc_init if t == 0 else soc[t-1]
            if Pc[t] > 0:
                soc[t] = soc_prev + (Pc[t] * 1.0 * self.eta_c) / self.E_rated
            elif Pd[t] > 0:
                soc[t] = soc_prev - (Pd[t] * 1.0) / (self.eta_d * self.E_rated)
            else:
                soc[t] = soc_prev
            # 确保SOC在合理范围内
            soc[t] = np.clip(soc[t], self.soc_min, self.soc_max)
        return soc
