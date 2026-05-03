# cleanup_processed_zips.ps1 - delete already-ingested zips from the inbox.
#
# WHEN IS IT SAFE TO DELETE?
#   Only when Phase 2 classify is actively running. During Phase 1 extraction,
#   later zips in the inbox have NOT yet been extracted -- deleting them would
#   lose content. The script detects which phase is active by looking for
#   classify-specific patterns in log.txt.
#
#   Classify lines look like:  'Photos from XXXX': N media -> photos_from
#   Extract lines look like:   extracting takeout-...zip
#
#   We require the LAST line of log.txt to be a classify-style line
#   (or a Phase 3 cleanup line, which also means classify is done).

param(
    [string]$Inbox = 'E:\GooglePhotosTakeouts',
    [string]$ArchiveIndex = 'E:\MyPhotoArchive\_index',
    [int]$ActivityMaxAgeMin = 15,
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Inbox)) {
    Write-Host "ERROR: inbox not found: $Inbox" -ForegroundColor Red
    exit 1
}

$now = Get-Date
Write-Host "Inbox       : $Inbox"
Write-Host "Now         : $now"
Write-Host ""

$logFile = Join-Path $ArchiveIndex 'log.txt'

if (-not (Test-Path $logFile)) {
    Write-Host "ERROR: log.txt not found at $logFile" -ForegroundColor Red
    Write-Host "  Cannot determine ingest phase. Use -Force at your own risk."
    if (-not $Force) { exit 1 }
}

# Sample the last few non-empty lines of log.txt to figure out what phase we're in
$lastLines = @(Get-Content $logFile -Tail 20 -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne '' })
$lastLine = if ($lastLines.Count -gt 0) { $lastLines[-1] } else { '' }

Write-Host "Most recent log lines (last 5):"
$lastLines | Select-Object -Last 5 | ForEach-Object { Write-Host ("  $_") }
Write-Host ""

$logAge = ($now - (Get-Item $logFile).LastWriteTime).TotalMinutes

# Phase detection
$inExtract = $lastLine -match 'extract|^.*\bextract'  # crude
$inExtract = $lastLine -match '(extracting takeout|extracted in \d+s)'
$inClassify = $lastLine -match "': \d+ media ->|truly orphan sidecar|hash failures|unique hashes|=== PHASE [23]|deleted|Run ended"
$logActive = $logAge -le $ActivityMaxAgeMin

Write-Host "Phase detection:"
Write-Host ("  log.txt last write: {0} min ago" -f [math]::Round($logAge, 1))
Write-Host ("  Looks like Phase 1 extract:  $inExtract")
Write-Host ("  Looks like Phase 2/3 done:   $inClassify")
Write-Host ""

$safe = $false
$reason = ''
if ($Force) {
    $safe = $true
    $reason = '-Force was passed; skipping safety check'
} elseif (-not $logActive) {
    $reason = "log.txt has not been updated in $ActivityMaxAgeMin min -- ingest may be between phases or moving zips"
} elseif ($inExtract) {
    $reason = 'log.txt shows Phase 1 extraction is active -- some zips in the inbox are NOT YET EXTRACTED. DO NOT DELETE.'
} elseif ($inClassify) {
    $safe = $true
    $reason = 'log.txt shows Phase 2 classify or later -- all zips in inbox are extracted'
} else {
    $reason = "could not determine phase from last log line: '$lastLine'"
}

if (-not $safe) {
    Write-Host "REFUSING TO PROCEED" -ForegroundColor Red
    Write-Host "  $reason" -ForegroundColor Red
    Write-Host ""
    Write-Host "  When you see classify lines flowing in the running pipeline window"
    Write-Host "  (e.g., \"'Photos from 2014': 5688 media -> photos_from\") it is safe to retry."
    Write-Host ""
    Write-Host "  To override (only if you really know all zips are extracted), use -Force."
    exit 1
}

Write-Host "SAFE TO PROCEED" -ForegroundColor Green
Write-Host "  $reason"
Write-Host ""

$zips = @(Get-ChildItem (Join-Path $Inbox 'takeout-*.zip') -ErrorAction SilentlyContinue)
if ($zips.Count -eq 0) {
    Write-Host "Inbox is empty. Nothing to delete." -ForegroundColor Yellow
    exit 0
}

$totalGB = [math]::Round(($zips | Measure-Object Length -Sum).Sum / 1GB, 2)
Write-Host "Zips in inbox: $($zips.Count) totaling $totalGB GB"

if ($DryRun) {
    Write-Host ""
    Write-Host "DRY RUN -- nothing will be deleted" -ForegroundColor Yellow
    Write-Host "Sample (first 5):"
    $zips | Sort-Object Name | Select-Object -First 5 | ForEach-Object {
        Write-Host ("  {0}" -f $_.Name)
    }
    exit 0
}

$start = Get-Date
$failed = 0
foreach ($z in $zips) {
    try { Remove-Item -LiteralPath $z.FullName -Force -ErrorAction Stop }
    catch {
        Write-Host ("  failed: {0}: {1}" -f $z.Name, $_) -ForegroundColor Yellow
        $failed++
    }
}
$secs = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)

Write-Host ""
Write-Host "Deletion complete in $secs s" -ForegroundColor Green
Write-Host ("  Deleted : {0}" -f ($zips.Count - $failed))
Write-Host ("  Failed  : {0}" -f $failed)
$free = [math]::Round((Get-PSDrive E).Free / 1GB, 1)
Write-Host ("Free space on E: {0} GB" -f $free)
