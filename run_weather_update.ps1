# ===========================================================
# 静岡気象データ自動更新 ラッパースクリプト
# Google Drive (G:) がマウントされた後に Python を実行し、
# 更新されたデータを GitHub へ Push します
# ===========================================================

$PythonExe  = "C:\Users\mtfro\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$ScriptPath = "G:\マイドライブ\AIエージェント\静岡気象データ\shizuoka_weather.py"
$ReportPath = "G:\マイドライブ\AIエージェント\静岡気象データ\generate_report.py"
$WorkDir    = "G:\マイドライブ\AIエージェント\静岡気象データ"
$LogFile    = "C:\Users\mtfro\shizuoka_weather_task.log"

function Write-Log {
    param($Message)
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "--- 自動更新タスク開始 ---"

# G:ドライブが利用可能になるまで最大60秒待機
$maxWait = 60
$waited  = 0
while (-not (Test-Path "G:\")) {
    Write-Log "G:ドライブ待機中... ($waited 秒経過)"
    Start-Sleep -Seconds 5
    $waited += 5
    if ($waited -ge $maxWait) {
        Write-Log "エラー: G:ドライブが $maxWait 秒待っても見つかりません。終了します。"
        exit 1
    }
}

Write-Log "G:ドライブ確認OK"

# 作業ディレクトリ確認
if (-not (Test-Path $WorkDir)) {
    Write-Log "エラー: 作業ディレクトリが見つかりません: $WorkDir"
    exit 1
}

Set-Location $WorkDir

# ─── STEP 1: データ取得 ──────────────────────────────────────
Write-Log "Pythonスクリプト実行開始: $ScriptPath"

$proc = Start-Process -FilePath $PythonExe -ArgumentList "`"$ScriptPath`"" -WorkingDirectory $WorkDir -Wait -PassThru -NoNewWindow
$exitCode = $proc.ExitCode

if ($exitCode -eq 0) {
    Write-Log "データ取得スクリプト正常完了 (終了コード: $exitCode)"
} else {
    Write-Log "データ取得スクリプトエラー (終了コード: $exitCode)"
    exit $exitCode
}

# ─── STEP 2: HTML レポート生成 ───────────────────────────────
if (Test-Path $ReportPath) {
    Write-Log "HTMLレポート生成開始: $ReportPath"
    $rProc = Start-Process -FilePath $PythonExe -ArgumentList "`"$ReportPath`"" -WorkingDirectory $WorkDir -Wait -PassThru -NoNewWindow
    if ($rProc.ExitCode -eq 0) {
        Write-Log "HTMLレポート生成完了"
    } else {
        Write-Log "警告: HTMLレポート生成でエラー (終了コード: $($rProc.ExitCode)) - 続行します"
    }
}

# ─── STEP 3: Git コミット & プッシュ ─────────────────────────
Write-Log "Git コミット & プッシュ開始"

# git が利用可能か確認
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Log "警告: git コマンドが見つかりません。Git Push をスキップします。"
} else {
    # 変更をステージング
    git -C $WorkDir add shizuoka_weather.csv `
                        shizuoka_weather_plot.png `
                        shizuoka_normal_plot.png `
                        shizuoka_weather_report.html 2>&1 | ForEach-Object { Write-Log "git add: $_" }

    # 変更があるか確認
    $diffOutput = git -C $WorkDir diff --cached --name-only 2>&1
    if ($diffOutput) {
        $today = (Get-Date).ToString("yyyy-MM-dd")
        $commitMsg = "🌤 自動更新: $today"
        git -C $WorkDir commit -m $commitMsg 2>&1 | ForEach-Object { Write-Log "git commit: $_" }
        git -C $WorkDir push 2>&1 | ForEach-Object { Write-Log "git push: $_" }
        Write-Log "✅ Git Push 完了: $commitMsg"
    } else {
        Write-Log "変更なし - Git コミットをスキップします"
    }
}

Write-Log "--- 自動更新タスク終了 ---"
exit 0

