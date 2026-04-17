from .dispatch_model import DispatchModel
from .awpso import AWPSO
from .pso import PSO
from .ga import GA
import numpy as np

def solve_dispatch(forecasts, price_buy, price_sell, ess_params=None, dr_ratio=0.2, algorithm='awpso'):
    """
    forecasts: dict 包含 'wind', 'pv', 'load' 各24个值
    price_buy, price_sell: list of length 24
    ess_params: dict, 储能系统参数
    algorithm: str, 优化算法名称 ('awpso', 'pso', 'ga')
    """
    # 默认储能参数
    default_params = {
        'ess_capacity': 40.0,  # MWh
        'ess_power': 20.0,     # MW
        'eta_c': 0.95,
        'eta_d': 0.95,
        'soc_min': 0.1,
        'soc_max': 0.9,
        'grid_max': 30.0      # MW
    }
    
    if ess_params:
        # 兼容前端参数命名：capacity/power -> ess_capacity/ess_power
        normalized_params = dict(ess_params)
        if 'capacity' in normalized_params and 'ess_capacity' not in normalized_params:
            normalized_params['ess_capacity'] = normalized_params.pop('capacity')
        if 'power' in normalized_params and 'ess_power' not in normalized_params:
            normalized_params['ess_power'] = normalized_params.pop('power')

        # 只保留 DispatchModel 支持的参数，避免传入未知字段
        allowed_keys = {'ess_capacity', 'ess_power', 'eta_c', 'eta_d', 'soc_min', 'soc_max', 'grid_max'}
        filtered_params = {k: v for k, v in normalized_params.items() if k in allowed_keys}
        default_params.update(filtered_params)
    
    wind_forecast = forecasts.get('wind')
    if wind_forecast is None:
        wind_forecast = forecasts.get('wind_power')

    pv_forecast = forecasts.get('pv')
    if pv_forecast is None:
        pv_forecast = forecasts.get('pv_power')

    load_forecast = forecasts.get('load')

    if wind_forecast is None or pv_forecast is None or load_forecast is None:
        missing = []
        if wind_forecast is None:
            missing.append('wind/wind_power')
        if pv_forecast is None:
            missing.append('pv/pv_power')
        if load_forecast is None:
            missing.append('load')
        raise KeyError(f"missing forecast keys: {', '.join(missing)}")

    model = DispatchModel(
        wind_forecast,
        pv_forecast,
        load_forecast,
        price_buy, 
        price_sell,
        **default_params,
        dr_ratio=dr_ratio
    )
    
    # 决策变量维度：Pc(24) + Pd(24) + abandon(24) + L_shift_actual(24) = 96
    dim = 96
    
    # 限制单小时可容纳的最大转移负荷 (为原始负荷峰值的 1.5 倍)
    max_load = np.max(model.load)
    max_shift = max_load * 1.5

    bounds = [
        np.zeros(dim),  # 下界
        np.array([model.P_rated]*24 + [model.P_rated]*24 + [max_load]*24 + [max_shift]*24)  # 上界
    ]
    
    if algorithm == 'pso':
        optimizer = PSO(
            model.objective, 
            model.constraints, 
            dim, 
            bounds,
            n_particles=50,
            max_iter=100
        )
    elif algorithm == 'ga':
        optimizer = GA(
            model.objective, 
            model.constraints, 
            dim, 
            bounds,
            pop_size=50,
            max_iter=100
        )
    else:
        # Default to awpso
        optimizer = AWPSO(
            model.objective, 
            model.constraints, 
            dim, 
            bounds,
            n_particles=30,  # 减少粒子数以提高速度
            max_iter=100    # 减少迭代次数以提高速度
        )
    
    best_x, best_obj, best_constr, fitness_history = optimizer.optimize()
    
    # 提取结果
    Pc = best_x[:24]
    Pd = best_x[24:48]
    abandon = best_x[48:72]
    L_shift_actual = best_x[72:96]
    
    actual_load = model.base_load + L_shift_actual
    
    # 计算 SOC 曲线
    soc = model.calculate_soc_curve(Pc, Pd)
    
    # 计算弃风弃光率
    total_renewable = model.wind + model.pv
    abandon_rate = np.sum(abandon) / (np.sum(total_renewable) + 1e-6)
    
    return {
        'charge_plan': Pc.tolist(),
        'discharge_plan': Pd.tolist(),
        'soc_curve': soc.tolist(),
        'abandon_plan': abandon.tolist(),
        'demand_response_plan': L_shift_actual.tolist(),
        'actual_load_profile': actual_load.tolist(),
        'abandon_rate': abandon_rate,
        'total_cost': best_obj[0],
        'constraint_violation': best_constr,
        'fitness_history': fitness_history,
        'objectives': {
            'cost': best_obj[0],
            'abandon_rate': best_obj[1],
            'life_loss': best_obj[2]
        }
    }

def solve_dispatch_multi_objective(forecasts, price_buy, price_sell, ess_params=None, dr_ratio=0.2, algorithm='awpso'):
    """
    多目标优化版本，返回帕累托前沿解
    """
    # 这里可以实现多目标优化算法，如NSGA-II
    # 为简化，暂时返回单目标优化的多个解
    solutions = []
    
    # 使用不同的权重组合生成多个解
    weight_combinations = [
        [0.6, 0.2, 0.2],  # 侧重成本
        [0.2, 0.6, 0.2],  # 侧重弃电
        [0.2, 0.2, 0.6],  # 侧重寿命
        [0.4, 0.3, 0.3],  # 平衡
    ]
    
    for weights in weight_combinations:
        # 修改AWPSO/PSO/GA的权重设置
        # 为简化，暂未实现动态权重传入，直接调用单目标优化
        result = solve_dispatch(forecasts, price_buy, price_sell, ess_params, dr_ratio=dr_ratio, algorithm=algorithm)
        result['weights'] = weights
        solutions.append(result)
    
    return solutions
