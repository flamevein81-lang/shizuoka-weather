# ===========================================================
# 静岡気象データ自動更新タスク登録スクリプト
# 毎月 1・6・11・16・21・26日 07:00 に実行
# ===========================================================

$TaskName   = "ShizuokaWeatherUpdate"
$WrapperPs1 = "C:\Users\mtfro\run_weather_update.ps1"
$UserName   = "$env:USERDOMAIN\$env:USERNAME"

Write-Host "登録ユーザー: $UserName"

# 既存タスクの削除
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "既存タスクを削除しました"
}

# ─── XMLで直接タスク定義 ──────────────────────────────────────
# 毎月 1・6・11・16・21・26日 07:00 に実行 (6つのCalendarTrigger)
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>静岡気象データ自動更新 (毎月1/6/11/16/21/26日 07:00)</Description>
  </RegistrationInfo>
  <Triggers>
    <!-- 毎月 1日 -->
    <CalendarTrigger>
      <StartBoundary>2026-07-01T07:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth><Day>1</Day></DaysOfMonth>
        <Months>
          <January/><February/><March/><April/><May/><June/>
          <July/><August/><September/><October/><November/><December/>
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
    <!-- 毎月 6日 -->
    <CalendarTrigger>
      <StartBoundary>2026-07-06T07:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth><Day>6</Day></DaysOfMonth>
        <Months>
          <January/><February/><March/><April/><May/><June/>
          <July/><August/><September/><October/><November/><December/>
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
    <!-- 毎月 11日 -->
    <CalendarTrigger>
      <StartBoundary>2026-07-11T07:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth><Day>11</Day></DaysOfMonth>
        <Months>
          <January/><February/><March/><April/><May/><June/>
          <July/><August/><September/><October/><November/><December/>
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
    <!-- 毎月 16日 -->
    <CalendarTrigger>
      <StartBoundary>2026-07-16T07:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth><Day>16</Day></DaysOfMonth>
        <Months>
          <January/><February/><March/><April/><May/><June/>
          <July/><August/><September/><October/><November/><December/>
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
    <!-- 毎月 21日 -->
    <CalendarTrigger>
      <StartBoundary>2026-07-21T07:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth><Day>21</Day></DaysOfMonth>
        <Months>
          <January/><February/><March/><April/><May/><June/>
          <July/><August/><September/><October/><November/><December/>
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
    <!-- 毎月 26日 -->
    <CalendarTrigger>
      <StartBoundary>2026-07-26T07:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth><Day>26</Day></DaysOfMonth>
        <Months>
          <January/><February/><March/><April/><May/><June/>
          <July/><August/><September/><October/><November/><December/>
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$UserName</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions>
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File "C:\Users\mtfro\run_weather_update.ps1"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

# XMLをUTF-16で一時ファイルに保存
$tmpXml = "$env:TEMP\shizuoka_task.xml"
[System.IO.File]::WriteAllText($tmpXml, $xml, [System.Text.Encoding]::Unicode)

# schtasks コマンドで登録 (XML経由)
$result = schtasks /Create /TN $TaskName /XML $tmpXml /F 2>&1
Write-Host "schtasks 結果: $result"

# 一時ファイル削除
Remove-Item $tmpXml -ErrorAction SilentlyContinue

# 確認
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host ""
    Write-Host "✅ タスク登録完了!" -ForegroundColor Green
    Write-Host "   タスク名     : $TaskName"
    Write-Host "   実行ユーザー : $UserName"
    Write-Host "   実行日       : 毎月 1・6・11・16・21・26日"
    Write-Host "   実行時刻     : 07:00"
    Write-Host "   ラッパー     : $WrapperPs1"
    Write-Host "   タスクログ   : C:\Users\mtfro\shizuoka_weather_task.log"
    Write-Host ""
    Write-Host "手動テスト実行:"
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
} else {
    Write-Host "❌ 登録失敗" -ForegroundColor Red
}
