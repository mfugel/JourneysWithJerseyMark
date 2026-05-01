# run_pipeline.ps1 - one-command Journeys pipeline
# Drop new Takeout zips into E:\GooglePhotosTakeouts, then run this script.
# Re-running is safe; every step is idempotent.

$ErrorActionPreference = 'Stop'

$PhotoMap = 'C:\Users\mfuge\OneDrive\Desktop\ClaudeDesktop\PhotoMap'
$Repo     = 'C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark'
$Inbox    = 'E:\GooglePhotosTakeouts'

# Resolve python.exe — try PATH first, then known install location
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = 'C:\Python313\python.exe' }
if (-not (Test-Path $Python)) {
    Write-Host "ERROR: cannot find python.exe (tried PATH and C:\Python313\python.exe)" -ForegroundColor Red
    exit 1
}

function Write-Section {
    param([string]$Title)
    $bar = '=' * 70
    Write-Host ''
    Write-Host $bar -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host $bar -ForegroundColor Cyan
    Write-Host ''
}

function Invoke-Step {
    param(
        [string]$Label,
        [string]$WorkDir,
        [string]$ScriptName
    )
    Write-Section $Label
    $start = Get-Date
    Push-Location $WorkDir
    try {
        & $script:Python $ScriptName
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
    } finally {
        Pop-Location
    }
    if ($code -ne 0) {
        Write-Host ''
        Write-Host "STEP FAILED: $Label (exit $code)" -ForegroundColor Red
        Write-Host 'Stopping pipeline. Fix and re-run; earlier steps are idempotent.' -ForegroundColor Red
        exit $code
    }
    $elapsed = (Get-Date) - $start
    $secs = [math]::Round($elapsed.TotalSeconds, 1)
    Write-Host ''
    Write-Host "[$Label] completed in $secs s" -ForegroundColor Green
}

# Sanity checks
if (-not (Test-Path $PhotoMap)) { Write-Host "ERROR: PhotoMap not found at $PhotoMap" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $Repo))     { Write-Host "ERROR: Repo not found at $Repo" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $Inbox))    { Write-Host "ERROR: Inbox not found at $Inbox" -ForegroundColor Red; exit 1 }

# Show inbox contents
$zips = @(Get-ChildItem -Path (Join-Path $Inbox 'takeout-*.zip') -ErrorAction SilentlyContinue)
if ($zips.Count -gt 0) {
    Write-Host 'Takeout zips currently in inbox:' -ForegroundColor Yellow
    foreach ($z in $zips) {
        $sizeGB = [math]::Round($z.Length / 1GB, 2)
        Write-Host ("  {0}  ({1} GB)" -f $z.Name, $sizeGB)
    }
} else {
    Write-Host 'No new zips in inbox. Steps 2-4 will still refresh thumbs/places/page.' -ForegroundColor Yellow
}

Invoke-Step -Label 'STEP 1 of 4 - Ingest Takeout zips'         -WorkDir $PhotoMap -ScriptName 'extract_to_ssd_v2.py'
Invoke-Step -Label 'STEP 2 of 4 - Build journey thumbnails'    -WorkDir $PhotoMap -ScriptName 'build_journey_thumbs.py'
Invoke-Step -Label 'STEP 3 of 4 - Geocode stay places'         -WorkDir $PhotoMap -ScriptName 'build_journey_places.py'
Invoke-Step -Label 'STEP 4 of 4 - Render journeys.html'        -WorkDir $Repo     -ScriptName 'build_journeys_page.py'

Write-Section 'PIPELINE COMPLETE'
Write-Host 'Next steps:' -ForegroundColor Yellow
Write-Host '  1. Optional preview:'
Write-Host "       cd $Repo"
Write-Host '       python -m http.server 8000'
Write-Host '       open http://localhost:8000/journeys.html'
Write-Host ''
Write-Host '  2. Open GitHub Desktop, review changes, commit, push.'
Write-Host '     Vercel auto-deploys on push.'
Write-Host ''
Write-Host 'To remove a sensitive thumb after the fact:'
Write-Host '  - Delete the file from journeys\thumbs\ in File Explorer'
Write-Host "  - Run:  python $PhotoMap\reconcile_thumbs.py"
Write-Host '  - Commit and push from GitHub Desktop'
