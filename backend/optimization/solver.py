"""
优化求解器模块

该模块提供了新能源车辆调度优化的核心功能，包括：
- 单目标调度优化
- 多目标调度优化
- 帕累托前沿筛选
- 不同优化算法的封装

使用场景：
- 新能源微电网调度
- 储能系统优化
- 需求响应调度
- 多目标资源分配
"""
from .dispatch_model import DispatchModel
from .awpso import AWPSO
from .pso import PSO
from .ga import GA
import numpy as np


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------

def _build_model_and_bounds(forecasts, price_buy, price_sell, ess_params, dr_ratio):
    """
    根据预报数据和参数构造 DispatchModel 及决策变量上下界。
    
    参数：
    - forecasts: 预报数据，包含 wind/pv/load
    - price_buy: 购电价格
    - price_sell: 售电价格
    - ess_params: 储能系统参数
    - dr_ratio: 需求响应比例
    
    返回：
    - model: DispatchModel 实例
    - dim: 优化变量维度
    - bounds: 变量边界
    """
    # 默认储能系统参数
    default_params = {
        'ess_capacity': 40.0,  # 储能容量（kWh）
        'ess_power':    20.0,  # 储能功率（kW）
        'eta_c':  0.95,        # 充电效率
        'eta_d':  0.95,        # 放电效率
        'soc_min': 0.1,        # 最小荷电状态
        'soc_max': 0.9,        # 最大荷电状态
        'grid_max': 30.0,      # 电网最大功率
    }

    # 处理用户提供的参数
    if ess_params:
        norm = dict(ess_params)
        # 参数名称兼容处理
        if 'capacity' in norm and 'ess_capacity' not in norm:
            norm['ess_capacity'] = norm.pop('capacity')
        if 'power' in norm and 'ess_power' not in norm:
            norm['ess_power'] = norm.pop('power')
        # 只保留允许的参数
        allowed = set(default_params.keys())
        default_params.update({k: v for k, v in norm.items() if k in allowed})

    # 提取预报数据
    wind = forecasts.get('wind') or forecasts.get('wind_power')
    pv   = forecasts.get('pv')   or forecasts.get('pv_power')
    load = forecasts.get('load')

    # 检查必需的预报数据
    missing = [k for k, v in [('wind/wind_power', wind), ('pv/pv_power', pv), ('load', load)] if v is None]
    if missing:
        raise KeyError(f"missing forecast keys: {', '.join(missing)}")

    # 创建调度模型
    model = DispatchModel(wind, pv, load, price_buy, price_sell,
                          **default_params, dr_ratio=dr_ratio)

    # 定义优化变量维度和边界
    dim = 96  # Pc(24) + Pd(24) + abandon(24) + L_shift_actual(24)
    max_shift = np.max(model.load) * 1.5  # 最大负荷转移量
    bounds = [
        np.zeros(dim),  # 下界
        np.array([model.P_rated]*24 + [model.P_rated]*24
                 + list(model.wind + model.pv) + [max_shift]*24),  # 上界
    ]
    return model, dim, bounds


def _extract_result(model, best_x, best_obj, best_constr, fitness_history, weights):
    """
    从优化结果向量中提取可读的调度方案字典。
    
    参数：
    - model: DispatchModel 实例
    - best_x: 最优解向量
    - best_obj: 最优目标值
    - best_constr: 约束违反值
    - fitness_history: 适应度历史
    - weights: 目标权重
    
    返回：
    - 调度方案字典
    """
    # 从解向量中提取各个变量
    Pc             = best_x[:24]        # 充电功率
    Pd             = best_x[24:48]      # 放电功率
    abandon        = best_x[48:72]      # 弃电量
    L_shift_actual = best_x[72:96]      # 负荷转移量

    # 计算实际负荷和SOC曲线
    actual_load = model.base_load + L_shift_actual
    soc         = model.calculate_soc_curve(Pc, Pd)

    # 计算弃电率
    total_renewable = model.wind + model.pv
    abandon_rate = float(np.sum(abandon) / (np.sum(total_renewable) + 1e-6))

    # 构造结果字典
    return {
        'charge_plan':           Pc.tolist(),           # 充电计划
        'discharge_plan':        Pd.tolist(),           # 放电计划
        'soc_curve':             soc.tolist(),           # SOC曲线
        'abandon_plan':          abandon.tolist(),       # 弃电计划
        'demand_response_plan':  L_shift_actual.tolist(), # 需求响应计划
        'actual_load_profile':   actual_load.tolist(),   # 实际负荷曲线
        'abandon_rate':          abandon_rate,          # 弃电率
        'total_cost':            float(best_obj[0]),    # 总成本
        'constraint_violation':  float(best_constr),    # 约束违反值
        'fitness_history':       fitness_history,       # 适应度历史
        'weights':               weights.tolist(),      # 使用的权重
        'objectives': {
            'cost':        float(best_obj[0]),    # 成本目标
            'abandon_rate': float(best_obj[1]),    # 弃电率目标
            'life_loss':   float(best_obj[2]),    # 寿命损失目标
        },
    }


