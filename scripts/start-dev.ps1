$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$PidFile = Join-Path $ScriptDir ".dev-pids.json"

function Quote-PowerShellString {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

function Test-ProcessIsRunning {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    return $null -ne (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
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

function Assert-Directory {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "$Name directory not found: $Path"
    }
}

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$CommandName)

    $command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        throw "Command not found: $CommandName"
    }

    return $command.Source
}

function Get-PythonCommand {
    $venvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
        return $venvPython
    }

    return (Assert-Command "python")
}

function Assert-NoRecordedInstance {
    if (-not (Test-Path -LiteralPath $PidFile -PathType Leaf)) {
        return
    }

    try {
        $records = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
    }
    catch {
        Remove-Item -LiteralPath $PidFile -Force
        return
    }

    $running = @()
    foreach ($record in @($records)) {
        if ($null -ne $record.rootPid -and (Test-ProcessIsRunning -ProcessId ([int]$record.rootPid))) {
            $running += $record
        }
    }

    if ($running.Count -gt 0) {
        Write-Host "LexAd dev services already look like they are running:"
        foreach ($record in $running) {
            Write-Host ("  {0}: PID {1}" -f $record.name, $record.rootPid)
        }
        throw "Run stop-dev.bat first, or close the recorded windows and delete scripts\.dev-pids.json if the record is stale."
    }

    Remove-Item -LiteralPath $PidFile -Force
}

function Start-ServiceWindow {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Command
    )

    $title = "LexAd $Name"
    $quotedTitle = Quote-PowerShellString $title
    $quotedWorkingDirectory = Quote-PowerShellString $WorkingDirectory

    $windowCommand = @"
`$Host.UI.RawUI.WindowTitle = $quotedTitle
Set-Location -LiteralPath $quotedWorkingDirectory
Write-Host ''
Write-Host 'Starting $title...'
Write-Host 'Working directory: $WorkingDirectory'
Write-Host ''
$Command
Write-Host ''
Write-Host '$title exited. Review the output above, then close this window.'
"@

    return Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $windowCommand
    ) -PassThru
}

Assert-Directory -Path $BackendDir -Name "Backend"
Assert-Directory -Path $FrontendDir -Name "Frontend"
Assert-NoRecordedInstance

if (Test-PortInUse -Port 8000) {
    throw "Port 8000 is already in use. Stop the existing backend before starting LexAd."
}

if (Test-PortInUse -Port 5173) {
    throw "Port 5173 is already in use. Stop the existing frontend before starting LexAd."
}

$pythonCommand = Get-PythonCommand
$npmCommand = Assert-Command "npm.cmd"

if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules") -PathType Container)) {
    Write-Host "Warning: frontend\node_modules was not found. If Vite fails, run npm install in frontend first."
}

$backendCommand = "& $(Quote-PowerShellString $pythonCommand) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
$frontendCommand = "& $(Quote-PowerShellString $npmCommand) run dev -- --host 0.0.0.0 --port 5173 --strictPort"

Write-Host "Starting LexAd backend and frontend..."
$backendProcess = Start-ServiceWindow -Name "Backend" -WorkingDirectory $BackendDir -Command $backendCommand
$frontendProcess = Start-ServiceWindow -Name "Frontend" -WorkingDirectory $FrontendDir -Command $frontendCommand

Start-Sleep -Milliseconds 300

$startedAt = (Get-Date).ToString("o")
$records = @(
    [pscustomobject]@{
        name = "backend"
        rootPid = $backendProcess.Id
        rootProcessStartTime = $backendProcess.StartTime.ToString("o")
        startedAt = $startedAt
        port = 8000
    },
    [pscustomobject]@{
        name = "frontend"
        rootPid = $frontendProcess.Id
        rootProcessStartTime = $frontendProcess.StartTime.ToString("o")
        startedAt = $startedAt
        port = 5173
    }
)

$records | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $PidFile -Encoding UTF8

Write-Host "Started LexAd dev services."
Write-Host ("  Backend:  http://localhost:8000/docs   PID {0}" -f $backendProcess.Id)
Write-Host ("  Frontend: http://localhost:5173        PID {0}" -f $frontendProcess.Id)
Write-Host "Use stop-dev.bat to close the recorded service windows."
