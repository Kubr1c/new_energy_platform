"""
标准粒子群优化算法 (Particle Swarm Optimization, PSO)

算法原理：
- 基于群体智能的优化算法，模拟鸟群觅食行为
- 每个粒子根据自身经验（个人最优）和群体经验（全局最优）调整飞行方向
- 使用固定惯性权重，平衡全局搜索和局部搜索能力
- 支持多目标优化，通过加权和将多目标转化为单目标
- 处理约束条件，通过惩罚函数将约束优化问题转化为无约束优化问题

使用场景：
- 连续变量优化问题
- 多目标资源分配
- 参数优化
"""
import numpy as np

# 统一惩罚系数常量，所有算法(PSO/AWPSO/GA)使用同一个值
PENALTY_COEFF = 10000.0


class PSO:
    """
    标准粒子群优化算法类
    
    该类实现了标准粒子群优化算法，通过模拟鸟群的群体智能行为
    寻找最优解，适用于连续变量的优化问题。
    """
    
    def __init__(self, obj_func, constr_func, dim, bounds, 
                 n_particles=50, max_iter=200, w=0.7, c1=2.0, c2=2.0):
        """
        初始化PSO算法
        
        Args:
            obj_func (function): 目标函数，返回长度为3的数组 [成本, 弃风率, 寿命损失]
            constr_func (function): 约束函数，返回约束违反值
            dim (int): 优化变量维度
            bounds (list): 变量边界，格式为 [下界数组, 上界数组]
            n_particles (int, optional): 粒子数量，默认50
            max_iter (int, optional): 最大迭代次数，默认200
            w (float, optional): 惯性权重，默认0.7
            c1 (float, optional): 认知学习因子，默认2.0
            c2 (float, optional): 社会学习因子，默认2.0
        """
        self.obj_func = obj_func  # 目标函数
        self.constr_func = constr_func  # 约束函数
        self.dim = dim  # 优化变量维度
        self.bounds = bounds  # 变量边界
        self.n_particles = n_particles  # 粒子数量
        self.max_iter = max_iter  # 最大迭代次数
        self.w = w  # 惯性权重
        self.c1 = c1  # 认知学习因子
        self.c2 = c2  # 社会学习因子
        
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
        weights = weights / (weights.sum() + 1e-12)   # 归一化，防止传入未归一化的权重

        # 初始化粒子位置和速度
        pos = np.random.uniform(self.bounds[0], self.bounds[1], (self.n_particles, self.dim))  # 随机初始化位置
        vel = np.random.uniform(-1, 1, (self.n_particles, self.dim))  # 随机初始化速度
        pbest = pos.copy()  # 个人最优位置初始化
        pbest_obj = np.array([self.obj_func(p) for p in pos])  # 计算个人最优目标值
        pbest_constr = np.array([self.constr_func(p) for p in pos])  # 计算约束违反值
        
        # 计算适应度值
        fitness = np.array([np.dot(ob, weights) for ob in pbest_obj])
        # 添加约束惩罚（使用统一惩罚系数）
        fitness += pbest_constr * PENALTY_COEFF
        
        # 初始化全局最优解
        gbest_idx = np.argmin(fitness)  # 找到初始最优粒子索引
        gbest = pos[gbest_idx].copy()  # 全局最优位置
        gbest_obj = pbest_obj[gbest_idx].copy()  # 全局最优目标值
        gbest_constr = pbest_constr[gbest_idx]  # 全局最优约束违反值
        
        fitness_history = []  # 记录适应度历史
        
        # 开始迭代优化
        for iter in range(self.max_iter):
            # 固定惯性权重
            w = self.w
            
            # 生成随机数
            r1 = np.random.rand(self.n_particles, self.dim)  # 认知随机因子
            r2 = np.random.rand(self.n_particles, self.dim)  # 社会随机因子
            
            # 更新速度：惯性项 + 认知项 + 社会项
            # 惯性项：保持粒子当前运动趋势
            # 认知项：粒子向自身历史最优位置移动的趋势
            # 社会项：粒子向全局最优位置移动的趋势
            vel = w * vel + self.c1 * r1 * (pbest - pos) + self.c2 * r2 * (gbest - pos)
            # 更新位置
            pos = pos + vel
            
            # 边界处理：确保粒子在边界内
            pos = np.clip(pos, self.bounds[0], self.bounds[1])
            
            # 计算新的目标值和约束违反值
            new_obj = np.array([self.obj_func(p) for p in pos])
            new_constr = np.array([self.constr_func(p) for p in pos])
            # 计算新的适应度值
            new_fitness = np.array([np.dot(ob, weights) for ob in new_obj]) + new_constr * PENALTY_COEFF
            
            # 更新个人最优解
            improved = new_fitness < fitness  # 找出适应度改善的粒子
            pbest[improved] = pos[improved]  # 更新个人最优位置
            pbest_obj[improved] = new_obj[improved]  # 更新个人最优目标值
            pbest_constr[improved] = new_constr[improved]  # 更新个人最优约束违反值
            fitness[improved] = new_fitness[improved]  # 更新适应度
            
            # 更新全局最优解
            best_idx = np.argmin(fitness)  # 找到当前最优粒子索引
            gbest_fitness = np.dot(gbest_obj, weights) + gbest_constr * PENALTY_COEFF  # 计算当前全局最优适应度
            if fitness[best_idx] < gbest_fitness:  # 如果找到更优解
                gbest = pos[best_idx].copy()  # 更新全局最优位置
                gbest_obj = new_obj[best_idx].copy()  # 更新全局最优目标值
                gbest_constr = new_constr[best_idx]  # 更新全局最优约束违反值
            
            # 输出优化进度
            if iter % 50 == 0:
                print(f"[PSO] Iteration {iter}: Best fitness = {fitness[best_idx]:.6f}, Constraint violation = {new_constr[best_idx]:.6f}")
                
            # 记录历史最优适应度
            fitness_history.append(float(np.dot(gbest_obj, weights) + gbest_constr * PENALTY_COEFF))

        # 返回优化结果
        return gbest, gbest_obj, gbest_constr, fitness_history
