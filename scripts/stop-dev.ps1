$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ScriptDir ".dev-pids.json"
$ManagedPorts = @(8000, 5173)
$ExpectedServices = @{
    backend = 8000
    frontend = 5173
}

function Get-RecordProperty {
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $property = $Record.PSObject.Properties[$Name]
    if ($null -eq $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
        throw "PID record is missing required field '$Name'."
    }
    return $property.Value
}

function ConvertTo-ValidatedPidRecords {
    param([Parameter(Mandatory = $true)][object[]]$Records)

    if ($Records.Count -eq 0) {
        throw "PID record file does not contain any service records."
    }

    $seenServices = @{}
    $validated = @()
    foreach ($record in $Records) {
        $name = ([string](Get-RecordProperty -Record $record -Name "name")).Trim().ToLowerInvariant()
        if (-not $ExpectedServices.ContainsKey($name)) {
            throw "PID record contains unsupported service name '$name'."
        }
        if ($seenServices.ContainsKey($name)) {
            throw "PID record contains duplicate service '$name'."
        }

        $pidValue = 0
        $rawPid = Get-RecordProperty -Record $record -Name "rootPid"
        if (-not [int]::TryParse([string]$rawPid, [ref]$pidValue) -or $pidValue -le 0) {
            throw "PID record for '$name' has an invalid rootPid."
        }

        $startTime = [datetime]::MinValue
        $rawStartTime = Get-RecordProperty -Record $record -Name "rootProcessStartTime"
        if (-not [datetime]::TryParse([string]$rawStartTime, [ref]$startTime)) {
            throw "PID record for '$name' has an invalid rootProcessStartTime."
        }

        $seenServices[$name] = $true
        $validated += [pscustomobject]@{
            name = $name
            rootPid = $pidValue
            rootProcessStartTime = $startTime
            port = $ExpectedServices[$name]
        }
    }

    return @($validated)
}

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

    try {
        return [math]::Abs(($Process.StartTime - $Record.rootProcessStartTime).TotalSeconds) -lt 2
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
    $rawRecords = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
    $records = @(ConvertTo-ValidatedPidRecords -Records @($rawRecords))
}
catch {
    Write-Host "Could not validate scripts\.dev-pids.json. The invalid PID file was preserved for diagnosis."
    Write-Host ("  {0}" -f $_.Exception.Message)
    Write-PortStatus -Ports $ManagedPorts
    exit 1
}

$allStopped = $true

foreach ($record in @($records)) {
    $pidValue = $record.rootPid
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
        $taskkillOutput = & taskkill.exe /PID $pidValue /T /F 2>&1 | Out-String
        $taskkillExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($taskkillExitCode -ne 0 -and $null -ne (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
        $detail = $taskkillOutput.Trim()
        if (-not $detail) {
            $detail = "taskkill returned no diagnostic output"
        }
        Write-Host ("  WARNING: taskkill exited with code {0}: {1}" -f $taskkillExitCode, $detail)
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
    $remainingProcess = Get-Process -Id $record.rootPid -ErrorAction SilentlyContinue
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
    exit 0
}
else {
    Write-Host "Some services could not be stopped. PID file preserved at $PidFile"
    exit 1
}
