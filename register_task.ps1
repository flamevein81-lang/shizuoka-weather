$TaskName   = "ShizuokaWeatherUpdate"
$WrapperPs1 = "C:\Users\mtfro\run_weather_update.ps1"
$UserName   = "$env:USERDOMAIN\$env:USERNAME"

Write-Host "User: $UserName"

# 既存タスク削除（管理者権限で試みる）
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Host "Deleted existing task"
    } catch {
        Write-Host "Could not delete existing task (may need admin). Continuing..."
    }
}

# XML テンプレート（毎月指定日トリガー）
$xmlContent = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Shizuoka Weather Auto Update</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-07-01T07:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth>
          <Day>1</Day>
          <Day>6</Day>
          <Day>11</Day>
          <Day>16</Day>
          <Day>21</Day>
          <Day>26</Day>
        </DaysOfMonth>
        <Months>
          <January /><February /><March /><April /><May /><June />
          <July /><August /><September /><October /><November /><December />
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>DESKTOP-6H5QHRI\mtfro</UserId>
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

# UTF-16 で一時XMLファイルに保存
$tmpXml = "$env:TEMP\shizuoka_task_reg.xml"
[System.IO.File]::WriteAllText($tmpXml, $xmlContent, [System.Text.Encoding]::Unicode)

# schtasks で登録
$result = schtasks /Create /TN $TaskName /XML $tmpXml /F 2>&1
Write-Host "schtasks: $result"

Remove-Item $tmpXml -ErrorAction SilentlyContinue

# 確認
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host ""
    Write-Host "SUCCESS: Task registered!" -ForegroundColor Green
    Write-Host "  Name : $TaskName"
    Write-Host "  Days : 1, 6, 11, 16, 21, 26 of each month at 07:00"
    Write-Host "  Script : $WrapperPs1"
    Write-Host ""
    Write-Host "Manual test: Start-ScheduledTask -TaskName '$TaskName'"
} else {
    Write-Host "FAILED: Task not registered" -ForegroundColor Red
}
