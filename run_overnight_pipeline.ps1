# run_overnight_pipeline.ps1
# Batched overnight ingest of Google Photos Takeout zips from Drive.
#
# What it does:
#   - Finds zips in G:\My Drive\GooglePhotosTakeout matching the configured pattern
#   - Moves them in batches of $BatchSize into E:\GooglePhotosTakeouts
#   - Runs ingest only on each batch
#   - Stops on any error
#   - After all batches succeed, runs thumbs + places + page render once

# ---------- CONFIG ----------
$DriveSource    = 'G:\My Drive\GooglePhotosTakeout'
$Inbox          = 'E:\GooglePhotosTakeouts'
$ZipPattern     = 'takeout-20260501T144741Z-3-*.zip'
$BatchSize      = 50
$MinFreeGB      = 200
$MaxRunHours    = 12
$PhotoMap       = 'C:\Users\mfuge\OneDrive\Desktop\ClaudeDesktop\PhotoMap'
$Repo           = 'C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark'
$LogDir         = 'E:\MyPhotoArchive\_index\overnight'
# ----------------------------

$ErrorActionPreference = 'Stop'
$Started = Get-Date

# Resolve python.exe
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = 'C:\Python313\python.exe' }
if (-not (Test-Path $Python)) { Write-Host 'ERROR: python.exe not found' -ForegroundColor Red; exit 1 }

# Sanity checks
if (-not (Test-Path $DriveSource)) { Write-Host "ERROR: Drive source not found: $DriveSource" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $Inbox))       { Write-Host "ERROR: Inbox not found: $Inbox" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $PhotoMap))    { Write-Host "ERROR: PhotoMap not found: $PhotoMap" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $Repo))        { Write-Host "ERROR: Repo not found: $Repo" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $LogDir))      { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }

function Write-Section { param([string]$Title)
    $bar = '=' * 70
    Write-Host ''
    Write-Host $bar -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host $bar -ForegroundColor Cyan
    Write-Host ''
}

function Get-FreeSpaceGB { param([string]$DriveLetter)
    $d = Get-PSDrive $DriveLetter -ErrorAction SilentlyContinue
    if ($d) { return [math]::Round($d.Free / 1GB, 1) }
    return 0
}

function Should-Stop {
    $elapsed = (Get-Date) - $Started
    if ($elapsed.TotalHours -ge $MaxRunHours) {
        Write-Host "STOPPING: max runtime ($MaxRunHours h) reached." -ForegroundColor Yellow
        return $true
    }
    return $false
}

# Inbox sanity: must be empty before we start
$inboxNow = @(Get-ChildItem -Path (Join-Path $Inbox '*.zip') -ErrorAction SilentlyContinue)
if ($inboxNow.Count -gt 0) {
    Write-Host 'ERROR: inbox is not empty. Process or remove those zips first.' -ForegroundColor Red
    Write-Host "Inbox: $Inbox"
    foreach ($z in $inboxNow) { Write-Host "  $($z.Name)" }
    exit 1
}

# Get the candidate list from Drive
$candidates = @(Get-ChildItem -Path (Join-Path $DriveSource $ZipPattern) -ErrorAction SilentlyContinue | Sort-Object Name)
if ($candidates.Count -eq 0) {
    Write-Host "No zips matching '$ZipPattern' found in $DriveSource" -ForegroundColor Yellow
    exit 1
}

# Filter out 0-byte files (broken downloads)
$preFilterCount = $candidates.Count
$candidates = @($candidates | Where-Object { $_.Length -gt 0 })
$skipped = $preFilterCount - $candidates.Count
if ($skipped -gt 0) {
    Write-Host "Skipping $skipped zero-byte zip file(s) (broken downloads)" -ForegroundColor Yellow
}

$totalBatches = [math]::Ceiling($candidates.Count / $BatchSize)
Write-Host ''
Write-Host 'Overnight ingest plan:' -ForegroundColor Yellow
Write-Host "  Source       : $DriveSource"
Write-Host "  Pattern      : $ZipPattern"
Write-Host "  Total zips   : $($candidates.Count)"
Write-Host "  Batch size   : $BatchSize"
Write-Host "  Batches      : $totalBatches"
$freeNow = Get-FreeSpaceGB 'E'
Write-Host "  E: free now  : $freeNow GB"
Write-Host "  Min free req : $MinFreeGB GB before each batch"
Write-Host "  Max runtime  : $MaxRunHours hours"
Write-Host "  Log dir      : $LogDir"
Write-Host ''

