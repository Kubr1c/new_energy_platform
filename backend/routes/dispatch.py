"""
调度相关API路由
提供储能系统优化调度功能
"""

from flask import Blueprint, request, jsonify
from models.database import db, DispatchResult, PredictResult, StrategyConfig
from optimization.solver import solve_dispatch, solve_dispatch_multi_objective
from datetime import datetime, timedelta
import numpy as np

dispatch_bp = Blueprint('dispatch', __name__)

@dispatch_bp.route('/api/dispatch/exec', methods=['POST'])
def exec_dispatch():
    """
    执行优化调度接口
    
    请求参数：
        start_date: str - 调度开始日期（格式：YYYY-MM-DD）
        forecasts: dict - 预测数据（可选）
            wind_power: list - 风力发电预测值
            pv_power: list - 光伏发电预测值
            load: list - 负荷预测值
        price_buy: list - 购电价格（可选）
        price_sell: list - 售电价格（可选）
        ess_params: dict - 储能参数（可选）
        algorithm: str - 优化算法（可选，默认为 'awpso'）
        weights: list - 目标权重（可选，格式：[w_cost, w_abandon, w_life]）
    
    返回值：
        code: 200 - 调度执行成功
        data: dict - 调度结果
            dispatch_id: int - 调度记录ID
            schedule_date: str - 调度日期
            charge_plan: list - 充电计划
            discharge_plan: list - 放电计划
            soc_curve: list - 荷电状态曲线
            abandon_plan: list - 弃风弃光计划
            abandon_rate: float - 弃风弃光率
            total_cost: float - 总成本
            objectives: dict - 各目标值
            constraint_violation: dict - 约束违反情况
    
    错误处理：
        400 - 没有可用的预测数据或预测数据格式错误
        500 - 调度执行错误
    """
    try:
        data = request.json
        
        # 获取预测数据
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        
        # 读取分时电价策略
        strategy = StrategyConfig.query.first()
        dr_ratio = 0.2
        if strategy:
            price_map = {
                'extreme_peak': strategy.extreme_peak_price,
                'peak': strategy.peak_price,
                'flat': strategy.flat_price,
                'valley': strategy.valley_price,
                'deep_valley': strategy.deep_valley_price
            }
            tou_config = strategy.tou_config
            default_price_buy = [price_map.get(tou_config.get(str(h), 'flat'), strategy.flat_price) for h in range(24)]
            dr_ratio = strategy.dr_ratio
        else:
            default_price_buy = [500] * 24
            
        price_buy = data.get('price_buy', default_price_buy)
        price_sell = data.get('price_sell', [300] * 24)
        
        # 方式1：使用提供的预测数据
        if 'forecasts' in data:
            forecasts = data['forecasts']
        else:
            # 方式2：从数据库获取最新的预测结果
            latest_prediction = PredictResult.query.filter_by(
                predict_type='multi',
                horizon=24
            ).order_by(PredictResult.created_at.desc()).first()
            
            if not latest_prediction:
                return jsonify({'code': 400, 'message': '没有可用的预测数据，请先执行预测'})
            
            forecasts = latest_prediction.data
        
        # 验证预测数据格式
        required_keys = ['wind_power', 'pv_power', 'load']
        for key in required_keys:
            if key not in forecasts or len(forecasts[key]) != 24:
                return jsonify({'code': 400, 'message': f'预测数据格式错误，缺少{key}或长度不为24'})
        
        # 获取储能参数、选择的优化算法和目标权重
        ess_params = data.get('ess_params', {})
        algorithm  = data.get('algorithm', 'awpso')
        weights    = data.get('weights', None)   # [w_cost, w_abandon, w_life]

        # 调用优化求解器
        result = solve_dispatch(forecasts, price_buy, price_sell,
                                ess_params, dr_ratio=dr_ratio,
                                algorithm=algorithm, weights=weights)
        
        # 存入数据库
        dispatch_record = DispatchResult(
            schedule_date=start_date.date(),
            charge_plan=result['charge_plan'],
            discharge_plan=result['discharge_plan'],
            soc_curve=result['soc_curve'],
            abandon_rate=result['abandon_rate'],
            cost=result['total_cost']
        )
        db.session.add(dispatch_record)
        db.session.commit()
        
        return jsonify({
            'code': 200, 
            'data': {
                'dispatch_id': dispatch_record.id,
                'schedule_date': start_date.date().isoformat(),
                'charge_plan': result['charge_plan'],
                'discharge_plan': result['discharge_plan'],
                'soc_curve': result['soc_curve'],
                'abandon_plan': result['abandon_plan'],
                'abandon_rate': result['abandon_rate'],
                'total_cost': result['total_cost'],
                'objectives': result['objectives'],
                'constraint_violation': result['constraint_violation']
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'调度执行错误: {str(e)}'})

@dispatch_bp.route('/api/dispatch/multi_objective', methods=['POST'])
def exec_multi_objective_dispatch():
    """
    执行多目标优化调度接口
    
    请求参数：
        start_date: str - 调度开始日期（格式：YYYY-MM-DD）
        forecasts: dict - 预测数据（可选）
            wind_power: list - 风力发电预测值
            pv_power: list - 光伏发电预测值
            load: list - 负荷预测值
        price_buy: list - 购电价格（可选）
        price_sell: list - 售电价格（可选）
        ess_params: dict - 储能参数（可选）
        algorithm: str - 优化算法（可选，默认为 'awpso'）
    
    返回值：
        code: 200 - 调度执行成功
        data: dict - 调度结果
            dispatch_id: int - 调度记录ID
            schedule_date: str - 调度日期
            solutions: list - 帕累托前沿（非支配解集）
            all_solutions: list - 全部4个解（含被支配解）
            best_solution: dict - 综合最优解
            pareto_objectives: list - 帕累托目标坐标
            weight_labels: list - 权重标签
    
    错误处理：
        400 - 没有可用的预测数据或预测数据格式错误
        500 - 多目标调度执行错误
    """
    try:
        data = request.json
        
        # 获取预测数据（同单目标版本）
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        
        # 读取分时电价策略
        strategy = StrategyConfig.query.first()
        dr_ratio = 0.2
        if strategy:
            price_map = {
                'extreme_peak': strategy.extreme_peak_price,
                'peak': strategy.peak_price,
                'flat': strategy.flat_price,
                'valley': strategy.valley_price,
                'deep_valley': strategy.deep_valley_price
            }
            tou_config = strategy.tou_config
            default_price_buy = [price_map.get(tou_config.get(str(h), 'flat'), strategy.flat_price) for h in range(24)]
            dr_ratio = strategy.dr_ratio
        else:
            default_price_buy = [500] * 24
            
        price_buy = data.get('price_buy', default_price_buy)
        price_sell = data.get('price_sell', [300] * 24)
        
        if 'forecasts' in data:
            forecasts = data['forecasts']
        else:
            latest_prediction = PredictResult.query.filter_by(
                predict_type='multi',
                horizon=24
            ).order_by(PredictResult.created_at.desc()).first()
            
            if not latest_prediction:
                return jsonify({'code': 400, 'message': '没有可用的预测数据，请先执行预测'})
            
            forecasts = latest_prediction.data
        
        # 验证预测数据格式
        required_keys = ['wind_power', 'pv_power', 'load']
        for key in required_keys:
            if key not in forecasts or len(forecasts[key]) != 24:
                return jsonify({'code': 400, 'message': f'预测数据格式错误，缺少{key}或长度不为24'})
        
        # 获取储能参数和选择的优化算法
        ess_params = data.get('ess_params', {})
        algorithm  = data.get('algorithm', 'awpso')

        # 调用多目标优化求解器（真实传入不同权重，返回帕累托前沿）
        mo_result = solve_dispatch_multi_objective(
            forecasts, price_buy, price_sell,
            ess_params, dr_ratio=dr_ratio, algorithm=algorithm
        )

        best_solution = mo_result['best_solution']

        # 存储综合最优解到数据库
        dispatch_record = DispatchResult(
            schedule_date=start_date.date(),
            charge_plan=best_solution['charge_plan'],
            discharge_plan=best_solution['discharge_plan'],
            soc_curve=best_solution['soc_curve'],
            abandon_rate=best_solution['abandon_rate'],
            cost=best_solution['total_cost']
        )
        db.session.add(dispatch_record)
        db.session.commit()

        return jsonify({
            'code': 200,
            'data': {
                'dispatch_id':       dispatch_record.id,
                'schedule_date':     start_date.date().isoformat(),
                # 帕累托前沿（非支配解集）
                'solutions':         mo_result['solutions'],
                # 全部 4 个解（含被支配解，便于前端完整展示）
                'all_solutions':     mo_result['all_solutions'],
                # 综合最优解（均衡权重下最佳）
                'best_solution':     best_solution,
                # 帕累托目标坐标，便于前端绘制散点图
                'pareto_objectives': mo_result['pareto_objectives'],
                'weight_labels':     mo_result['weight_labels'],
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'多目标调度执行错误: {str(e)}'})

@dispatch_bp.route('/api/dispatch/history', methods=['GET'])
def get_dispatch_history():
    """
    获取调度历史接口
    
    查询参数：
        limit: int - 返回记录数（可选，默认为10）
        start_date: str - 开始日期（可选，格式：YYYY-MM-DD）
        end_date: str - 结束日期（可选，格式：YYYY-MM-DD）
    
    返回值：
        code: 200 - 获取成功
        data: list - 调度历史记录
            每个元素为调度记录字典
                id: int - 调度记录ID
                schedule_date: str - 调度日期
                charge_plan: list - 充电计划
                discharge_plan: list - 放电计划
                soc_curve: list - 荷电状态曲线
                abandon_rate: float - 弃风弃光率
                cost: float - 成本
                created_at: str - 创建时间
    
    错误处理：
        500 - 查询错误
    """
    try:
        # 获取查询参数
        limit = request.args.get('limit', 10, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 构建查询
        query = DispatchResult.query
        
        if start_date:
            query = query.filter(DispatchResult.schedule_date >= datetime.fromisoformat(start_date).date())
        if end_date:
            query = query.filter(DispatchResult.schedule_date <= datetime.fromisoformat(end_date).date())
        
        # 执行查询
        dispatches = query.order_by(DispatchResult.created_at.desc()).limit(limit).all()
        
        result = []
        for dispatch in dispatches:
            result.append({
                'id': dispatch.id,
                'schedule_date': dispatch.schedule_date.isoformat(),
                'charge_plan': dispatch.charge_plan,
                'discharge_plan': dispatch.discharge_plan,
                'soc_curve': dispatch.soc_curve,
                'abandon_rate': dispatch.abandon_rate,
                'cost': dispatch.cost,
                'created_at': dispatch.created_at.isoformat()
            })
        
        return jsonify({'code': 200, 'data': result})
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询错误: {str(e)}'})

@dispatch_bp.route('/api/dispatch/detail/<int:dispatch_id>', methods=['GET'])
def get_dispatch_detail(dispatch_id):
    """
    获取调度详情接口
    
    路径参数：
        dispatch_id: int - 调度记录ID
    
    返回值：
        code: 200 - 获取成功
        data: dict - 调度详情
            id: int - 调度记录ID
            schedule_date: str - 调度日期
            charge_plan: list - 充电计划
            discharge_plan: list - 放电计划
            soc_curve: list - 荷电状态曲线
            abandon_rate: float - 弃风弃光率
            cost: float - 成本
            statistics: dict - 统计信息
                total_charge: float - 总充电量
                total_discharge: float - 总放电量
                max_soc: float - 最大荷电状态
                min_soc: float - 最小荷电状态
                avg_soc: float - 平均荷电状态
                efficiency: float - 效率
            created_at: str - 创建时间
    
    错误处理：
        404 - 调度记录不存在
        500 - 查询错误
    """
    try:
        dispatch = DispatchResult.query.get(dispatch_id)
        if not dispatch:
            return jsonify({'code': 404, 'message': '调度记录不存在'})
        
        # 计算一些额外的统计信息
        charge_plan = np.array(dispatch.charge_plan)
        discharge_plan = np.array(dispatch.discharge_plan)
        soc_curve = np.array(dispatch.soc_curve)
        
        stats = {
            'total_charge': np.sum(charge_plan),
            'total_discharge': np.sum(discharge_plan),
            'max_soc': np.max(soc_curve),
            'min_soc': np.min(soc_curve),
            'avg_soc': np.mean(soc_curve),
            'efficiency': np.sum(discharge_plan) / (np.sum(charge_plan) + 1e-6)
        }
        
        return jsonify({
            'code': 200, 
            'data': {
                'id': dispatch.id,
                'schedule_date': dispatch.schedule_date.isoformat(),
                'charge_plan': dispatch.charge_plan,
                'discharge_plan': dispatch.discharge_plan,
                'soc_curve': dispatch.soc_curve,
                'abandon_rate': dispatch.abandon_rate,
                'cost': dispatch.cost,
                'statistics': stats,
                'created_at': dispatch.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询错误: {str(e)}'})

@dispatch_bp.route('/api/dispatch/simulate', methods=['POST'])
def simulate_dispatch():
    """
    模拟调度执行效果接口
    
    请求参数：
        dispatch_id: int - 调度记录ID
    
    返回值：
        code: 200 - 模拟成功
        data: dict - 模拟结果
            actual_wind: list - 实际风力发电数据
            actual_pv: list - 实际光伏发电数据
            actual_load: list - 实际负荷数据
            grid_power: list - 电网功率
            buy_power: list - 购电功率
            sell_power: list - 售电功率
            actual_cost: float - 实际成本
            planned_cost: float - 计划成本
            cost_deviation: float - 成本偏差
    
    错误处理：
        400 - 缺少调度ID或该日期没有实际数据
        404 - 调度记录不存在
        500 - 模拟错误
    """
    try:
        data = request.json
        dispatch_id = data.get('dispatch_id')
        
        if not dispatch_id:
            return jsonify({'code': 400, 'message': '缺少调度ID'})
        
        dispatch = DispatchResult.query.get(dispatch_id)
        if not dispatch:
            return jsonify({'code': 404, 'message': '调度记录不存在'})
        
        # 获取该日期的实际数据（用于对比）
        start_time = datetime.combine(dispatch.schedule_date, datetime.min.time())
        end_time = start_time + timedelta(hours=24)
        
        from models.database import NewEnergyData
        actual_data = NewEnergyData.query.filter(
            NewEnergyData.timestamp >= start_time,
            NewEnergyData.timestamp < end_time
        ).order_by(NewEnergyData.timestamp.asc()).all()
        
        if len(actual_data) == 0:
            return jsonify({'code': 400, 'message': '该日期没有实际数据，无法模拟'})
        
        # 提取实际数据，补齐到24小时
        actual_wind = [0.0] * 24
        actual_pv = [0.0] * 24
        actual_load = [0.0] * 24
        for i, item in enumerate(actual_data):
            if i < 24:
                actual_wind[i] = item.wind_power or 0
                actual_pv[i] = item.pv_power or 0
                actual_load[i] = item.load or 0
        
        # 模拟执行调度计划
        charge_plan = np.array(dispatch.charge_plan)
        discharge_plan = np.array(dispatch.discharge_plan)
        
        # 计算实际执行效果
        net_load = np.array(actual_load) - (np.array(actual_wind) + np.array(actual_pv))
        grid_power = net_load + discharge_plan - charge_plan
        
        # 计算成本（使用简化电价）
        price_buy = np.array([500] * 24)
        price_sell = np.array([300] * 24)
        
        buy_power = np.maximum(grid_power, 0)
        sell_power = -np.minimum(grid_power, 0)
        
        actual_cost = np.sum(price_buy * buy_power) - np.sum(price_sell * sell_power)
        
        simulation_result = {
            'actual_wind': actual_wind,
            'actual_pv': actual_pv,
            'actual_load': actual_load,
            'grid_power': grid_power.tolist(),
            'buy_power': buy_power.tolist(),
            'sell_power': sell_power.tolist(),
            'actual_cost': actual_cost,
            'planned_cost': dispatch.cost,
            'cost_deviation': actual_cost - dispatch.cost
        }
        
        return jsonify({
            'code': 200, 
            'data': simulation_result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'模拟错误: {str(e)}'})

@dispatch_bp.route('/api/dispatch/statistics', methods=['GET'])
def get_dispatch_statistics():
    """
    获取调度统计信息接口
    
    返回值：
        code: 200 - 获取成功
        data: dict - 统计信息
            total_dispatches: int - 总调度次数
            avg_cost: float - 平均成本
            avg_abandon_rate: float - 平均弃风弃光率
            total_savings: float - 总节约
    
    错误处理：
        500 - 统计错误
    """
    try:
        # 获取所有调度记录
        dispatches = DispatchResult.query.all()
        
        if not dispatches:
            return jsonify({
                'code': 200,
                'data': {
                    'total_dispatches': 0,
                    'avg_cost': 0,
                    'avg_abandon_rate': 0,
                    'total_savings': 0
                }
            })
        
        # 计算统计数据
        total_dispatches = len(dispatches)
        total_cost = sum(d.cost for d in dispatches if d.cost)
        avg_cost = total_cost / total_dispatches if total_dispatches > 0 else 0
        avg_abandon_rate = sum(d.abandon_rate for d in dispatches if d.abandon_rate) / total_dispatches if total_dispatches > 0 else 0
        
        # 计算总节约（简化计算）
        baseline_cost = total_dispatches * 15000  # 假设基准成本
        total_savings = baseline_cost - total_cost
        
        statistics = {
            'total_dispatches': total_dispatches,
            'avg_cost': round(avg_cost, 2),
            'avg_abandon_rate': round(avg_abandon_rate, 6),
            'total_savings': round(total_savings, 2)
        }
        
        return jsonify({
            'code': 200,
            'data': statistics
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'统计错误: {str(e)}'})
