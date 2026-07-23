@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 代理节点监控面板
echo ==========================================
echo   代理节点监控面板 启动中...
echo   目标: 详见 config.yaml
echo   浏览器访问: http://localhost:8501
echo   关闭此窗口即可停止面板
echo   (后台监控需单独启动"启动后台监控.bat")
echo ==========================================
start http://localhost:8501
streamlit run main.py --server.headless true
pause
