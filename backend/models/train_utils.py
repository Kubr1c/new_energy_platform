"""
================================================================================
训练工具模块
================================================================================

【模块简介】
    本模块提供了一系列用于深度学习模型训练的实用工具函数和类。
    这些工具可以帮助开发者更高效、更规范地完成模型训练任务。

【主要功能】
    1. 高级训练技巧
       - EarlyStopping：早停机制，防止过拟合
       - LearningRateScheduler：学习率调度器，自动调整学习率

    2. 自定义损失函数
       - WeightedMSELoss：加权MSE损失，对不同时段赋予不同权重
       - HuberLoss：Huber损失，对异常值更鲁棒
       - CombinedLoss：组合损失，结合多种损失函数的优点

    3. 训练循环和评估
       - train_model：完整的模型训练流程
       - evaluate_model：模型评估

    4. 模型保存和加载
       - save_model：保存模型及元信息
       - load_model：加载模型

    5. 工厂函数
       - get_optimizer：获取优化器实例
       - get_loss_function：获取损失函数实例

【使用示例】
    # 创建早停机制
    early_stopping = EarlyStopping(patience=10, path='best_model.pt')

    # 创建学习率调度器
    scheduler = LearningRateScheduler(
        optimizer,
        mode='cosine',
        initial_lr=0.001,
        min_lr=1e-6
    )

    # 使用自定义损失函数
    loss_fn = WeightedMSELoss(peak_hours=[7, 8, 18, 19, 20], peak_weight=2.0)

    # 训练模型
    history = train_model(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        loss_fn=loss_fn,
        optimizer=optimizer,
        scheduler=scheduler,
        num_epochs=100,
        patience=10,
        gradient_clip=1.0
    )

================================================================================
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import time
import os
from copy import deepcopy


class EarlyStopping:
    """
    ==========================================================================
    早停机制 (Early Stopping)
    ==========================================================================

    【功能说明】
        早停是一种防止深度学习模型过拟合的正则化技术。
        通过监控验证集性能，当模型性能连续多次没有改善时，自动停止训练。

    【工作原理】
        1. 训练过程中持续监控验证集损失
        2. 记录历史最佳损失值和对应的模型权重
        3. 如果验证损失连续patience个epoch没有改善，则停止训练
        4. 训练结束后，加载历史最佳权重

    【为什么需要早停】
        - 防止模型在训练集上过度训练（过拟合）
        - 节省训练时间和计算资源
        - 避免模型记忆训练数据的噪声

    【参数说明】
        patience (int): 等待epoch数
            - 默认值：10
            - 含义：验证损失连续10个epoch没有改善才停止训练
            - 设置建议：通常5-20之间，太小容易过早停止，太大可能过拟合

        delta (float): 最小改善量
            - 默认值：0
            - 含义：只有当新损失比最佳损失低至少delta时，才算"改善"
            - 设置建议：通常0即可，要求太严格可能导致无法停止

        path (str): 模型保存路径
            - 默认值：'checkpoint.pt'
            - 含义：最佳模型权重的保存位置

    【使用示例】
        >>> early_stopping = EarlyStopping(patience=10, delta=0, path='best_model.pt')
        >>> for epoch in range(100):
        ...     # 训练和验证代码...
        ...     val_loss = validate(model, val_loader)
        ...     if early_stopping(val_loss, model):
        ...         print("早停触发！")
        ...         break
        ...     model.load_state_dict(torch.load('best_model.pt'))
    """
    def __init__(self, patience=10, delta=0, path='checkpoint.pt'):
        """
        初始化早停机制

        参数:
            patience (int): 等待的epoch数
            delta (float): 最小改善值
            path (str): 模型保存路径
        """
        self.patience = patience  # 早停耐心值
        self.delta = delta  # 最小改善阈值
        self.path = path  # 最佳模型保存路径
        self.counter = 0  # 连续未改善的epoch计数器
        self.best_score = None  # 历史最佳得分（负的损失值）
        self.early_stop = False  # 是否触发早停
        self.val_loss_min = np.Inf  # 历史最低验证损失

    def __call__(self, val_loss, model):
        """
        检查是否需要早停

        参数:
            val_loss (float): 当前epoch的验证损失
            model (nn.Module): 当前模型（用于保存最佳权重）

        返回:
            bool: 是否触发早停（True表示需要停止，False表示继续训练）
        """
        # 将损失转换为得分（损失越低，得分越高）
        score = -val_loss

        # 第一次调用：记录初始值
        if self.best_score is None:
            self.best_score = score  # 记录当前得分为最佳
            self.save_checkpoint(val_loss, model)  # 保存当前模型
        # 得分没有显著改善
        elif score < self.best_score + self.delta:
            self.counter += 1  # 未改善计数器加1
            if self.counter >= self.patience:
                # 连续patience个epoch未改善，触发早停
                self.early_stop = True
        # 得分有显著改善
        else:
            self.best_score = score  # 更新最佳得分
            self.save_checkpoint(val_loss, model)  # 保存当前最佳模型
            self.counter = 0  # 重置未改善计数器

        return self.early_stop

    def save_checkpoint(self, val_loss, model):
        """
        保存当前最佳模型

        参数:
            val_loss (float): 当前验证损失
            model (nn.Module): 当前模型
        """
        # 保存模型权重到文件
        torch.save(model.state_dict(), self.path)
        self.val_loss_min = val_loss  # 更新最低损失记录


class LearningRateScheduler:
    """
    ==========================================================================
    学习率调度器 (Learning Rate Scheduler)
    ==========================================================================

    【功能说明】
        学习率调度器用于在训练过程中自动调整学习率。
        合适的调整策略可以加速收敛，提高模型性能。

    【支持的学习率调度策略】

        1. Cosine Annealing（余弦退火）
           - 学习率按照余弦函数曲线周期性变化
           - 从初始学习率缓慢下降到最小学习率
           - 适合训练后期精细调整

        2. Step Decay（阶梯衰减）
           - 每隔固定epoch数，将学习率降低一定比例
           - 简单有效，适合大多数场景

        3. Reduce on Plateau（验证损失 plateau 时降低）
           - 监控验证集损失
           - 当损失停止下降时，自动降低学习率
           - 本项目使用这种策略

    【参数说明】
        optimizer (optim.Optimizer): 优化器实例
        mode (str): 调度模式
            - 'cosine': 余弦退火
            - 'step': 阶梯衰减
            - 'reduce_on_plateau': 验证损失plateau时降低
        initial_lr (float): 初始学习率
        min_lr (float): 最小学习率（防止过低）
        patience (int): 等待epoch数（仅reduce_on_plateau模式）

    【使用示例】
        >>> optimizer = optim.Adam(model.parameters(), lr=0.001)
        >>> scheduler = LearningRateScheduler(optimizer, mode='reduce_on_plateau')
        >>> for epoch in range(100):
        ...     train_loss = train_epoch(model, train_loader)
        ...     val_loss = validate(model, val_loader)
        ...     scheduler.step(val_loss)  # 更新学习率
        ...     print(f"当前学习率: {scheduler.get_lr()}")
    """
    def __init__(self, optimizer, mode='cosine', initial_lr=0.001, min_lr=1e-6, patience=5):
        """
        初始化学习率调度器

        参数:
            optimizer (optim.Optimizer): 优化器
            mode (str): 调度模式：'cosine', 'step', 'reduce_on_plateau'
            initial_lr (float): 初始学习率
            min_lr (float): 最小学习率
            patience (int): 等待epoch数（用于reduce_on_plateau）
        """
        self.optimizer = optimizer  # 保存优化器引用
        self.mode = mode  # 调度模式
        self.initial_lr = initial_lr  # 初始学习率
        self.min_lr = min_lr  # 最小学习率下限
        self.patience = patience  # Plateau耐心值

        # 根据模式创建对应的调度器
        if mode == 'cosine':
            # 余弦退火：学习率先上升再下降（或持续下降）
            # T_max: 周期长度，eta_min: 最小学习率
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=100, eta_min=min_lr
            )
        elif mode == 'step':
            # 阶梯衰减：每10个epoch学习率减半
            # step_size: 衰减周期，gamma: 衰减比例
            self.scheduler = optim.lr_scheduler.StepLR(
                optimizer, step_size=10, gamma=0.5
            )
        elif mode == 'reduce_on_plateau':
            # 验证损失 Plateau 时降低学习率
            # mode='min': 监控最小值，factor: 衰减比例
            self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode='min', factor=0.5, patience=patience, min_lr=min_lr
            )
        else:
            raise ValueError(f"Unknown scheduler mode: {mode}")

    def step(self, metric=None):
        """
        更新学习率

        参数:
            metric (float, optional): 当前指标值（用于reduce_on_plateau模式）
        """
        if self.mode == 'reduce_on_plateau':
            # reduce_on_plateau需要传入监控指标
            self.scheduler.step(metric)
        else:
            # 其他模式不需要参数
            self.scheduler.step()

    def get_lr(self):
        """
        获取当前学习率

        返回:
            float: 当前学习率
        """
        return self.optimizer.param_groups[0]['lr']


class WeightedMSELoss(nn.Module):
    """
    ==========================================================================
    加权均方误差损失 (Weighted Mean Squared Error Loss)
    ==========================================================================

    【功能说明】
        标准MSE损失对所有样本一视同仁，但实际应用中，
        我们可能希望对某些样本（如高峰时段）给予更多关注。
        加权MSE损失允许我们为不同时段或样本赋予不同权重。

    【适用场景】
        - 负荷预测：高峰时段预测准确性更重要
        - 电力调度：极端天气下的预测更关键
        - 异常检测：近期数据比远期数据更重要

    【数学公式】
        Loss = mean(weight * (prediction - target)^2)

        其中weight是不同时段的权重值

    【参数说明】
        peak_hours (list): 高峰时段的小时列表
            - 默认：[7, 8, 18, 19, 20]（早高峰和晚高峰）
            - 这些时段的预测误差将被放大2倍

        peak_weight (float): 高峰时段的权重倍数
            - 默认值：2.0
            - 含义：高峰时段的误差权重是普通时段的2倍

    【使用示例】
        >>> # 定义高峰时段
        >>> loss_fn = WeightedMSELoss(
        ...     peak_hours=[7, 8, 18, 19, 20],  # 早晚高峰
        ...     peak_weight=2.0  # 权重翻倍
        ... )
        >>>
        >>> # 前向传播
        >>> loss = loss_fn(predictions, targets, hour_indices)
    """
    def __init__(self, peak_hours=None, peak_weight=2.0):
        """
        初始化加权MSE损失

        参数:
            peak_hours (list): 高峰时段的小时列表
            peak_weight (float): 高峰时段的权重倍数
        """
        super(WeightedMSELoss, self).__init__()

        # 设置默认高峰时段（早晚高峰）
        self.peak_hours = peak_hours or [7, 8, 18, 19, 20]
        self.peak_weight = peak_weight  # 高峰时段权重倍数

        # 标准MSE损失（用于非加权情况）
        self.mse_loss = nn.MSELoss()

    def forward(self, pred, target, hour_indices=None):
        """
        计算加权MSE损失

        参数:
            pred (torch.Tensor): 预测值
            target (torch.Tensor): 真实值
            hour_indices (torch.Tensor): 小时索引，用于确定时段

        返回:
            torch.Tensor: 加权损失值
        """
        # 如果没有提供小时索引，使用标准MSE
        if hour_indices is None:
            return self.mse_loss(pred, target)

        # ========== 创建权重矩阵 ==========
        # 初始化为全1的权重矩阵
        weights = torch.ones_like(pred)

        # ========== 为高峰时段分配更高权重 ==========
        for hour in self.peak_hours:
            # 找出属于高峰时段的样本
            mask = (hour_indices == hour)
            # 分配高峰权重
            weights[mask] = self.peak_weight

        # ========== 计算加权MSE ==========
        # 加权平方误差的平均值
        loss = (weights * (pred - target) ** 2).mean()

        return loss


class HuberLoss(nn.Module):
    """
    ==========================================================================
    Huber损失 (Huber Loss)
    ==========================================================================

    【功能说明】
        Huber损失是MSE损失和MAE损失的结合，兼具两者的优点。
        它对异常值（outliers）比MSE更鲁棒，同时比MAE有更好的梯度特性。

    【数学公式】
        对于每个样本：
        L(pred, target) =
            0.5 * (pred - target)^2,  当 |error| <= delta
            delta * |error| - 0.5*delta^2,  当 |error| > delta

        其中delta是阈值超参数

    【损失曲线对比】
        MSE: 抛物线，对大误差惩罚极重（误差平方）
        MAE: V形，对所有误差惩罚相同
        Huber: 在小误差时像MSE，大误差时像MAE

        误差
        ^
        |-------- MSE (抛物线)
        |      /
        |-----/   Huber (组合)
        |   /
        |__/  MAE (V形)
        +-----------------> 误差
           delta

    【优势】
        - 对异常值鲁棒：不像MSE那样被异常值主导
        - 梯度稳定：不像MAE在0点不可导
        - 平滑过渡：在大误差和小误差之间平滑切换

    【参数说明】
        delta (float): 切换阈值
            - 默认值：1.0
            - 小于delta的误差用MSE计算
            - 大于delta的误差用MAE计算

    【使用示例】
        >>> loss_fn = HuberLoss(delta=1.0)
        >>> loss = loss_fn(predictions, targets)
    """
    def __init__(self, delta=1.0):
        """
        初始化Huber损失

        参数:
            delta (float): Huber损失的阈值
        """
        super(HuberLoss, self).__init__()
        self.delta = delta  # 切换阈值

    def forward(self, pred, target):
        """
        计算Huber损失

        参数:
            pred (torch.Tensor): 预测值
            target (torch.Tensor): 真实值

        返回:
            torch.Tensor: Huber损失值
        """
        # 计算误差
        error = pred - target
        abs_error = torch.abs(error)

        # 二次误差部分（|error| <= delta）
        quadratic = torch.min(abs_error, torch.tensor(self.delta))

        # 线性误差部分（|error| > delta）
        linear = abs_error - quadratic

        # Huber损失公式
        loss = 0.5 * quadratic ** 2 + self.delta * linear

        return loss.mean()


class CombinedLoss(nn.Module):
    """
    ==========================================================================
    组合损失 (Combined Loss)
    ==========================================================================

    【功能说明】
        组合损失允许我们将多个损失函数加权组合，
        以兼顾多个优化目标或平衡不同类型误差的影响。

    【典型应用】
        - 多任务学习：同时优化多个输出
        - 平衡不同误差类型：结合MSE和Huber
        - 引入正则化：将主损失与辅助损失组合

    【数学公式】
        Total_Loss = sum(weight_i * Loss_i(pred, target))

    【参数说明】
        loss_functions (list): 损失函数列表
        weights (list): 各损失函数的权重

    【使用示例】
        >>> # 组合MSE和Huber损失
        >>> loss_fn = CombinedLoss(
        ...     loss_functions=[nn.MSELoss(), HuberLoss(delta=1.0)],
        ...     weights=[0.5, 0.5]
        ... )
        >>> loss = loss_fn(pred, target)
    """
    def __init__(self, loss_functions, weights=None):
        """
        初始化组合损失

        参数:
            loss_functions (list): 损失函数列表
            weights (list): 损失函数权重
        """
        super(CombinedLoss, self).__init__()

        # 保存损失函数列表
        self.loss_functions = loss_functions

        # 设置默认权重（均等权重）
        self.weights = weights or [1.0] * len(loss_functions)

    def forward(self, pred, target, **kwargs):
        """
        计算组合损失

        参数:
            pred (torch.Tensor): 预测值
            target (torch.Tensor): 真实值
            **kwargs: 额外参数（如hour_indices）

        返回:
            torch.Tensor: 加权组合后的总损失
        """
        total_loss = 0.0  # 初始化总损失

        # 遍历每个损失函数
        for loss_fn, weight in zip(self.loss_functions, self.weights):
            # 如果提供了hour_indices且损失函数支持，则传递
            if 'hour_indices' in kwargs and hasattr(loss_fn, 'forward'):
                loss = loss_fn(pred, target, kwargs['hour_indices'])
            else:
                loss = loss_fn(pred, target)

            # 加权累加
            total_loss += weight * loss

        return total_loss


def train_model(model, train_loader, val_loader, loss_fn, optimizer, scheduler,
               num_epochs=100, patience=10, gradient_clip=1.0, device='cpu'):
    """
    ==========================================================================
    模型训练函数
    ==========================================================================

    【功能说明】
        提供完整的模型训练流程，包括：
        - 训练阶段：前向传播、损失计算、反向传播、参数更新
        - 验证阶段：评估模型在验证集上的性能
        - 早停机制：防止过拟合
        - 学习率调整：根据验证性能自动调整学习率
        - 梯度裁剪：防止梯度爆炸

    【参数说明】
        model (nn.Module): 待训练的模型
        train_loader (DataLoader): 训练数据加载器
        val_loader (DataLoader): 验证数据加载器
        loss_fn (nn.Module): 损失函数
        optimizer (optim.Optimizer): 优化器
        scheduler (LearningRateScheduler): 学习率调度器
        num_epochs (int): 最大训练轮数
        patience (int): 早停耐心值
        gradient_clip (float): 梯度裁剪阈值（0表示不裁剪）
        device (str): 计算设备

    【返回值的结构】
        dict: 训练历史记录
            - train_loss: 每个epoch的训练损失
            - val_loss: 每个epoch的验证损失
            - train_mae: 每个epoch的训练MAE
            - val_mae: 每个epoch的验证MAE

    【训练流程】
        1. 初始化早停机制
        2. 训练循环（最多num_epochs轮）：
           a. 训练阶段：遍历训练集，计算损失，更新参数
           b. 验证阶段：遍历验证集，评估性能
           c. 学习率调整：根据验证损失更新学习率
           d. 早停检查：如果验证损失连续patience个epoch未改善，停止训练
        3. 加载最佳模型权重
    """
    # ========== 初始化早停机制 ==========
    early_stopping = EarlyStopping(
        patience=patience,
        path=f'{model.__class__.__name__}_best.pt'
    )

    # ========== 初始化训练历史记录 ==========
    history = {
        'train_loss': [],  # 训练损失历史
        'val_loss': [],    # 验证损失历史
        'train_mae': [],   # 训练MAE历史
        'val_mae': []     # 验证MAE历史
    }

    # ========== 训练循环 ==========
    for epoch in range(num_epochs):
        epoch_start_time = time.time()  # 记录epoch开始时间

        # ========== 训练阶段 ==========
        model.train()  # 设置为训练模式
        train_loss = 0.0  # 累积训练损失
        train_mae = 0.0   # 累积训练MAE

        for batch_X, batch_y, batch_hours in train_loader:
            # 将数据移动到计算设备
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            batch_hours = batch_hours.to(device) if batch_hours is not None else None

            # 梯度清零
            optimizer.zero_grad()

            # 前向传播
            outputs = model(batch_X)

            # 计算损失（如果支持hour_indices参数）
            if batch_hours is not None and hasattr(loss_fn, 'forward'):
                loss = loss_fn(outputs, batch_y, hour_indices=batch_hours)
            else:
                loss = loss_fn(outputs, batch_y)

            # 反向传播
            loss.backward()

            # 梯度裁剪（防止梯度爆炸）
            if gradient_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip)

            # 更新参数
            optimizer.step()

            # 累积指标
            train_loss += loss.item()
            train_mae += torch.mean(torch.abs(outputs - batch_y)).item()

        # 计算平均训练指标
        train_loss /= max(len(train_loader), 1)
        train_mae /= max(len(train_loader), 1)

        # ========== 验证阶段 ==========
        model.eval()  # 设置为评估模式
        val_loss = 0.0  # 累积验证损失
        val_mae = 0.0   # 累积验证MAE

        with torch.no_grad():  # 禁用梯度计算
            for batch_X, batch_y, batch_hours in val_loader:
                # 将数据移动到计算设备
                batch_X = batch_X.to(device)
                batch_y = batch_y.to(device)
                batch_hours = batch_hours.to(device) if batch_hours is not None else None

                # 前向传播
                outputs = model(batch_X)

                # 计算损失
                if batch_hours is not None and hasattr(loss_fn, 'forward'):
                    loss = loss_fn(outputs, batch_y, hour_indices=batch_hours)
                else:
                    loss = loss_fn(outputs, batch_y)

                # 累积指标
                val_loss += loss.item()
                val_mae += torch.mean(torch.abs(outputs - batch_y)).item()

        # 计算平均验证指标
        val_loss /= max(len(val_loader), 1)
        val_mae /= max(len(val_loader), 1)

        # ========== 学习率调整 ==========
        scheduler.step(val_loss)

        # ========== 记录训练历史 ==========
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['train_mae'].append(train_mae)
        history['val_mae'].append(val_mae)

        # ========== 打印训练状态 ==========
        epoch_time = time.time() - epoch_start_time
        print(f'Epoch {epoch+1}/{num_epochs}, '
              f'Train Loss: {train_loss:.4f}, Train MAE: {train_mae:.4f}, '
              f'Val Loss: {val_loss:.4f}, Val MAE: {val_mae:.4f}, '
              f'LR: {scheduler.get_lr():.6f}, '
              f'Time: {epoch_time:.2f}s')

        # ========== 早停检查 ==========
        if early_stopping(val_loss, model):
            print(f'早停触发 @ epoch {epoch+1}')
            break

    # ========== 加载最佳模型 ==========
    model.load_state_dict(torch.load(f'{model.__class__.__name__}_best.pt'))

    return history


def evaluate_model(model, test_loader, loss_fn, device='cpu'):
    """
    ==========================================================================
    模型评估函数
    ==========================================================================

    【功能说明】
        在测试集上评估训练好的模型的性能，
        计算损失、MSE、MAE等多个评估指标。

    【参数说明】
        model (nn.Module): 训练好的模型
        test_loader (DataLoader): 测试数据加载器
        loss_fn (nn.Module): 损失函数
        device (str): 计算设备

    【返回值的结构】
        dict: 评估指标
            - loss: 平均测试损失
            - mae: 平均绝对误差
            - rmse: 均方根误差

    【使用示例】
        >>> model = load_model('best_model.pt')
        >>> metrics = evaluate_model(model, test_loader, loss_fn)
        >>> print(f"MAE: {metrics['mae']:.4f}")
    """
    model.eval()  # 设置为评估模式
    test_loss = 0.0  # 累积测试损失
    test_mae = 0.0   # 累积测试MAE
    test_rmse = 0.0  # 累积测试RMSE

    with torch.no_grad():  # 禁用梯度计算
        for batch_X, batch_y, batch_hours in test_loader:
            # 将数据移动到计算设备
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            batch_hours = batch_hours.to(device) if batch_hours is not None else None

            # 前向传播
            outputs = model(batch_X)

            # 计算损失
            if batch_hours is not None and hasattr(loss_fn, 'forward'):
                loss = loss_fn(outputs, batch_y, hour_indices=batch_hours)
            else:
                loss = loss_fn(outputs, batch_y)

            # 累积指标
            test_loss += loss.item()
            test_mae += torch.mean(torch.abs(outputs - batch_y)).item()
            test_rmse += torch.sqrt(torch.mean((outputs - batch_y) ** 2)).item()

    # 计算平均指标
    test_loss /= max(len(test_loader), 1)
    test_mae /= max(len(test_loader), 1)
    test_rmse /= max(len(test_loader), 1)

    # 返回评估指标字典
    metrics = {
        'loss': test_loss,
        'mae': test_mae,
        'rmse': test_rmse
    }

    return metrics


def save_model(model, path):
    """
    ==========================================================================
    模型保存函数
    ==========================================================================

    【功能说明】
        将模型权重和元信息保存到文件。

    【保存内容】
        - model_state_dict: 模型的参数权重
        - model_class: 模型类的名称

    【参数说明】
        model (nn.Module): 待保存的模型
        path (str): 保存路径

    【使用示例】
        >>> save_model(model, 'models/best_model.pt')
        Model saved to models/best_model.pt
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # 保存模型（包含元信息）
    torch.save({
        'model_state_dict': model.state_dict(),  # 模型权重
        'model_class': model.__class__.__name__  # 模型类名
    }, path)

    print(f'Model saved to {path}')


