@echo off
REM OpenCode 初始化脚本 (Windows)
REM - 创建/激活虚拟环境
REM - 安装后端依赖
REM - 初始化数据库
echo OpenCode 初始化开始...

IF EXIST ".venv\Scripts\activate.bat" (
    echo 使用已存在的虚拟环境
    CALL ".\.venv\Scripts\activate.bat"
) ELSE (
    echo 创建虚拟环境...
    python -m venv .venv
    CALL ".\.venv\Scripts\activate.bat"
)

echo 安装后端依赖...
pip install -r backend\requirements.txt

echo 初始化数据库...
python backend\init_db.py

echo OpenCode 初始化完成。
pause
