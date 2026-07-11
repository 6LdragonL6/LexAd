$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ScriptDir ".dev-pids.json"

function Test-RecordedProcessMatches {
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)]$Process
    )

    if ($null -eq $Record.rootProcessStartTime) {
        return $true
    }

    try {
        $recordedStart = [datetime]$Record.rootProcessStartTime
        return [math]::Abs(($Process.StartTime - $recordedStart).TotalSeconds) -lt 2
    }
    catch {
        return $false
    }
}

if (-not (Test-Path -LiteralPath $PidFile -PathType Leaf)) {
    Write-Host "No recorded LexAd dev services were found."
    exit 0
}

try {
    $records = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
}
catch {
    Write-Host "Could not read scripts\.dev-pids.json. Removing the invalid PID file."
    Remove-Item -LiteralPath $PidFile -Force
    exit 0
}

$allStopped = $true

foreach ($record in @($records)) {
    if ($null -eq $record.rootPid) {
        continue
    }

    $pidValue = [int]$record.rootPid
    $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Write-Host ("{0}: PID {1} is not running." -f $record.name, $pidValue)
        continue
    }

    if (-not (Test-RecordedProcessMatches -Record $record -Process $process)) {
        Write-Host ("{0}: PID {1} start time does not match the recorded service. Skipping it." -f $record.name, $pidValue)
        continue
    }

    Write-Host ("Stopping {0}: PID {1}" -f $record.name, $pidValue)
    & taskkill.exe /PID $pidValue /T /F 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ("  WARNING: taskkill exited with code {0}, {1} may still be running" -f $LASTEXITCODE, $record.name)
        $allStopped = $false
    }
}

if ($allStopped) {
    Remove-Item -LiteralPath $PidFile -Force
    Write-Host "Finished stopping recorded LexAd dev services."
}
else {
    Write-Host "Some services could not be stopped. PID file preserved at $PidFile"
}