def load_model(model, path):
    """
    ==========================================================================
    模型加载函数
    ==========================================================================

    【功能说明】
        从文件加载模型权重到模型实例中。

    【参数说明】
        model (nn.Module): 模型实例（结构必须与保存时一致）
        path (str): 模型文件路径

    【返回值的类型】
        nn.Module: 加载权重后的模型实例

    【使用示例】
        >>> model = ImprovedTFT(input_size=6, output_size=3)
        >>> model = load_model(model, 'models/best_model.pt')
        Model loaded from models/best_model.pt
    """
    # 加载模型文件
    checkpoint = torch.load(path)
    # 将权重加载到模型
    model.load_state_dict(checkpoint['model_state_dict'])

    print(f'Model loaded from {path}')
    return model


def get_optimizer(model, optimizer_type='adam', lr=0.001, weight_decay=1e-5):
    """
    ==========================================================================
    优化器工厂函数
    ==========================================================================

    【功能说明】
        根据配置创建优化器实例。

    【支持的优化器】
        - Adam: 自适应学习率优化器，适合大多数场景
        - AdamW: Adam的改进版，权重衰减更规范
        - SGD: 随机梯度下降，带动量选项

    【参数说明】
        model (nn.Module): 待优化的模型
        optimizer_type (str): 优化器类型：'adam', 'adamw', 'sgd'
        lr (float): 学习率
        weight_decay (float): 权重衰减（L2正则化）

    【返回值的类型】
        optim.Optimizer: 优化器实例

    【使用示例】
        >>> optimizer = get_optimizer(
        ...     model=model,
        ...     optimizer_type='adam',
        ...     lr=0.001,
        ...     weight_decay=1e-5
        ... )
    """
    if optimizer_type == 'adam':
        return optim.Adam(
            model.parameters(),
            lr=lr,
            weight_decay=weight_decay
        )
    elif optimizer_type == 'adamw':
        return optim.AdamW(
            model.parameters(),
            lr=lr,
            weight_decay=weight_decay
        )
    elif optimizer_type == 'sgd':
        return optim.SGD(
            model.parameters(),
            lr=lr,
            momentum=0.9,
            weight_decay=weight_decay
        )
    else:
        raise ValueError(f"Unknown optimizer type: {optimizer_type}")


