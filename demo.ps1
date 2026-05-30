#Requires -Version 5.1
<#
.SYNOPSIS
    Synthetic Persona Sandbox -- one-command demo launcher.

.DESCRIPTION
    1.  Kills every process currently occupying an app port.
    2.  Loads .env into the current process environment.
    3.  Verifies Docker is running.
    4.  Discovers the virtualenv Python executable.
    5.  Starts all Docker Compose services.
    6.  Waits for PostgreSQL and Redis to report healthy, Qdrant to be running.
    7.  Runs Alembic database migrations.
    8.  Opens a new PowerShell window for the FastAPI server.
    9.  Opens a new PowerShell window for the ARQ simulation worker.
    10. Opens a new PowerShell window for the Vite frontend dev server.
    11. Opens the browser after a short delay.
    12. Prints a URL summary.

.EXAMPLE
    .\demo.ps1
#>

# ---- Bootstrap --------------------------------------------------------------

$RepoRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Set-Location $RepoRoot

# ---- Color helpers ----------------------------------------------------------

function Write-Step { param([string]$Msg)
    Write-Host ""
    Write-Host "  >> $Msg" -ForegroundColor Cyan
}
function Write-Ok   { param([string]$Msg) Write-Host "  OK  $Msg" -ForegroundColor Green  }
function Write-Warn { param([string]$Msg) Write-Host "  !!  $Msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg) Write-Host "  XX  $Msg" -ForegroundColor Red    }

function Exit-Script {
    param([string]$Reason)
    Write-Fail $Reason
    Read-Host "`n  Press Enter to exit"
    exit 1
}

# ---- Banner -----------------------------------------------------------------

Write-Host ""
Write-Host "  ======================================================" -ForegroundColor DarkCyan
Write-Host "     Synthetic Persona Sandbox  --  Demo Launcher       " -ForegroundColor Cyan
Write-Host "  ======================================================" -ForegroundColor DarkCyan
Write-Host ""

# =============================================================================
# STEP 1 -- Kill stale API and frontend processes
# =============================================================================
#
# Only the locally-launched processes are killed (FastAPI + Vite).
# Docker service ports are left alone -- Docker manages its own port bindings.

$AppPorts = @(8001, 5173)

Write-Step "Clearing ports: $($AppPorts -join '  ')"

foreach ($port in $AppPorts) {
    # netstat -ano columns:  Proto  LocalAddr  ForeignAddr  State  PID
    # ":PORT " appears in the Local Address column for both IPv4 and IPv6
    $matchedLines = netstat -ano 2>$null | Where-Object { $_ -match ":$port\s" }

    foreach ($line in $matchedLines) {
        $parts  = ($line.Trim()) -split '\s+'
        $pidStr = $parts[-1]

        if ($pidStr -match '^\d+$') {
            $pidInt = [int]$pidStr
            # Skip PID 0 (Idle) and PID 4 (System) -- cannot be killed
            if ($pidInt -le 4) { continue }

            try {
                Stop-Process -Id $pidInt -Force -ErrorAction SilentlyContinue
                Write-Warn "  Killed PID $pidInt (was on :$port)"
            } catch { }
        }
    }
}

Write-Ok "Ports cleared"

# =============================================================================
# STEP 2 -- Load .env
# =============================================================================

Write-Step "Loading environment variables"

$EnvFile = Join-Path $RepoRoot '.env'

if (-not (Test-Path $EnvFile)) {
    $ExampleFile = Join-Path $RepoRoot '.env.example'
    if (Test-Path $ExampleFile) {
        Copy-Item $ExampleFile $EnvFile
        Write-Warn ".env not found -- copied from .env.example"
        Write-Warn "Set ANTHROPIC_API_KEY in .env before running real simulations"
    } else {
        Exit-Script ".env and .env.example are both missing from $RepoRoot"
    }
}

$envVarsLoaded = 0
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()

    # Skip blank lines and comments
    if (-not $line -or $line -match '^\s*#') { return }

    if ($line -match '^([^=]+)=(.*)$') {
        $key   = $matches[1].Trim()
        $value = $matches[2].Trim()

        # Strip surrounding single or double quotes:  "value" or 'value'  -> value
        $value = $value -replace '^[''"]|[''"]$', ''

        [System.Environment]::SetEnvironmentVariable($key, $value, 'Process')
        $envVarsLoaded++
    }
}