def _make_optimizer(algorithm, obj_func, constr_func, dim, bounds, fast=False):
    """
    创建优化器实例。
    
    参数：
    - algorithm: 算法名称 ('pso', 'ga', 'awpso')
    - obj_func: 目标函数
    - constr_func: 约束函数
    - dim: 优化变量维度
    - bounds: 变量边界
    - fast: 是否使用快速模式（减少迭代次数）
    
    返回：
    - 优化器实例
    """
    n_iter = 60 if fast else 100  # 快速模式减少迭代次数
    if algorithm == 'pso':
        return PSO(obj_func, constr_func, dim, bounds,
                   n_particles=50, max_iter=n_iter)
    elif algorithm == 'ga':
        return GA(obj_func, constr_func, dim, bounds,
                  pop_size=50, max_iter=n_iter)
    else:  # awpso（默认）
        return AWPSO(obj_func, constr_func, dim, bounds,
                     n_particles=30, max_iter=n_iter)


# ---------------------------------------------------------------------------
# 帕累托支配
# ---------------------------------------------------------------------------

def _is_dominated(a_obj, b_obj):
    """
    判断解 b 是否支配解 a。
    如果 b 在所有目标上不比 a 差，且至少一个目标更好，则 b 支配 a。
    
    参数：
    - a_obj: 解 a 的目标值
    - b_obj: 解 b 的目标值
    
    返回：
    - bool: b 是否支配 a
    """
    return (np.all(b_obj <= a_obj)) and (np.any(b_obj < a_obj))


def _pareto_filter(solutions):
    """
    从解列表中保留非支配解（帕累托前沿）。
    
    参数：
    - solutions: 解列表，每个元素包含 'objectives' 字典
    
    返回：
    - 帕累托前沿解列表
    """
    # 提取所有解的目标值
    objs = np.array([
        [s['objectives']['cost'],
         s['objectives']['abandon_rate'],
         s['objectives']['life_loss']]
        for s in solutions
    ])

    n = len(objs)
    is_non_dominated = np.ones(n, dtype=bool)  # 标记是否为非支配解

    # 遍历所有解对，判断支配关系
    for i in range(n):
        if not is_non_dominated[i]:
            continue
        for j in range(n):
            if i == j or not is_non_dominated[j]:
                continue
            if _is_dominated(objs[i], objs[j]):
                is_non_dominated[i] = False
                break

    # 筛选出非支配解
    front = [s for s, keep in zip(solutions, is_non_dominated) if keep]
    return front if front else solutions   # 安全降级：如果没有非支配解，返回原列表


# ---------------------------------------------------------------------------
# 单目标调度（公开接口）
# ---------------------------------------------------------------------------

def solve_dispatch(forecasts, price_buy, price_sell,
                   ess_params=None, dr_ratio=0.2,
                   algorithm='awpso', weights=None):
    """
    执行单目标加权调度优化。

    参数：
    - forecasts: 预报数据，包含 wind/pv/load
    - price_buy: 购电价格
    - price_sell: 售电价格
    - ess_params: 储能系统参数
    - dr_ratio: 需求响应比例，默认0.2
    - algorithm: 优化算法，可选 'pso', 'ga', 'awpso'，默认 'awpso'
    - weights: 目标权重 [w_cost, w_abandon, w_life]，默认 [0.4, 0.3, 0.3]
    
    返回：
    - 调度方案字典
    """
    # 处理权重参数
    weights_arr = np.array(weights if weights is not None else [0.4, 0.3, 0.3], dtype=float)
    weights_arr = weights_arr / (weights_arr.sum() + 1e-12)  # 归一化处理

    # 构建模型和边界
    model, dim, bounds = _build_model_and_bounds(
        forecasts, price_buy, price_sell, ess_params, dr_ratio)

    # 创建优化器并执行优化
    optimizer = _make_optimizer(algorithm, model.objective, model.constraints, dim, bounds)
    best_x, best_obj, best_constr, fitness_history = optimizer.optimize(weights=weights_arr)

    # 提取结果
    return _extract_result(model, best_x, best_obj, best_constr, fitness_history, weights_arr)


