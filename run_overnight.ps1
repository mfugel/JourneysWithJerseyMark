# run_overnight.ps1 - process a Drive folder of Takeout zips in batches.
#
# WHAT IT DOES
#   Moves Takeout zips from G:\My Drive\GooglePhotosTakeout into
#   E:\GooglePhotosTakeouts in batches of $BatchSize, runs INGEST ONLY
#   on each batch, and stops between batches to log a summary.
#
#   After all batches are done, it runs the remaining pipeline steps
#   (thumbnails, geocoding, page render) ONCE -- much faster than running
#   them after every batch.
#
# WHAT IT DOES NOT DO
#   - Does not handle the loose .mp4 files in the Drive folder (only .zip).
#   - Does not commit to git. You do that in GitHub Desktop after a spot-check.
#   - Does not retry failed batches automatically. If a batch fails, the
#     wrapper stops so you can investigate in the morning.
#
# SAFETY
#   - Pre-flight checks: source folder, target folder, free disk space,
#     no Python already running.
#   - Power management: prevents sleep during the run, restores on exit.
#   - All output goes to a timestamped log under E:\MyPhotoArchive\_index\.
#   - Idempotent: re-running picks up where it left off because the underlying
#     ingest script tracks zip-level checkpoints.
#
# USAGE
#   .\run_overnight.ps1                       # full run, batches of 50
#   .\run_overnight.ps1 -BatchSize 25         # smaller batches
#   .\run_overnight.ps1 -DryRun               # show plan, do nothing
#   .\run_overnight.ps1 -SkipFinalSteps       # ingest only, skip thumbs/places/render

[CmdletBinding()]
param(
    [int]$BatchSize = 50,
    [int]$MinFreeGB = 200,
    [string]$Source = 'G:\My Drive\GooglePhotosTakeout',
    [string]$Inbox  = 'E:\GooglePhotosTakeouts',
    [switch]$DryRun,
    [switch]$SkipFinalSteps
)

$ErrorActionPreference = 'Stop'

$PhotoMap = 'C:\Users\mfuge\OneDrive\Desktop\ClaudeDesktop\PhotoMap'
$Repo     = 'C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark'

$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = 'C:\Python313\python.exe' }
if (-not (Test-Path $Python)) {
    Write-Host "ERROR: cannot find python.exe" -ForegroundColor Red
    exit 1
}

$ts      = Get-Date -Format 'yyyyMMdd_HHmmss'
$LogDir  = 'E:\MyPhotoArchive\_index'
$RunLog  = Join-Path $LogDir "overnight_$ts.log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Start-Transcript -Path $RunLog -Append | Out-Null

function Write-Section {
    param([string]$Title)
    $bar = '=' * 70
    Write-Host ''
    Write-Host $bar -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host $bar -ForegroundColor Cyan
    Write-Host ''
}

function Get-FreeGB {
    param([string]$Letter)
    $d = Get-PSDrive -Name $Letter
    return [math]::Round($d.Free / 1GB, 1)
}

function Test-PythonRunning {
    return ((Get-Process python -ErrorAction SilentlyContinue) | Measure-Object).Count -gt 0
}

# ----------------- pre-flight checks -----------------

Write-Section "OVERNIGHT BATCH RUN -- preflight"
Write-Host "Source       : $Source"
Write-Host "Inbox        : $Inbox"
Write-Host "Batch size   : $BatchSize"
Write-Host "Min free GB  : $MinFreeGB"
Write-Host "Dry run      : $DryRun"
Write-Host "Skip final   : $SkipFinalSteps"
Write-Host "Log file     : $RunLog"

if (-not (Test-Path $Source))   { Write-Host "ERROR: Source not found: $Source" -ForegroundColor Red; Stop-Transcript | Out-Null; exit 1 }
if (-not (Test-Path $Inbox))    { Write-Host "ERROR: Inbox not found: $Inbox"   -ForegroundColor Red; Stop-Transcript | Out-Null; exit 1 }
if (-not (Test-Path $PhotoMap)) { Write-Host "ERROR: PhotoMap not found"        -ForegroundColor Red; Stop-Transcript | Out-Null; exit 1 }
if (-not (Test-Path $Repo))     { Write-Host "ERROR: Repo not found"            -ForegroundColor Red; Stop-Transcript | Out-Null; exit 1 }

if (Test-PythonRunning) {
    Write-Host "ERROR: Python is already running. Kill all python processes first:" -ForegroundColor Red
    Write-Host "  Get-Process python | Stop-Process -Force" -ForegroundColor Yellow
    Stop-Transcript | Out-Null
    exit 1
}

$startFree = Get-FreeGB E
Write-Host ("Free space on E: {0} GB" -f $startFree)
if ($startFree -lt $MinFreeGB) {
    Write-Host "ERROR: less than $MinFreeGB GB free on E:; aborting" -ForegroundColor Red
    Stop-Transcript | Out-Null
    exit 1
}

$pending = @(Get-ChildItem -Path (Join-Path $Inbox 'takeout-*.zip') -ErrorAction SilentlyContinue)
if ($pending.Count -gt 0) {
    Write-Host "ERROR: $($pending.Count) zip(s) already in inbox $Inbox" -ForegroundColor Red
    Write-Host "  Run the regular pipeline first to clear them, or move them out manually."
    Stop-Transcript | Out-Null
    exit 1
}

$pattern = 'takeout-20260501T144741Z-3-*.zip'
$allZips = @(Get-ChildItem -Path (Join-Path $Source $pattern) -ErrorAction SilentlyContinue |
             Where-Object { $_.Length -gt 100MB })