Write-Ok "$envVarsLoaded variables loaded from .env"

# =============================================================================
# STEP 3 -- Verify Docker daemon
# =============================================================================

Write-Step "Checking Docker daemon"

$dockerReady = $false
for ($attempt = 1; $attempt -le 18; $attempt++) {
    # Suppress stderr -- Docker prints pipe-not-found errors while still starting up
    docker info > $null 2> $null
    if ($LASTEXITCODE -eq 0) { $dockerReady = $true; break }
    $elapsed = ($attempt - 1) * 5
    Write-Warn "Docker not yet ready -- ${elapsed}s elapsed (will keep trying up to 90s) ..."
    Start-Sleep 5
}
if (-not $dockerReady) {
    Exit-Script "Docker did not become ready after 90s. Open Docker Desktop, wait for the tray icon to stop animating, then retry."
}

Write-Ok "Docker is running"

# =============================================================================
# STEP 4 -- Locate Python executable
# =============================================================================

Write-Step "Locating Python"

$pythonExe = $null

$venvCandidates = @(
    (Join-Path $RepoRoot '.venv\Scripts\python.exe'),
    (Join-Path $RepoRoot  'venv\Scripts\python.exe')
)

foreach ($candidate in $venvCandidates) {
    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    $sysPython = Get-Command python -ErrorAction SilentlyContinue
    if ($sysPython) {
        $pythonExe = $sysPython.Source
        Write-Warn "No virtualenv found -- using system Python at $pythonExe"
    }
}

if (-not $pythonExe) {
    Exit-Script "Python not found. Create a virtualenv: python -m venv .venv"
}

$pyVersion = & $pythonExe --version 2>&1
Write-Ok "$pyVersion  ->  $pythonExe"

# =============================================================================
# STEP 5 -- docker compose up
# =============================================================================

Write-Step "Starting Docker Compose services (--force-recreate)"

Set-Location $RepoRoot
docker compose up -d --force-recreate
if ($LASTEXITCODE -ne 0) {
    Exit-Script "docker compose up failed (exit code $LASTEXITCODE)"
}

Write-Ok "Compose services started"

# =============================================================================
# STEP 6 -- Wait for services to be ready
# =============================================================================

function Wait-ContainerHealthy {
    <#
    .SYNOPSIS
        Polls docker inspect until the container reports health status "healthy".
        Used for containers that define a HEALTHCHECK in docker-compose.yml
        (spb-postgres, spb-redis).
    #>
    param(
        [Parameter(Mandatory)][string]$ContainerName,
        [int]$TimeoutSec = 120
    )

    Write-Step "Waiting for $ContainerName to be healthy (up to ${TimeoutSec}s)"

    $deadline = (Get-Date).AddSeconds($TimeoutSec)

    while ((Get-Date) -lt $deadline) {
        $status = docker inspect --format '{{.State.Health.Status}}' $ContainerName 2>$null
        if ($status) { $status = $status.Trim() }

        switch ($status) {
            'healthy'   { Write-Ok "$ContainerName is healthy"; return }
            'unhealthy' { Exit-Script "$ContainerName is unhealthy. Check: docker logs $ContainerName" }
            default     { Write-Host "    $ContainerName  [$status] ..." -ForegroundColor DarkGray }
        }

        Start-Sleep 3
    }

    Exit-Script "$ContainerName did not become healthy in ${TimeoutSec}s. Check: docker logs $ContainerName"
}

function Wait-ContainerRunning {
    <#
    .SYNOPSIS
        Polls docker inspect until the container reports State.Status "running".
        Used for containers with no HEALTHCHECK (spb-qdrant).
    #>
    param(
        [Parameter(Mandatory)][string]$ContainerName,
        [int]$TimeoutSec    = 60,
        [int]$ExtraDelaySec = 5
    )

    Write-Step "Waiting for $ContainerName to be running (up to ${TimeoutSec}s)"

    $deadline = (Get-Date).AddSeconds($TimeoutSec)

    while ((Get-Date) -lt $deadline) {
        $status = docker inspect --format '{{.State.Status}}' $ContainerName 2>$null
        if ($status) { $status = $status.Trim() }

        if ($status -eq 'running') {
            Write-Ok "$ContainerName is running"
            if ($ExtraDelaySec -gt 0) {
                Write-Host "    Settling for ${ExtraDelaySec}s ..." -ForegroundColor DarkGray
                Start-Sleep $ExtraDelaySec
            }
            return
        }

        Write-Host "    $ContainerName  [$status] ..." -ForegroundColor DarkGray
        Start-Sleep 3
    }

    Exit-Script "$ContainerName did not start in ${TimeoutSec}s. Check: docker logs $ContainerName"
}

