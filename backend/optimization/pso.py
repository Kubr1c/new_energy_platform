import numpy as np

class PSO:
    def __init__(self, obj_func, constr_func, dim, bounds, 
                 n_particles=50, max_iter=200, w=0.7, c1=2.0, c2=2.0):
        self.obj_func = obj_func
        self.constr_func = constr_func
        self.dim = dim
        self.bounds = bounds
        self.n_particles = n_particles
        self.max_iter = max_iter
        self.w = w
        self.c1 = c1
        self.c2 = c2
        
    def optimize(self):
        # 初始化
        pos = np.random.uniform(self.bounds[0], self.bounds[1], (self.n_particles, self.dim))
        vel = np.random.uniform(-1, 1, (self.n_particles, self.dim))
        pbest = pos.copy()
        pbest_obj = np.array([self.obj_func(p) for p in pos])
        pbest_constr = np.array([self.constr_func(p) for p in pos])
        
        # 针对调度问题：默认权重分配 (同AWPSO一样，用于打平多维度的目标函数)
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
            # 固定惯性权重
            w = self.w
            
            # 更新速度和位置
            r1 = np.random.rand(self.n_particles, self.dim)
            r2 = np.random.rand(self.n_particles, self.dim)
            
            vel = w * vel + self.c1 * r1 * (pbest - pos) + self.c2 * r2 * (gbest - pos)
            pos = pos + vel
            
            # 边界处理 (Clip to bounds)
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
                print(f"[PSO] Iteration {iter}: Best fitness = {fitness[best_idx]:.6f}, Constraint violation = {new_constr[best_idx]:.6f}")
                
            # 记录历史最优适应度
            fitness_history.append(float(np.dot(gbest_obj, weights) + gbest_constr * 10))
        
        return gbest, gbest_obj, gbest_constr, fitness_history
