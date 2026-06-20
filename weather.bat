@echo off
chcp 65001 > nul
set WORKDIR=g:\マイドライブ\AIエージェント\静岡気象データ
set PYTHON="C:\Users\mtfro\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set SCRIPT=shizuoka_weather.py

echo =========================================
echo  🌤  静岡気象データを更新しています...
echo =========================================
echo.

cd /d "%WORKDIR%"

%PYTHON% "%SCRIPT%"

echo.
if %errorlevel% equ 0 (
    echo =========================================
    echo  ✅ 更新が正常に完了しました！
    echo  ・グラフ : shizuoka_normal_plot.png
    echo  ・CSV    : shizuoka_weather.csv
    echo =========================================
) else (
    echo =========================================
    echo  ❌ 実行中にエラーが発生しました (code: %errorlevel%)
    echo =========================================
)

echo.
pause
