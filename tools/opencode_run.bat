@ Echo Off
REM OpenCode 运行脚本 (Windows)
REM 需要先完成 opencode_init.bat，并在项目中有虚拟环境
echo 启动 OpenCode 后端...

IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo 未检测到虚拟环境，请先运行 opencode_init.bat 初始化环境。
    pause
    exit /B 1
)

CALL ".\.venv\Scripts\activate.bat"
set "FLASK_APP=backend.app"
set "FLASK_ENV=development"
python backend/start.py
