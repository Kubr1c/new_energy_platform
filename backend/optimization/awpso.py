import numpy as np

class AWPSO:
    def __init__(self, obj_func, constr_func, dim, bounds, 
                 n_particles=50, max_iter=200, w_max=0.9, w_min=0.4, w_rand=0.2,
                 c1=1.5, c2=1.5):
        self.obj_func = obj_func
        self.constr_func = constr_func
        self.dim = dim
        self.bounds = bounds
        self.n_particles = n_particles
        self.max_iter = max_iter
        self.w_max = w_max
        self.w_min = w_min
        self.w_rand = w_rand
        self.c1 = c1
        self.c2 = c2
        
    def optimize(self):
        # 初始化
        pos = np.random.uniform(self.bounds[0], self.bounds[1], (self.n_particles, self.dim))
        vel = np.random.uniform(-1, 1, (self.n_particles, self.dim))
        pbest = pos.copy()
        pbest_obj = np.array([self.obj_func(p) for p in pos])
        pbest_constr = np.array([self.constr_func(p) for p in pos])
        
        # 全局最优（帕累托前沿简化：选取加权和最小）
        weights = np.array([0.4, 0.3, 0.3])  # 成本、弃电、寿命权重
        fitness = np.array([np.dot(ob, weights) for ob in pbest_obj])
        # 添加约束惩罚
        fitness += pbest_constr * 100000
        
        gbest_idx = np.argmin(fitness)
        gbest = pos[gbest_idx].copy()
        gbest_obj = pbest_obj[gbest_idx].copy()
        gbest_constr = pbest_constr[gbest_idx]
        
        fitness_history = []
        
        for iter in range(self.max_iter):
            # 自适应惯性权重
            w = self.w_max - (self.w_max - self.w_min) * (iter / self.max_iter) + self.w_rand * np.random.rand()
            
            # 更新速度和位置
            r1 = np.random.rand(self.n_particles, self.dim)
            r2 = np.random.rand(self.n_particles, self.dim)
            
            vel = w * vel + self.c1 * r1 * (pbest - pos) + self.c2 * r2 * (gbest - pos)
            pos = pos + vel
            
            # 边界处理
            pos = np.clip(pos, self.bounds[0], self.bounds[1])
            
            # 计算新目标值和约束违反
            new_obj = np.array([self.obj_func(p) for p in pos])
            new_constr = np.array([self.constr_func(p) for p in pos])
            new_fitness = np.array([np.dot(ob, weights) for ob in new_obj]) + new_constr * 10
            
            # 更新 pbest
            improved = new_fitness < fitness
            pbest[improved] = pos[improved]
            pbest_obj[improved] = new_obj[improved]
            pbest_constr[improved] = new_constr[improved]
            fitness[improved] = new_fitness[improved]
            
            # 更新 gbest
            best_idx = np.argmin(fitness)
            if fitness[best_idx] < np.dot(gbest_obj, weights) + gbest_constr * 10:
                gbest = pos[best_idx].copy()
                gbest_obj = new_obj[best_idx].copy()
                gbest_constr = new_constr[best_idx]
            
            # 输出进度
            if iter % 50 == 0:
                print(f"Iteration {iter}: Best fitness = {fitness[best_idx]:.6f}, Constraint violation = {new_constr[best_idx]:.6f}")
                
            # 记录历史最优适应度
            fitness_history.append(float(np.dot(gbest_obj, weights) + gbest_constr * 10))
            
        return gbest, gbest_obj, gbest_constr, fitness_history
