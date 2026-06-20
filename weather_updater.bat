@echo off
chcp 65001 > nul
set WORKDIR=g:\マイドライブ\AIエージェント\静岡気象データ
set PYTHON="C:\Users\mtfro\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set SCRIPT=shizuoka_weather.py

cd /d "%WORKDIR%"
echo [%date% %time%] 静岡気象データ更新開始 >> "%WORKDIR%\weather_updater_bat.log"

%PYTHON% "%WORKDIR%\%SCRIPT%"

if %errorlevel% neq 0 (
    echo [%date% %time%] エラー発生 (code: %errorlevel%) >> "%WORKDIR%\weather_updater_bat.log"
) else (
    echo [%date% %time%] 更新完了 >> "%WORKDIR%\weather_updater_bat.log"
)
exit /b %errorlevel%