def get_loss_function(loss_type='mse', **kwargs):
    """
    ==========================================================================
    损失函数工厂函数
    ==========================================================================

    【功能说明】
        根据配置创建损失函数实例。

    【支持的损失函数】
        - 'mse': 标准均方误差损失
        - 'mae': 平均绝对误差损失
        - 'huber': Huber损失，对异常值更鲁棒
        - 'weighted_mse': 加权MSE损失
        - 'combined': 组合损失

    【参数说明】
        loss_type (str): 损失函数类型
        **kwargs: 额外参数，传递给损失函数

    【返回值的类型】
        nn.Module: 损失函数实例

    【使用示例】
        >>> # 标准MSE
        >>> loss_fn = get_loss_function('mse')

        >>> # 加权MSE（高峰时段）
        >>> loss_fn = get_loss_function(
        ...     'weighted_mse',
        ...     peak_hours=[7, 8, 18, 19, 20],
        ...     peak_weight=2.0
        ... )

        >>> # Huber损失
        >>> loss_fn = get_loss_function('huber', delta=1.0)
    """
    if loss_type == 'mse':
        return nn.MSELoss()
    elif loss_type == 'mae':
        return nn.L1Loss()
    elif loss_type == 'huber':
        return HuberLoss(**kwargs)
    elif loss_type == 'weighted_mse':
        return WeightedMSELoss(**kwargs)
    elif loss_type == 'combined':
        # 默认组合：MSE + Huber
        loss_functions = [nn.MSELoss(), HuberLoss()]
        weights = kwargs.get('weights', [0.5, 0.5])
        return CombinedLoss(loss_functions, weights)
    else:
        raise ValueError(f"Unknown loss type: {loss_type}")
