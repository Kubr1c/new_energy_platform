from .dispatch_model import DispatchModel
from .awpso import AWPSO
from .pso import PSO
from .ga import GA
import numpy as np


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------

def _build_model_and_bounds(forecasts, price_buy, price_sell, ess_params, dr_ratio):
    """根据预报数据和参数构造 DispatchModel 及决策变量上下界。"""
    default_params = {
        'ess_capacity': 40.0,
        'ess_power':    20.0,
        'eta_c':  0.95,
        'eta_d':  0.95,
        'soc_min': 0.1,
        'soc_max': 0.9,
        'grid_max': 30.0,
    }

    if ess_params:
        norm = dict(ess_params)
        if 'capacity' in norm and 'ess_capacity' not in norm:
            norm['ess_capacity'] = norm.pop('capacity')
        if 'power' in norm and 'ess_power' not in norm:
            norm['ess_power'] = norm.pop('power')
        allowed = set(default_params.keys())
        default_params.update({k: v for k, v in norm.items() if k in allowed})

    wind = forecasts.get('wind') or forecasts.get('wind_power')
    pv   = forecasts.get('pv')   or forecasts.get('pv_power')
    load = forecasts.get('load')

    missing = [k for k, v in [('wind/wind_power', wind), ('pv/pv_power', pv), ('load', load)] if v is None]
    if missing:
        raise KeyError(f"missing forecast keys: {', '.join(missing)}")

    model = DispatchModel(wind, pv, load, price_buy, price_sell,
                          **default_params, dr_ratio=dr_ratio)

    dim = 96  # Pc(24) + Pd(24) + abandon(24) + L_shift_actual(24)
    max_shift = np.max(model.load) * 1.5
    bounds = [
        np.zeros(dim),
        np.array([model.P_rated]*24 + [model.P_rated]*24
                 + list(model.wind + model.pv) + [max_shift]*24),
    ]
    return model, dim, bounds


def _extract_result(model, best_x, best_obj, best_constr, fitness_history, weights):
    """从优化结果向量中提取可读的调度方案字典。"""
    Pc             = best_x[:24]
    Pd             = best_x[24:48]
    abandon        = best_x[48:72]
    L_shift_actual = best_x[72:96]

    actual_load = model.base_load + L_shift_actual
    soc         = model.calculate_soc_curve(Pc, Pd)

    total_renewable = model.wind + model.pv
    abandon_rate = float(np.sum(abandon) / (np.sum(total_renewable) + 1e-6))

    return {
        'charge_plan':           Pc.tolist(),
        'discharge_plan':        Pd.tolist(),
        'soc_curve':             soc.tolist(),
        'abandon_plan':          abandon.tolist(),
        'demand_response_plan':  L_shift_actual.tolist(),
        'actual_load_profile':   actual_load.tolist(),
        'abandon_rate':          abandon_rate,
        'total_cost':            float(best_obj[0]),
        'constraint_violation':  float(best_constr),
        'fitness_history':       fitness_history,
        'weights':               weights.tolist(),
        'objectives': {
            'cost':        float(best_obj[0]),
            'abandon_rate': float(best_obj[1]),
            'life_loss':   float(best_obj[2]),
        },
    }


def _make_optimizer(algorithm, obj_func, constr_func, dim, bounds, fast=False):
    """创建优化器实例。fast=True 时减少迭代次数，适用于多目标批量运行。"""
    n_iter = 60 if fast else 100
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
    """如果 b 支配 a（b 在所有目标上不比 a 差，且至少一个更好），返回 True。"""
    return (np.all(b_obj <= a_obj)) and (np.any(b_obj < a_obj))


def _pareto_filter(solutions):
    """
    从解列表中保留非支配解（帕累托前沿）。
    解列表中每个元素必须包含 'objectives' 字典，键为 cost / abandon_rate / life_loss。
    如果所有解都被支配或前沿为空，返回原列表（降级保守处理）。
    """
    objs = np.array([
        [s['objectives']['cost'],
         s['objectives']['abandon_rate'],
         s['objectives']['life_loss']]
        for s in solutions
    ])

    n = len(objs)
    is_non_dominated = np.ones(n, dtype=bool)

    for i in range(n):
        if not is_non_dominated[i]:
            continue
        for j in range(n):
            if i == j or not is_non_dominated[j]:
                continue
            if _is_dominated(objs[i], objs[j]):
                is_non_dominated[i] = False
                break

    front = [s for s, keep in zip(solutions, is_non_dominated) if keep]
    return front if front else solutions   # 安全降级


# ---------------------------------------------------------------------------
# 单目标调度（公开接口）
# ---------------------------------------------------------------------------

def solve_dispatch(forecasts, price_buy, price_sell,
                   ess_params=None, dr_ratio=0.2,
                   algorithm='awpso', weights=None):
    """
    执行单目标加权调度优化。

    参数：
        weights: [w_cost, w_abandon, w_life]，不传则使用默认 [0.4, 0.3, 0.3]
    """
    weights_arr = np.array(weights if weights is not None else [0.4, 0.3, 0.3], dtype=float)
    weights_arr = weights_arr / (weights_arr.sum() + 1e-12)

    model, dim, bounds = _build_model_and_bounds(
        forecasts, price_buy, price_sell, ess_params, dr_ratio)

    optimizer = _make_optimizer(algorithm, model.objective, model.constraints, dim, bounds)
    best_x, best_obj, best_constr, fitness_history = optimizer.optimize(weights=weights_arr)

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

    权重组合（成本 / 弃电 / 寿命）：
        W1 [0.6, 0.2, 0.2]  侧重经济性
        W2 [0.2, 0.6, 0.2]  侧重消纳率
        W3 [0.2, 0.2, 0.6]  侧重电池寿命
        W4 [0.4, 0.3, 0.3]  均衡折中（与单目标默认权重相同）

    返回：
        {
          'solutions': [解1, 解2, ...],          # 全部帕累托前沿解
          'best_solution': {...},                 # 综合加权最优（W4 对应的解）
          'pareto_objectives': [[F1,F2,F3], ...]  # 便于前端绘制散点图
        }
    """
    weight_combinations = [
        [0.6, 0.2, 0.2],   # 侧重成本
        [0.2, 0.6, 0.2],   # 侧重弃电
        [0.2, 0.2, 0.6],   # 侧重寿命
        [0.4, 0.3, 0.3],   # 均衡
    ]

    weight_labels = ['侧重成本', '侧重消纳', '侧重寿命', '均衡折中']

    model, dim, bounds = _build_model_and_bounds(
        forecasts, price_buy, price_sell, ess_params, dr_ratio)

    all_solutions = []

    for idx, w_list in enumerate(weight_combinations):
        w = np.array(w_list, dtype=float)
        w = w / w.sum()

        # 每组权重独立运行优化器（fast 模式减少迭代次数）
        optimizer = _make_optimizer(
            algorithm, model.objective, model.constraints, dim, bounds, fast=True)
        best_x, best_obj, best_constr, fitness_history = optimizer.optimize(weights=w)

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
