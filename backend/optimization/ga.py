import numpy as np
from optimization.pso import PENALTY_COEFF


class GA:
    def __init__(self, obj_func, constr_func, dim, bounds, 
                 pop_size=50, max_iter=200, crossover_rate=0.8, mutation_rate=0.1):
        """
        标准遗传算法 (基于实数编码)
        """
        self.obj_func = obj_func
        self.constr_func = constr_func
        self.dim = dim
        self.bounds = bounds
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        
    def evaluate(self, pop, weights):
        objs = np.array([self.obj_func(ind) for ind in pop])
        constrs = np.array([self.constr_func(ind) for ind in pop])
        fitness = np.array([np.dot(ob, weights) for ob in objs])
        # 约束硬惩罚机制（使用统一惩罚系数）
        fitness += constrs * PENALTY_COEFF
        return objs, constrs, fitness

    def optimize(self, weights=None):
        """
        weights: 长度为 3 的数组 [w_cost, w_abandon, w_life]，默认 [0.4, 0.3, 0.3]
        """
        weights = np.array(weights if weights is not None else [0.4, 0.3, 0.3], dtype=float)
        weights = weights / (weights.sum() + 1e-12)
        # 初始化种群
        pop = np.random.uniform(self.bounds[0], self.bounds[1], (self.pop_size, self.dim))
        objs, constrs, fitness = self.evaluate(pop, weights)
        
        # 记录全局最优
        gbest_idx = np.argmin(fitness)
        gbest = pop[gbest_idx].copy()
        gbest_obj = objs[gbest_idx].copy()
        gbest_constr = constrs[gbest_idx]
        gbest_fitness = fitness[gbest_idx]
        
        fitness_history = []
        
        for iter in range(self.max_iter):
            new_pop = []
            
            # 选择操作 (锦标赛选择法)
            for _ in range(self.pop_size):
                idx1, idx2 = np.random.randint(0, self.pop_size, 2)
                if fitness[idx1] < fitness[idx2]:
                    new_pop.append(pop[idx1].copy())
                else:
                    new_pop.append(pop[idx2].copy())
                    
            new_pop = np.array(new_pop)
            
            # 交叉操作 (算术交叉)
            for i in range(0, self.pop_size, 2):
                if i + 1 < self.pop_size and np.random.rand() < self.crossover_rate:
                    alpha = np.random.rand(self.dim)
                    parent1 = new_pop[i].copy()
                    parent2 = new_pop[i+1].copy()
                    new_pop[i] = alpha * parent1 + (1 - alpha) * parent2
                    new_pop[i+1] = alpha * parent2 + (1 - alpha) * parent1
                    
            # 变异操作 (均匀变异)
            for i in range(self.pop_size):
                if np.random.rand() < self.mutation_rate:
                    mutation_mask = np.random.rand(self.dim) < 0.1 # 10%的基因突变
                    random_values = np.random.uniform(self.bounds[0], self.bounds[1])
                    new_pop[i][mutation_mask] = random_values[mutation_mask]
            
            # 边界处理
            pop = np.clip(new_pop, self.bounds[0], self.bounds[1])
            
            # 重新评估
            objs, constrs, fitness = self.evaluate(pop, weights)
            
            # 更新全局最优
            current_best_idx = np.argmin(fitness)
            if fitness[current_best_idx] < gbest_fitness:
                gbest = pop[current_best_idx].copy()
                gbest_obj = objs[current_best_idx].copy()
                gbest_constr = constrs[current_best_idx]
                gbest_fitness = fitness[current_best_idx]
            
            # 输出进度
            if iter % 50 == 0:
                print(f"[GA] Iteration {iter}: Best fitness = {gbest_fitness:.6f}, Constraint violation = {gbest_constr:.6f}")
                
            # 记录历史最优适应度
            fitness_history.append(float(gbest_fitness))
        
        return gbest, gbest_obj, gbest_constr, fitness_history
