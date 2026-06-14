@echo off
REM ── 阶段 5 测试运行脚本（Windows）──
REM 双击此文件即可运行全部测试

echo ═══════════════════════════════════════════
echo  阶段 5 测试 Demo — 运行全部测试
echo ═══════════════════════════════════════════
echo.

REM 安装测试依赖（如未安装则取消注释）
REM pip install httpx pytest pytest-cov

echo [1/3] 运行全部测试...
pytest tests/ -v
echo.

echo [2/3] 生成覆盖率报告...
pytest tests/ --cov=. --cov-report=term-missing
echo.

echo [3/3] 完成！
pause