# ---------------------------------------------------------------------------
# 多目标调度（公开接口）
# ---------------------------------------------------------------------------

def solve_dispatch_multi_objective(forecasts, price_buy, price_sell,
                                   ess_params=None, dr_ratio=0.2,
                                   algorithm='awpso'):
    """
    加权分解法（Scalarization）多目标优化：
    针对 4 组预设权重分别独立运行优化器，收集全部解后做帕累托支配筛选，
    返回非支配解集合（帕累托前沿近似）及综合最优解。

    参数：
    - forecasts: 预报数据，包含 wind/pv/load
    - price_buy: 购电价格
    - price_sell: 售电价格
    - ess_params: 储能系统参数
    - dr_ratio: 需求响应比例，默认0.2
    - algorithm: 优化算法，可选 'pso', 'ga', 'awpso'，默认 'awpso'

    权重组合（成本 / 弃电 / 寿命）：
        W1 [0.6, 0.2, 0.2]  侧重经济性
        W2 [0.2, 0.6, 0.2]  侧重消纳率
        W3 [0.2, 0.2, 0.6]  侧重电池寿命
        W4 [0.4, 0.3, 0.3]  均衡折中（与单目标默认权重相同）

    返回：
        {
          'solutions': [解1, 解2, ...],          # 全部帕累托前沿解
          'all_solutions': [解1, 解2, ...],       # 所有4个解
          'best_solution': {...},                 # 综合加权最优（W4 对应的解）
          'pareto_objectives': [[F1,F2,F3], ...]  # 便于前端绘制散点图
          'weight_combinations': [[w1,w2,w3], ...], # 权重组合
          'weight_labels': ['标签1', '标签2', ...]  # 权重标签
        }
    """
    # 定义权重组合
    weight_combinations = [
        [0.6, 0.2, 0.2],   # 侧重成本
        [0.2, 0.6, 0.2],   # 侧重弃电
        [0.2, 0.2, 0.6],   # 侧重寿命
        [0.4, 0.3, 0.3],   # 均衡
    ]

    # 权重标签
    weight_labels = ['侧重成本', '侧重消纳', '侧重寿命', '均衡折中']

    # 构建模型和边界
    model, dim, bounds = _build_model_and_bounds(
        forecasts, price_buy, price_sell, ess_params, dr_ratio)

    all_solutions = []

    # 对每组权重运行优化器
    for idx, w_list in enumerate(weight_combinations):
        w = np.array(w_list, dtype=float)
        w = w / w.sum()  # 归一化

        # 每组权重独立运行优化器（fast 模式减少迭代次数）
        optimizer = _make_optimizer(
            algorithm, model.objective, model.constraints, dim, bounds, fast=True)
        best_x, best_obj, best_constr, fitness_history = optimizer.optimize(weights=w)

        # 提取结果并添加标签
        result = _extract_result(model, best_x, best_obj, best_constr, fitness_history, w)
        result['label']        = weight_labels[idx]
        result['weight_index'] = idx
        all_solutions.append(result)

    # 帕累托支配筛选：保留非支配解
    pareto_front = _pareto_filter(all_solutions)

    # 综合最优：从帕累托前沿中选取均衡权重 [0.4,0.3,0.3] 下适应度最小的解
    balance_w = np.array([0.4, 0.3, 0.3])
    best_solution = min(
        pareto_front,
        key=lambda s: np.dot(
            [s['objectives']['cost'],
             s['objectives']['abandon_rate'],
             s['objectives']['life_loss']],
            balance_w
        )
    )

    # 构造返回结果
    return {
        'solutions':         pareto_front,
        'all_solutions':     all_solutions,   # 含所有 4 个解，便于前端展示全貌
        'best_solution':     best_solution,
        'pareto_objectives': [
            [s['objectives']['cost'],
             s['objectives']['abandon_rate'],
             s['objectives']['life_loss']]
            for s in pareto_front
        ],
        'weight_combinations': weight_combinations,
        'weight_labels':       weight_labels,
    }