# PostgreSQL and Redis have HEALTHCHECK entries -- wait for "healthy"
Wait-ContainerHealthy -ContainerName 'spb-postgres' -TimeoutSec 120
Wait-ContainerHealthy -ContainerName 'spb-redis'    -TimeoutSec  60

# Qdrant has no HEALTHCHECK -- wait for "running" + 5 s settle time
Wait-ContainerRunning -ContainerName 'spb-qdrant' -TimeoutSec 60 -ExtraDelaySec 5

# =============================================================================
# STEP 7 -- Apply SQL migrations via docker exec + psql
#
# The project uses plain .sql files (no Alembic). Docker applies them
# automatically on a fresh volume via docker-entrypoint-initdb.d, but that
# mechanism only fires on first init. We run them explicitly here so the
# schema is always current regardless of whether the volume pre-exists.
# All migrations use CREATE TABLE/INDEX IF NOT EXISTS -- re-running is safe.
# =============================================================================

Write-Step "Applying SQL migrations"

$MigrationsDir = Join-Path $RepoRoot 'migrations'
$sqlFiles = Get-ChildItem -Path $MigrationsDir -Filter '*.sql' |
            Sort-Object Name

if ($sqlFiles.Count -eq 0) {
    Write-Warn "No .sql files found in migrations\ -- skipping"
} else {
    # Read POSTGRES_ vars from the loaded .env (fall back to docker-compose defaults)
    $pgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { 'spb_user' }
    $pgDb   = if ($env:POSTGRES_DB)   { $env:POSTGRES_DB   } else { 'synthetic_persona' }

    foreach ($sqlFile in $sqlFiles) {
        Write-Host "    Applying $($sqlFile.Name) ..." -ForegroundColor DarkGray

        $sqlContent = Get-Content -Path $sqlFile.FullName -Raw
        $sqlContent | docker exec -i spb-postgres psql -U $pgUser -d $pgDb -v ON_ERROR_STOP=1

        if ($LASTEXITCODE -ne 0) {
            Exit-Script "Migration failed on $($sqlFile.Name) (exit code $LASTEXITCODE)"
        }
    }

    Write-Ok "$($sqlFiles.Count) migration file(s) applied"
}

# =============================================================================
# Helper: launch a child PowerShell window via -EncodedCommand
#
# -EncodedCommand accepts a Base64-encoded UTF-16LE command string.
# This avoids all argument-parsing issues when the repo path contains
# spaces, ampersands, or other shell-special characters.
# =============================================================================

