param(
    [ValidateSet("local", "neon")]
    [string]$DatabaseMode = "local"
)

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

function Get-PortListenerProcessIds {
    param([Parameter(Mandatory = $true)][int]$Port)

    return @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
}

function Stop-ProcessTree {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $taskkillOutput = & taskkill.exe /PID $ProcessId /T /F 2>&1 | Out-String
        $taskkillExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($taskkillExitCode -ne 0 -and (Test-ProcessIsRunning -ProcessId $ProcessId)) {
        $detail = $taskkillOutput.Trim()
        if (-not $detail) {
            $detail = "taskkill exited with code $taskkillExitCode"
        }
        throw "Could not stop PID ${ProcessId}: $detail"
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

function Get-PortOwnerSummary {
    param([Parameter(Mandatory = $true)][int[]]$ProcessIds)

    $descriptions = foreach ($processId in $ProcessIds) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            "PID $processId (process exited before it could be inspected)"
            continue
        }

        $path = $null
        try {
            $path = $process.Path
        }
        catch {}

        if ($path) {
            "PID $processId ($($process.ProcessName), $path)"
        }
        else {
            "PID $processId ($($process.ProcessName))"
        }
    }

    return ($descriptions -join "; ")
}

function Test-IsLexAdFrontendListener {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][int]$ProcessId
    )

    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $process -or $process.ProcessName -ne "node") {
        return $false
    }

    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 2
    }
    catch {
        return $false
    }

    return (
        $response.StatusCode -eq 200 -and
        $response.Content -match '<title>\s*LexAd\b' -and
        $response.Content -match '/@vite/client' -and
        $response.Content -match '/src/main\.ts'
    )
}

function Stop-VerifiedLexAdFrontendOnPort {
    param([Parameter(Mandatory = $true)][int]$Port)

    $listenerProcessIds = @(Get-PortListenerProcessIds -Port $Port)
    if ($listenerProcessIds.Count -eq 0) {
        return
    }

    $unverifiedProcessIds = @(
        $listenerProcessIds | Where-Object {
            -not (Test-IsLexAdFrontendListener -Port $Port -ProcessId $_)
        }
    )
    if ($unverifiedProcessIds.Count -gt 0) {
        $owners = Get-PortOwnerSummary -ProcessIds $listenerProcessIds
        throw "Port $Port is occupied by $owners. The listener is not a verified LexAd Vite frontend, so it was not stopped."
    }

    Write-Host "Port $Port is used by an existing LexAd frontend. Stopping the old frontend..."

    $frontendWindows = @(
        Get-Process -ErrorAction SilentlyContinue | Where-Object {
            $_.ProcessName -in @("powershell", "pwsh") -and
            $_.MainWindowTitle -eq "LexAd Frontend"
        }
    )

    if ($frontendWindows.Count -eq 1) {
        Stop-ProcessTree -ProcessId $frontendWindows[0].Id
    }
    elseif ($frontendWindows.Count -gt 1) {
        Write-Host "  Multiple LexAd Frontend windows were found; only the verified port listener will be stopped."
    }

    foreach ($processId in $listenerProcessIds) {
        if (Test-ProcessIsRunning -ProcessId $processId) {
            Stop-ProcessTree -ProcessId $processId
        }
    }

    $releaseTimeout = (Get-Date).AddSeconds(5)
    while ((Get-Date) -lt $releaseTimeout -and (Test-PortInUse -Port $Port)) {
        Start-Sleep -Milliseconds 250
    }

    if (Test-PortInUse -Port $Port) {
        $remainingProcessIds = @(Get-PortListenerProcessIds -Port $Port)
        $owners = Get-PortOwnerSummary -ProcessIds $remainingProcessIds
        throw "The old LexAd frontend could not release port ${Port}: $owners"
    }

    Write-Host "Port $Port was released by the old LexAd frontend."
}

