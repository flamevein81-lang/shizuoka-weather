@echo off
chcp 65001 > nul
title 静岡気象データ更新

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   🌤  静岡気象データ更新ツール            ║
echo  ║   気象庁データ取得 + グラフ自動生成       ║
echo  ╚══════════════════════════════════════════╝
echo.

set WORKDIR=G:\マイドライブ\AIエージェント\静岡気象データ
set PYTHON=C:\Users\mtfro\AppData\Local\Python\pythoncore-3.14-64\python.exe
set SCRIPT=%WORKDIR%\shizuoka_weather.py
set REPORT_SCRIPT=%WORKDIR%\generate_report.py
set REPORT_HTML=%WORKDIR%\shizuoka_weather_report.html
set MAIN_PLOT=%WORKDIR%\shizuoka_normal_plot.png
set COMP_PLOT=%WORKDIR%\shizuoka_weather_plot.png
set LOG=%WORKDIR%\weather_update.log

:: ─── 各種確認 ───────────────────────────────
if not exist "G:\" (
    echo  ❌ Gドライブ (Google Drive) がマウントされていません
    echo     Google Drive を起動してから再実行してください
    echo.
    goto :WAIT
)

if not exist "%PYTHON%" (
    echo  ❌ Pythonが見つかりません:
    echo     %PYTHON%
    echo.
    goto :WAIT
)

if not exist "%SCRIPT%" (
    echo  ❌ スクリプトが見つかりません:
    echo     %SCRIPT%
    echo.
    goto :WAIT
)

:: ─── データ取得・処理 ────────────────────────
echo  ┌──────────────────────────────────────────┐
echo  │  STEP 1/3  📡 気象庁からデータ取得中...  │
echo  └──────────────────────────────────────────┘
echo.

cd /d "%WORKDIR%"
"%PYTHON%" "%SCRIPT%"
set RESULT=%errorlevel%

echo.

:: ─── 結果判定 ────────────────────────────────
if %RESULT% equ 0 (
    echo  ╔══════════════════════════════════════════╗
    echo  ║  ✅ 更新が正常に完了しました！           ║
    echo  ╠══════════════════════════════════════════╣
    echo  ║  📊 グラフを自動表示します...            ║
    echo  ╚══════════════════════════════════════════╝
    echo.

    :: STEP 2: HTMLレポートを生成
    echo  ┌──────────────────────────────────────────┐
    echo  │  STEP 2/3  📄 HTMLレポートを生成中...    │
    echo  └──────────────────────────────────────────┘
    echo.

    if exist "%REPORT_SCRIPT%" (
        "%PYTHON%" "%REPORT_SCRIPT%"
        if %errorlevel% equ 0 (
            echo  ✅ レポート生成完了: shizuoka_weather_report.html
        ) else (
            echo  ⚠ レポート生成でエラーが発生しましたが続行します
        )
    ) else (
        echo  ⚠ generate_report.py が見つかりません。スキップします。
    )
    echo.

    :: STEP 3 (旧2): 更新後のグラフを表示
    echo  ┌──────────────────────────────────────────┐
    echo  │  STEP 3/3  🖼  グラフを開いています...   │
    echo  └──────────────────────────────────────────┘
    echo.

    if exist "%MAIN_PLOT%" (
        start "" "%MAIN_PLOT%"
        timeout /t 1 /nobreak > nul
    )
    if exist "%COMP_PLOT%" (
        start "" "%COMP_PLOT%"
        timeout /t 1 /nobreak > nul
    )

    :: STEP 3: ログの末尾を表示
    echo  ┌──────────────────────────────────────────┐
    echo  │  STEP 3/3  📋 最新ログ (末尾10行)        │
    echo  └──────────────────────────────────────────┘
    echo.
    if exist "%LOG%" (
        powershell -NoProfile -Command "Get-Content '%LOG%' -Tail 10 | ForEach-Object { Write-Host '    ' $_ }"
    )
    echo.
    echo  ───────────────────────────────────────────
    echo  ✔ グラフが別ウィンドウで開かれました
    echo    更新日時: %date% %time%
    echo  ───────────────────────────────────────────
) else (
    echo  ╔══════════════════════════════════════════╗
    echo  ║  ❌ エラーが発生しました (code:%RESULT%) ║
    echo  ╚══════════════════════════════════════════╝
    echo.
    echo  📋 ログファイルを自動で開きます...
    echo.
    if exist "%LOG%" (
        powershell -NoProfile -Command "Get-Content '%LOG%' -Tail 20 | ForEach-Object { Write-Host '    ' $_ }"
        echo.
        start "" notepad "%LOG%"
    )
)

:WAIT
echo.
echo  ▶ 何かキーを押すと閉じます...
pause > nul
