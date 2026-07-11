$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ScriptDir ".dev-pids.json"
$ManagedPorts = @(8000, 5173)

function Test-PortInUse {
    param([Parameter(Mandatory = $true)][int]$Port)

    try {
        return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    }
    catch {
        return $false
    }
}

function Write-PortStatus {
    param([Parameter(Mandatory = $true)][int[]]$Ports)

    foreach ($port in $Ports) {
        if (Test-PortInUse -Port $port) {
            Write-Host ("Port {0}: still listening." -f $port)
        }
        else {
            Write-Host ("Port {0}: released." -f $port)
        }
    }
}

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
    Write-Host "This only means the startup script has no PID record; current port status follows."
    Write-PortStatus -Ports $ManagedPorts
    exit 0
}

try {
    $records = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
}
catch {
    Write-Host "Could not read scripts\.dev-pids.json. The invalid PID file was preserved for diagnosis."
    Write-PortStatus -Ports $ManagedPorts
    exit 1
}

$allStopped = $true

foreach ($record in @($records)) {
    if ($null -eq $record.rootPid) {
        Write-Host ("{0}: PID is missing from the record. Skipping it." -f $record.name)
        $allStopped = $false
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
        $allStopped = $false
        continue
    }

    Write-Host ("Stopping {0}: PID {1}" -f $record.name, $pidValue)
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & taskkill.exe /PID $pidValue /T /F 2>&1 | Out-Null
        $taskkillExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($taskkillExitCode -ne 0) {
        Write-Host ("  WARNING: taskkill exited with code {0}, {1} may still be running" -f $taskkillExitCode, $record.name)
        $allStopped = $false
    }
}

$releaseTimeout = (Get-Date).AddSeconds(5)
while ((Get-Date) -lt $releaseTimeout) {
    $listeningPorts = @($ManagedPorts | Where-Object { Test-PortInUse -Port $_ })
    if ($listeningPorts.Count -eq 0) {
        break
    }
    Start-Sleep -Milliseconds 250
}

foreach ($record in @($records)) {
    if ($null -eq $record.rootPid) {
        continue
    }

    $remainingProcess = Get-Process -Id ([int]$record.rootPid) -ErrorAction SilentlyContinue
    if ($null -ne $remainingProcess -and (Test-RecordedProcessMatches -Record $record -Process $remainingProcess)) {
        Write-Host ("{0}: recorded PID {1} is still running." -f $record.name, $record.rootPid)
        $allStopped = $false
    }
}

Write-PortStatus -Ports $ManagedPorts
if (@($ManagedPorts | Where-Object { Test-PortInUse -Port $_ }).Count -gt 0) {
    $allStopped = $false
}

if ($allStopped) {
    Remove-Item -LiteralPath $PidFile -Force
    Write-Host "Finished stopping recorded LexAd dev services."
}
else {
    Write-Host "Some services could not be stopped. PID file preserved at $PidFile"
}
