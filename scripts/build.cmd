@echo off
REM 构建 VideoSlim 应用程序

setlocal

REM 切换到脚本所在目录（确保相对路径正确）
pushd "%~dp0.."
set "PROJECT_ROOT=%CD%"

REM 定位项目本地 venv：优先 .venv，回退 venv
set "VENV_PY=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" set "VENV_PY=%PROJECT_ROOT%\venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo 未找到 .venv 或 venv，请先创建虚拟环境并安装依赖：
    echo     python -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -e .[dev]
    popd
    exit /b 1
)

REM 设置构建目录（产物统一放在 scripts/output/，避免污染项目根）
set "BUILD_DIR=%~dp0output"
set "DIST_DIR=%BUILD_DIR%\dist"
set "BUILD_TMP_DIR=%BUILD_DIR%\build"

REM 创建构建目录（如果不存在）
mkdir %BUILD_DIR% 2>nul

REM 使用 venv 中的 PyInstaller 构建单文件应用
REM 路径全部用绝对路径：相对路径会以 --specpath 为基准解析，
REM 而 --specpath 设到 scripts/output/，会把 ./tools/... 解析错。
"%VENV_PY%" -m PyInstaller --onefile ^
    --name "VideoSlim" ^
    --noconsole ^
    --icon "%PROJECT_ROOT%\tools\icon.ico" ^
    --add-data "%PROJECT_ROOT%\tools\ffmpeg.exe;tools" ^
    --add-data "%PROJECT_ROOT%\tools\icon.ico;tools" ^
    --specpath "%BUILD_DIR%" ^
    --distpath %DIST_DIR% ^
    --workpath %BUILD_TMP_DIR% ^
    "%PROJECT_ROOT%\main.py"

REM 检查构建是否成功
if %ERRORLEVEL% NEQ 0 (
    echo 构建失败！
    popd
    exit /b 1
)

echo build success! executable file is located at: %DIST_DIR%\VideoSlim.exe

REM 复制配置文件和其他必要文件到输出目录
copy /Y "%PROJECT_ROOT%\config.json" %DIST_DIR%\ 2>nul

REM 清理临时文件（可选）
REM rmdir /S /Q %BUILD_TMP_DIR%

popd
endlocal
pause
