"""
遗传算法 (Genetic Algorithm, GA)

算法原理：
- 基于自然选择和遗传变异的随机搜索算法
- 使用实数编码，适合连续优化问题
- 通过选择、交叉、变异操作迭代进化种群
- 支持多目标优化，通过加权和将多目标转化为单目标
- 处理约束条件，通过惩罚函数将约束优化问题转化为无约束优化问题

使用场景：
- 复杂非线性优化问题
- 多目标资源分配
- 参数优化
"""
import numpy as np
from optimization.pso import PENALTY_COEFF


class GA:
    """
    遗传算法类（基于实数编码）
    
    该类实现了基于实数编码的遗传算法，通过模拟生物进化过程
    寻找最优解，适用于复杂的连续优化问题。
    """
    
    def __init__(self, obj_func, constr_func, dim, bounds, 
                 pop_size=50, max_iter=200, crossover_rate=0.8, mutation_rate=0.1):
        """
        初始化遗传算法
        
        Args:
            obj_func (function): 目标函数，返回长度为3的数组 [成本, 弃风率, 寿命损失]
            constr_func (function): 约束函数，返回约束违反值
            dim (int): 优化变量维度
            bounds (list): 变量边界，格式为 [下界数组, 上界数组]
            pop_size (int, optional): 种群大小，默认50
            max_iter (int, optional): 最大迭代次数，默认200
            crossover_rate (float, optional): 交叉概率，默认0.8
            mutation_rate (float, optional): 变异概率，默认0.1
        """
        self.obj_func = obj_func  # 目标函数
        self.constr_func = constr_func  # 约束函数
        self.dim = dim  # 优化变量维度
        self.bounds = bounds  # 变量边界
        self.pop_size = pop_size  # 种群大小
        self.max_iter = max_iter  # 最大迭代次数
        self.crossover_rate = crossover_rate  # 交叉概率
        self.mutation_rate = mutation_rate  # 变异概率
        
    def evaluate(self, pop, weights):
        """
        评估种群适应度
        
        Args:
            pop (np.ndarray): 种群矩阵，形状为 (pop_size, dim)
            weights (np.ndarray): 目标权重数组
        
        Returns:
            tuple: (objs, constrs, fitness)
                - objs: 每个个体的目标值
                - constrs: 每个个体的约束违反值
                - fitness: 每个个体的适应度值
        """
        objs = np.array([self.obj_func(ind) for ind in pop])  # 计算每个个体的目标值
        constrs = np.array([self.constr_func(ind) for ind in pop])  # 计算每个个体的约束违反值
        fitness = np.array([np.dot(ob, weights) for ob in objs])  # 计算加权适应度
        # 约束硬惩罚机制（使用统一惩罚系数）
        fitness += constrs * PENALTY_COEFF
        return objs, constrs, fitness

    def optimize(self, weights=None):
        """
        执行优化过程
        
        Args:
            weights (list, optional): 目标权重，长度为3的数组 [w_cost, w_abandon, w_life]，默认 [0.4, 0.3, 0.3]
        
        Returns:
            tuple: (gbest, gbest_obj, gbest_constr, fitness_history)
                - gbest: 全局最优解
                - gbest_obj: 全局最优解对应的目标值
                - gbest_constr: 全局最优解的约束违反值
                - fitness_history: 适应度历史记录
        """
        # 处理权重参数，确保权重归一化
        weights = np.array(weights if weights is not None else [0.4, 0.3, 0.3], dtype=float)
        weights = weights / (weights.sum() + 1e-12)  # 归一化处理，避免除零错误
        
        # 初始化种群
        pop = np.random.uniform(self.bounds[0], self.bounds[1], (self.pop_size, self.dim))  # 随机生成初始种群
        objs, constrs, fitness = self.evaluate(pop, weights)  # 评估初始种群
        
        # 记录全局最优
        gbest_idx = np.argmin(fitness)  # 找到初始最优个体索引
        gbest = pop[gbest_idx].copy()  # 全局最优解
        gbest_obj = objs[gbest_idx].copy()  # 全局最优目标值
        gbest_constr = constrs[gbest_idx]  # 全局最优约束违反值
        gbest_fitness = fitness[gbest_idx]  # 全局最优适应度
        
        fitness_history = []  # 记录适应度历史
        
        # 开始迭代优化
        for iter in range(self.max_iter):
            new_pop = []
            
            # 选择操作 (锦标赛选择法)
            for _ in range(self.pop_size):
                # 随机选择两个个体进行锦标赛
                idx1, idx2 = np.random.randint(0, self.pop_size, 2)
                # 选择适应度较好的个体
                if fitness[idx1] < fitness[idx2]:
                    new_pop.append(pop[idx1].copy())
                else:
                    new_pop.append(pop[idx2].copy())
                    
            new_pop = np.array(new_pop)  # 转换为numpy数组
            
            # 交叉操作 (算术交叉)
            for i in range(0, self.pop_size, 2):
                # 确保有两个个体进行交叉，且满足交叉概率
                if i + 1 < self.pop_size and np.random.rand() < self.crossover_rate:
                    alpha = np.random.rand(self.dim)  # 生成交叉因子
                    parent1 = new_pop[i].copy()  # 父代1
                    parent2 = new_pop[i+1].copy()  # 父代2
                    # 执行算术交叉
                    new_pop[i] = alpha * parent1 + (1 - alpha) * parent2
                    new_pop[i+1] = alpha * parent2 + (1 - alpha) * parent1
                    
            # 变异操作 (均匀变异)
            for i in range(self.pop_size):
                # 满足变异概率
                if np.random.rand() < self.mutation_rate:
                    mutation_mask = np.random.rand(self.dim) < 0.1  # 10%的基因突变
                    random_values = np.random.uniform(self.bounds[0], self.bounds[1])  # 生成随机值
                    new_pop[i][mutation_mask] = random_values[mutation_mask]  # 执行变异
            
            # 边界处理：确保个体在边界内
            pop = np.clip(new_pop, self.bounds[0], self.bounds[1])
            
            # 重新评估种群
            objs, constrs, fitness = self.evaluate(pop, weights)
            
            # 更新全局最优
            current_best_idx = np.argmin(fitness)  # 找到当前最优个体索引
            if fitness[current_best_idx] < gbest_fitness:  # 如果找到更优解
                gbest = pop[current_best_idx].copy()  # 更新全局最优解
                gbest_obj = objs[current_best_idx].copy()  # 更新全局最优目标值
                gbest_constr = constrs[current_best_idx]  # 更新全局最优约束违反值
                gbest_fitness = fitness[current_best_idx]  # 更新全局最优适应度
            
            # 输出优化进度
            if iter % 50 == 0:
                print(f"[GA] Iteration {iter}: Best fitness = {gbest_fitness:.6f}, Constraint violation = {gbest_constr:.6f}")
                
            # 记录历史最优适应度
            fitness_history.append(float(gbest_fitness))
        
        # 返回优化结果
        return gbest, gbest_obj, gbest_constr, fitness_history
