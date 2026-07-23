@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 代理节点后台监控服务
echo ======================================
echo   代理节点后台监控服务
echo   目标: 详见 config.yaml
echo   日志: monitor.log
echo   关闭此窗口可停止监控
echo ======================================
python daemon.py
pause