if ($allZips.Count -eq 0) {
    Write-Host "No matching zips found in $Source" -ForegroundColor Yellow
    Stop-Transcript | Out-Null
    exit 0
}

$totalGB = [math]::Round(($allZips | Measure-Object Length -Sum).Sum / 1GB, 1)
Write-Host ("Found {0} zip(s) totaling {1} GB" -f $allZips.Count, $totalGB)
$totalBatches = [math]::Ceiling($allZips.Count / $BatchSize)
Write-Host ("Will run {0} batch(es) of up to {1} zips each" -f $totalBatches, $BatchSize)

if ($DryRun) {
    Write-Host "DRY RUN -- exiting before any work"
    Stop-Transcript | Out-Null
    exit 0
}

# ----------------- power management -----------------

$sig = '[DllImport("kernel32.dll", SetLastError=true)] public static extern uint SetThreadExecutionState(uint esFlags);'
try {
    Add-Type -MemberDefinition $sig -Name Power -Namespace Win32 -ErrorAction SilentlyContinue
} catch {}
function Set-StayAwake { [Win32.Power]::SetThreadExecutionState([uint32](2147483648 -bor 1 -bor 64)) | Out-Null }
function Set-AllowSleep { [Win32.Power]::SetThreadExecutionState([uint32]2147483648) | Out-Null }
Set-StayAwake
Write-Host "Power: sleep suppressed for this script"

# ----------------- batch loop -----------------

$batchNum = 0
$startTime = Get-Date

try {
    while ($true) {
        $remaining = @(Get-ChildItem -Path (Join-Path $Source $pattern) -ErrorAction SilentlyContinue |
                       Where-Object { $_.Length -gt 100MB })
        if ($remaining.Count -eq 0) {
            Write-Host ""
            Write-Host "All zips processed. Exiting batch loop." -ForegroundColor Green
            break
        }

        $batchNum++
        $batch = $remaining | Select-Object -First $BatchSize
        $batchSizeGB = [math]::Round(($batch | Measure-Object Length -Sum).Sum / 1GB, 2)

        Write-Section "BATCH $batchNum  ($($batch.Count) zips, $batchSizeGB GB)"

        $freeNow = Get-FreeGB E
        Write-Host ("Free space on E: {0} GB" -f $freeNow)
        if ($freeNow -lt $MinFreeGB) {
            Write-Host "ABORT: less than $MinFreeGB GB free; stopping before batch $batchNum" -ForegroundColor Red
            break
        }

        Write-Host "Moving $($batch.Count) zips from Drive to inbox..."
        $moveStart = Get-Date
        foreach ($z in $batch) {
            try {
                Move-Item -LiteralPath $z.FullName -Destination $Inbox -Force
            } catch {
                Write-Host ("  WARN: failed to move {0}: {1}" -f $z.Name, $_) -ForegroundColor Yellow
            }
        }
        $moveSecs = [math]::Round(((Get-Date) - $moveStart).TotalSeconds, 1)
        Write-Host ("Move complete in {0}s" -f $moveSecs)

        Write-Host ""
        Write-Host "Running ingest..."
        $ingestStart = Get-Date
        Push-Location $PhotoMap
        try {
            & $Python 'extract_to_ssd_v2.py'
            $code = $LASTEXITCODE
            if ($null -eq $code) { $code = 0 }
        } finally {
            Pop-Location
        }
        $ingestMin = [math]::Round(((Get-Date) - $ingestStart).TotalMinutes, 1)

        if ($code -ne 0) {
            Write-Host ""
            Write-Host "BATCH $batchNum FAILED (exit $code) after $ingestMin min" -ForegroundColor Red
            Write-Host "Stopping wrapper. Investigate in the morning." -ForegroundColor Red
            Write-Host "  Log: $RunLog"
            break
        }

        Write-Host ""
        Write-Host ("Batch $batchNum ingest complete in $ingestMin min") -ForegroundColor Green

        $leftover = @(Get-ChildItem -Path (Join-Path $Inbox '*.zip') -ErrorAction SilentlyContinue)
        if ($leftover.Count -gt 0) {
            Write-Host "WARN: $($leftover.Count) zip(s) left in inbox after batch $batchNum" -ForegroundColor Yellow
            foreach ($z in $leftover) { Write-Host "  $($z.Name)" }
        }
    }

    if (-not $SkipFinalSteps) {
        Write-Section "FINAL STEPS -- thumbs, places, render page"

        Push-Location $PhotoMap
        try {
            Write-Host "Building thumbnails..."
            & $Python 'build_journey_thumbs.py'
            if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
                Write-Host "thumbs FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
            }

            Write-Host ""
            Write-Host "Geocoding stay places..."
            & $Python 'build_journey_places.py'
            if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
                Write-Host "places FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
            }
        } finally {
            Pop-Location
        }

        Push-Location $Repo
        try {
            Write-Host ""
            Write-Host "Rendering journeys.html..."
            & $Python 'build_journeys_page.py'
            if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
                Write-Host "render FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
            }
        } finally {
            Pop-Location
        }
    }
} finally {
    Set-AllowSleep
    Write-Host ""
    Write-Host "Power: sleep restored to normal"
}

$totalMin = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
Write-Section "OVERNIGHT RUN COMPLETE"
Write-Host "Batches processed : $batchNum"
Write-Host "Total time        : $totalMin min"
Write-Host "Free space on E:  : $(Get-FreeGB E) GB"
Write-Host "Run log           : $RunLog"
Write-Host ""
Write-Host "In the morning:"
Write-Host "  1. Read $RunLog for any errors"
Write-Host "  2. Spot-check the local map: cd $Repo; python -m http.server 8000"
Write-Host "  3. Commit + push from GitHub Desktop"

Stop-Transcript | Out-Null
