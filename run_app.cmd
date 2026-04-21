@echo off
cls
title ADB Admin - Launcher

REM --- Check for Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not found in your system's PATH.
    echo Please install Python 3.8+ and ensure it's added to your PATH during installation.
    echo You can download it from: https://www.python.org/downloads/
    pause
    exit /b
)

:menu
cls
echo ==================================================
echo              ADB Admin - Launcher
echo ==================================================
echo.
echo Please select an option:
echo.
echo   1. Install/Update Required Libraries
echo   2. Run ADB Admin Web App
echo   3. Exit
echo.

set /p choice="Enter your choice (1, 2, or 3): "

if "%choice%"=="1" goto setup
if "%choice%"=="2" goto run
if "%choice%"=="3" goto exit

echo Invalid choice. Please try again.
pause
goto menu

:setup
echo.
echo --- Installing required libraries from requirements.txt ---
echo This may take a few minutes...
echo.
python -m pip install -r requirements.txt
echo.
echo --- Installation complete! ---
pause
goto menu

:run
echo.
echo --- Launching ADB Admin Web App ---
echo Your web browser should open shortly.
echo Close this window to stop the server.
echo.
python -m streamlit run ADB_ADMIN.py
goto menu

:exit
exit /b
