#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键训练全部 5 个预测模型的入口脚本。

用法（在项目根目录执行）：
    python backend/train_all.py

或进入 backend 目录后执行：
    python train_all.py

训练流程：
  1. 从数据库加载 2023 年全年数据（8737 条）
  2. 按 70/15/15 时间顺序切分为 train/val/test 三段
  3. 基于 train 段重新拟合并保存 scaler.pkl（覆盖旧文件）
  4. 依次训练 5 个模型，共享同一个 scaler
  5. 每个模型训练完成后在 test 段（2023-11-07~12-31）评估并打印指标
  6. 最后打印 5 个模型的汇总对比表

训练完成后，调用以下接口令运行中的服务加载新权重（无需重启）：
  POST http://localhost:5000/api/predict/reload_models
"""

import sys
import os
import io

# Windows 控制台中文输出支持
if sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except AttributeError:
        pass  # 已经是 TextIOWrapper 则跳过

# 将 backend 目录加入 sys.path，使 train_all.py 既可从根目录也可从 backend 目录运行
_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

from app import create_app
from models.train import train_all_models

if __name__ == '__main__':
    app = create_app()
    train_all_models(app)
