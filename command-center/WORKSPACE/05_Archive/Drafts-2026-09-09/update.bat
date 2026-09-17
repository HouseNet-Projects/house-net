@echo off
chcp 65001 >nul
title Daily check - update
python "%~dp0run.py"
if errorlevel 1 pause
if not errorlevel 1 timeout /t 3 >nul