function Write-PidRecords {
    param([Parameter(Mandatory = $true)][array]$Records)

    $tempPidFile = "$PidFile.tmp"
    $Records | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $tempPidFile -Encoding UTF8
    Move-Item -LiteralPath $tempPidFile -Destination $PidFile -Force
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

function Stop-RecordedInstanceForRestart {
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
    $mismatched = @()
    foreach ($record in @($records)) {
        if ($null -eq $record.rootPid) {
            continue
        }

        $process = Get-Process -Id ([int]$record.rootPid) -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            continue
        }

        if (Test-RecordedProcessMatches -Record $record -Process $process) {
            $running += [pscustomobject]@{
                record = $record
                process = $process
            }
        }
        else {
            $mismatched += $record
        }
    }

    if ($mismatched.Count -gt 0) {
        $details = @(
            $mismatched | ForEach-Object { "{0}: PID {1}" -f $_.name, $_.rootPid }
        ) -join "; "
        throw "The saved LexAd process record is stale and now points to another process ($details). It was not stopped. Delete scripts\.dev-pids.json after verifying the recorded PIDs."
    }

    if ($running.Count -gt 0) {
        Write-Host "A recorded LexAd instance is already running. Stopping it before restart..."
        foreach ($item in $running) {
            Write-Host ("  Stopping {0}: PID {1}" -f $item.record.name, $item.record.rootPid)
            Stop-ProcessTree -ProcessId ([int]$item.record.rootPid)
        }

        $stopTimeout = (Get-Date).AddSeconds(5)
        do {
            $stillRunning = @(
                $running | Where-Object {
                    $process = Get-Process -Id ([int]$_.record.rootPid) -ErrorAction SilentlyContinue
                    $null -ne $process -and (Test-RecordedProcessMatches -Record $_.record -Process $process)
                }
            )
            if ($stillRunning.Count -eq 0) {
                break
            }
            Start-Sleep -Milliseconds 250
        } while ((Get-Date) -lt $stopTimeout)

        if ($stillRunning.Count -gt 0) {
            $details = @(
                $stillRunning | ForEach-Object { "{0}: PID {1}" -f $_.record.name, $_.record.rootPid }
            ) -join "; "
            throw "The old recorded LexAd instance could not be stopped ($details)."
        }
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

function Extract-AlembicRevision {
    param([Parameter(Mandatory = $true)][string]$Text)
    $match = [regex]::Match($Text, '\b([0-9a-f]{12})\b')
    if ($match.Success) {
        return $match.Groups[1].Value
    }
    return $null
}

Assert-Directory -Path $BackendDir -Name "Backend"
Assert-Directory -Path $FrontendDir -Name "Frontend"
Stop-RecordedInstanceForRestart

if (Test-PortInUse -Port 8000) {
    throw "Port 8000 is already in use. Stop the existing backend before starting LexAd."
}

Stop-VerifiedLexAdFrontendOnPort -Port 5173

$pythonCommand = Get-PythonCommand
$npmCommand = Assert-Command "npm.cmd"

# ── Database preflight ───────────────────────────────────────────────────
$env:DATABASE_MODE = $DatabaseMode
if ($DatabaseMode -eq "local") {
    Write-Host "Database target: local SQLite"
    Write-Host "Running alembic upgrade head..."

    Push-Location $BackendDir
    try {
        & $pythonCommand -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            throw "Alembic migration failed. Check the output above for details."
        }
        Write-Host "Alembic migration: OK"

        & $pythonCommand -m app.db.seed
        if ($LASTEXITCODE -ne 0) {
            throw "Database seed failed. Check the output above for details."
        }
        Write-Host "Database seed: OK"
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "Database target: Neon PostgreSQL"
    Write-Host "Running read-only preflight checks..."

    Push-Location $BackendDir
    try {
        $currentOutput = & $pythonCommand -m alembic current 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            throw "Neon connection or SSL session failed. Check DATABASE_URL and network reachability."
        }

        $headsOutput = & $pythonCommand -m alembic heads 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            throw "Cannot read Alembic heads revision."
        }

        $currentRev = Extract-AlembicRevision -Text $currentOutput
        $headsRev = Extract-AlembicRevision -Text $headsOutput

        if (-not $currentRev) {
            throw "Neon migration is behind: no Alembic revision found in the database. Run manual migration first."
        }
        if (-not $headsRev) {
            throw "Cannot determine the latest Alembic revision."
        }
        if ($currentRev -ne $headsRev) {
            throw "Neon migration is behind: database is at $currentRev, latest is $headsRev. Run manual migration first."
        }
        Write-Host "Neon migration check: OK (revision $currentRev)"
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules") -PathType Container)) {
    Write-Host "Warning: frontend\node_modules was not found. If Vite fails, run npm install in frontend first."
}

$backendCommand = "`$env:DATABASE_MODE = $(Quote-PowerShellString $DatabaseMode); & $(Quote-PowerShellString $pythonCommand) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
$frontendCommand = "& $(Quote-PowerShellString $npmCommand) run dev -- --host 0.0.0.0 --port 5173 --strictPort"

Write-Host "Starting LexAd backend and frontend..."
Write-Host ("Database mode: {0}" -f $DatabaseMode)
$startedAt = (Get-Date).ToString("o")
$records = @()

$backendProcess = Start-ServiceWindow -Name "Backend" -WorkingDirectory $BackendDir -Command $backendCommand
$records += [pscustomobject]@{
    name = "backend"
    rootPid = $backendProcess.Id
    rootProcessStartTime = $backendProcess.StartTime.ToString("o")
    startedAt = $startedAt
    port = 8000
}
Write-PidRecords -Records $records

$frontendProcess = Start-ServiceWindow -Name "Frontend" -WorkingDirectory $FrontendDir -Command $frontendCommand
$records += [pscustomobject]@{
    name = "frontend"
    rootPid = $frontendProcess.Id
    rootProcessStartTime = $frontendProcess.StartTime.ToString("o")
    startedAt = $startedAt
    port = 5173
}
Write-PidRecords -Records $records

# Wait for both services to become healthy, for at most 30 seconds.
$timeout = (Get-Date).AddSeconds(30)
$backendOk = $false
$frontendOk = $false

while ((Get-Date) -lt $timeout) {
    Start-Sleep -Milliseconds 1500

    $backendProcess.Refresh()
    $frontendProcess.Refresh()
    if ($backendProcess.HasExited -or $frontendProcess.HasExited) {
        break
    }

    if (-not $backendOk) {
        try {
            $b = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
            if ($b.StatusCode -eq 200 -and ($b.Content | ConvertFrom-Json).status -eq "ok") {
                $backendOk = $true
                Write-Host "  Backend health check: OK"
            }
        } catch {}
    }

    if (-not $frontendOk) {
        try {
            $f = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 2 -UseBasicParsing
            if ($f.StatusCode -eq 200) {
                $frontendOk = $true
                Write-Host "  Frontend health check: OK"
            }
        } catch {}
    }

    if ($backendOk -and $frontendOk) { break }
}

if (-not $backendOk) {
    Write-Host "  Backend health check: FAILED (port 8000 not responding)"
}
if (-not $frontendOk) {
    Write-Host "  Frontend health check: FAILED (port 5173 not responding)"
}

if (-not ($backendOk -and $frontendOk)) {
    Write-Host "Startup did not complete. Process records were kept at scripts\.dev-pids.json."
    Write-Host "Review the Backend and Frontend windows, then run stop-dev.bat to clean up."
    throw "LexAd health checks failed."
}

Write-Host "Started LexAd dev services."
Write-Host ("  Backend:  http://localhost:8000/docs   PID {0}" -f $backendProcess.Id)
Write-Host ("  Frontend: http://localhost:5173        PID {0}" -f $frontendProcess.Id)
Write-Host "Use stop-dev.bat to close the recorded service windows."

try {
    Start-Process -FilePath "http://localhost:5173"
    Write-Host "Opened the LexAd frontend in the default browser."
}
catch {
    Write-Host "Warning: the browser could not be opened automatically."
    Write-Host "Open http://localhost:5173 manually."
}