$batchNum = 0
$processed = 0
while ($processed -lt $candidates.Count) {
    if (Should-Stop) { break }

    $batchNum++
    $remaining = $candidates.Count - $processed
    $thisBatch = [math]::Min($BatchSize, $remaining)
    $batch = $candidates[$processed..($processed + $thisBatch - 1)]

    Write-Section "BATCH $batchNum / $totalBatches - moving $thisBatch zips"

    # Disk space check
    $freeGB = Get-FreeSpaceGB 'E'
    if ($freeGB -lt $MinFreeGB) {
        Write-Host "STOPPING: E: free space ($freeGB GB) below threshold ($MinFreeGB GB)." -ForegroundColor Red
        Write-Host 'Manually clean up _staging or _quarantine and restart.' -ForegroundColor Red
        exit 1
    }
    Write-Host "E: free space before batch: $freeGB GB"

    # Move the zips into the inbox
    $movedCount = 0
    foreach ($z in $batch) {
        $dst = Join-Path $Inbox $z.Name
        try {
            Move-Item -LiteralPath $z.FullName -Destination $dst -ErrorAction Stop
            $movedCount++
        } catch {
            Write-Host "ERROR moving $($z.Name): $_" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "Moved $movedCount zips to inbox."

    # Run ingest only
    $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $batchLog = Join-Path $LogDir "batch-$batchNum-$stamp.log"

    $start = Get-Date
    Push-Location $PhotoMap
    try {
        & $Python 'extract_to_ssd_v2.py' *>&1 | Tee-Object -FilePath $batchLog
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
    } finally {
        Pop-Location
    }
    $elapsed = (Get-Date) - $start

    if ($code -ne 0) {
        Write-Host ''
        Write-Host "BATCH $batchNum FAILED (exit $code) - stopping pipeline." -ForegroundColor Red
        Write-Host "Log: $batchLog" -ForegroundColor Yellow
        exit $code
    }

    # The script itself extracts zips and marks them done in zip_progress.json
    # but does NOT delete the .zip from the inbox. We delete them after a clean run.
    $remainInInbox = @(Get-ChildItem -Path (Join-Path $Inbox '*.zip') -ErrorAction SilentlyContinue)
    foreach ($z in $remainInInbox) {
        Remove-Item -LiteralPath $z.FullName -Force
    }
    Write-Host "Cleared $($remainInInbox.Count) processed zip(s) from inbox."

    $processed += $thisBatch
    $secs = [math]::Round($elapsed.TotalMinutes, 1)
    Write-Host "BATCH $batchNum complete in $secs min. Total processed: $processed / $($candidates.Count)" -ForegroundColor Green
    $freeAfter = Get-FreeSpaceGB 'E'
    Write-Host "E: free space after batch: $freeAfter GB"
}

# Final phase - only if we processed everything
if ($processed -ge $candidates.Count) {
    Write-Section 'ALL BATCHES COMPLETE - building thumbs + places + page'

    $finalSteps = @(
        @{ Label = 'Thumbnails';        Dir = $PhotoMap; Script = 'build_journey_thumbs.py' },
        @{ Label = 'Places (geocode)';  Dir = $PhotoMap; Script = 'build_journey_places.py' },
        @{ Label = 'Render page';       Dir = $Repo;     Script = 'build_journeys_page.py' }
    )

    foreach ($s in $finalSteps) {
        Write-Section "FINAL - $($s.Label)"
        $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
        $log = Join-Path $LogDir "final-$($s.Script)-$stamp.log"
        Push-Location $s.Dir
        try {
            & $Python $s.Script *>&1 | Tee-Object -FilePath $log
            $code = $LASTEXITCODE
            if ($null -eq $code) { $code = 0 }
        } finally {
            Pop-Location
        }
        if ($code -ne 0) {
            Write-Host "FINAL STEP FAILED ($($s.Label)) - log: $log" -ForegroundColor Red
            exit $code
        }
    }

    Write-Section 'OVERNIGHT PIPELINE COMPLETE'
    $totalElapsed = (Get-Date) - $Started
    $totalHours = [math]::Round($totalElapsed.TotalHours, 1)
    Write-Host "Total runtime: $totalHours hours" -ForegroundColor Green
    Write-Host ''
    Write-Host 'Next steps:' -ForegroundColor Yellow
    Write-Host "  1. Review batch logs in: $LogDir"
    Write-Host '  2. Open GitHub Desktop, review changes, commit, push.'
    Write-Host '  3. Visit https://www.journeyswithjerseymark.com/journeys.html'
} else {
    Write-Section 'OVERNIGHT PIPELINE STOPPED EARLY'
    Write-Host "Processed $processed of $($candidates.Count) zips. Re-run to continue." -ForegroundColor Yellow
    Write-Host "Logs in: $LogDir"
}