function Start-EncodedWindow {
    param(
        [Parameter(Mandatory)][string]$Title,
        [Parameter(Mandatory)][string]$Command,
        [string]$WorkDir = $RepoRoot
    )

    # Prepend a title setter so each terminal is identifiable in the taskbar
    $fullCmd = '$Host.UI.RawUI.WindowTitle = ''' + $Title + '''; ' + $Command
    $bytes   = [System.Text.Encoding]::Unicode.GetBytes($fullCmd)
    $encoded = [Convert]::ToBase64String($bytes)

    Start-Process powershell.exe `
        -ArgumentList "-NoExit", "-EncodedCommand", $encoded `
        -WorkingDirectory $WorkDir
}

# =============================================================================
# STEP 8 -- FastAPI server
# =============================================================================

Write-Step "Opening FastAPI server window  (port 8001)"

# Set PYTHONPATH so the `api` package is importable from the repo root
$apiCommand = '$env:PYTHONPATH = ''' + $RepoRoot + '''; ' +
              'Set-Location ''' + $RepoRoot + '''; ' +
              '& ''' + $pythonExe + ''' -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8001'

Start-EncodedWindow -Title "SPB API :8001" -Command $apiCommand -WorkDir $RepoRoot

Write-Ok "API server window opened  ->  http://localhost:8001"

# =============================================================================
# STEP 9 -- ARQ simulation worker
# =============================================================================

Write-Step "Opening ARQ worker window"

$workerCommand = '$env:PYTHONPATH = ''' + $RepoRoot + '''; ' +
                 'Set-Location ''' + $RepoRoot + '''; ' +
                 '& ''' + $pythonExe + ''' -m api.worker'

Start-EncodedWindow -Title "SPB ARQ Worker" -Command $workerCommand -WorkDir $RepoRoot

Write-Ok "ARQ worker window opened"

# =============================================================================
# STEP 10 -- Vite frontend dev server
# =============================================================================

Write-Step "Opening Vite dev server window  (port 5173)"

$DashDir = Join-Path $RepoRoot 'dashboard'
$ViteJs  = Join-Path $DashDir 'node_modules\vite\bin\vite.js'

# Install npm dependencies if node_modules is missing
if (-not (Test-Path $ViteJs)) {
    Write-Warn "node_modules not found -- running npm install in dashboard\"
    $origDir = (Get-Location).Path
    Set-Location $DashDir
    npm install
    if ($LASTEXITCODE -ne 0) { Exit-Script "npm install failed" }
    Set-Location $origDir
}

# Verify node is available on PATH
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Exit-Script "node not found on PATH. Install Node.js and retry."
}
$nodeExe = $nodeCmd.Source

# IMPORTANT: do NOT use "npm run dev".
# npm.cmd launches Vite through cmd.exe, which re-parses the path and chokes on
# special characters (& ; spaces) in the repo path.
# Invoking node + the Vite entry-point directly bypasses cmd.exe entirely.
$feCommand = 'Set-Location ''' + $DashDir + '''; ' +
             '& ''' + $nodeExe + ''' ''' + $ViteJs + ''''

Start-EncodedWindow -Title "SPB Vite :5173" -Command $feCommand -WorkDir $DashDir

Write-Ok "Vite dev server window opened  ->  http://localhost:5173"

# =============================================================================
# STEP 11 -- Wait for API then open browser
# =============================================================================

Write-Step "Waiting for API server to be ready ..."

$apiReady = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8001/health" `
                               -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $apiReady = $true; break }
    } catch { }
    Write-Host "    API not yet up -- ${i}/30 ..." -ForegroundColor DarkGray
    Start-Sleep 2
}

if ($apiReady) {
    Write-Ok "API is responding"
} else {
    Write-Warn "API did not respond after 60s -- opening browser anyway"
}

Start-Process "http://localhost:5173"
Write-Ok "Browser opened at http://localhost:5173"

# =============================================================================
# STEP 12 -- Summary
# =============================================================================

$div = "  " + ("-" * 54)

Write-Host ""
Write-Host $div                                                        -ForegroundColor DarkGray
Write-Host "  Service                  URL"                            -ForegroundColor White
Write-Host $div                                                        -ForegroundColor DarkGray
Write-Host "  Dashboard                http://localhost:5173"          -ForegroundColor Green
Write-Host "  API (FastAPI)            http://localhost:8001"          -ForegroundColor Green
Write-Host "  API docs (Swagger)       http://localhost:8001/docs"     -ForegroundColor Green
Write-Host "  API docs (ReDoc)         http://localhost:8001/redoc"    -ForegroundColor Green
Write-Host $div                                                        -ForegroundColor DarkGray
Write-Host "  PostgreSQL               localhost:5432"                 -ForegroundColor Cyan
Write-Host "  Redis                    localhost:6379"                 -ForegroundColor Cyan
Write-Host "  Qdrant                   http://localhost:6333"          -ForegroundColor Cyan
Write-Host "  Kafka                    localhost:9092"                 -ForegroundColor DarkGray
Write-Host "  Schema Registry          http://localhost:8081"          -ForegroundColor DarkGray
Write-Host $div                                                        -ForegroundColor DarkGray
Write-Host "  Prometheus               http://localhost:9090"          -ForegroundColor DarkGray
Write-Host "  Grafana                  http://localhost:3000"          -ForegroundColor DarkGray
Write-Host "  Grafana credentials      admin / changeme"               -ForegroundColor DarkGray
Write-Host $div                                                        -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Stop Docker services:    docker compose down"            -ForegroundColor Gray
Write-Host "  Remove volumes too:      docker compose down -v"         -ForegroundColor Gray
Write-Host ""
