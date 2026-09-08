param(
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"
$root = "D:\Neuroqaa Stuff\POS System\pos-system-GT"
$archiveDir = "$root\docs\archived_docs"

$filesToArchive = @(
    "CCTV_DATABASE_SETUP.md",
    "CCTV_STORE_COMPLETE_GUIDE.md",
    "KIDS_POSHAK_THEME_GUIDE.md",
    "DASHBOARD_REDESIGN_PROPOSAL.md",
    "DASHBOARD_REDESIGN_SUMMARY.md",
    "DASHBOARD_TESTING_GUIDE.md",
    "UI_UX_REVAMP_SPEC.md",
    "PHASE_8A_COMPLETION_SUMMARY.md",
    "PHASE_8B_STATUS.md",
    "FEATURE_SUMMARY.md",
    "IMPLEMENTATION_GUIDE.md",
    "USER_GUIDE.md",
    "DEVELOPER_CHECKLIST.md",
    "PRODUCT_IMAGES_IMPLEMENTATION.md",
    "RECEIPT_QA_TESTING_GUIDE.md",
    "RECEIPT_TEMPLATES_GUIDE.md",
    "RECEIPT_TEMPLATES_UI_TESTING.md",
    "setup-and-testing.md"
)

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "DOCUMENTATION CLEANUP - Archive Old Files" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "  [DRY RUN MODE] No files will be moved" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "STEP 1: Create archive directory" -ForegroundColor Yellow

if (-not (Test-Path $archiveDir)) {
    if ($DryRun) {
        Write-Host "  Would create: $archiveDir" -ForegroundColor Gray
    } else {
        New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
        Write-Host "  Created: $archiveDir" -ForegroundColor Green
    }
} else {
    Write-Host "  Archive already exists" -ForegroundColor Gray
}

Write-Host ""
Write-Host "STEP 2: Move deprecated files" -ForegroundColor Yellow
Write-Host "  Total files to archive: $($filesToArchive.Count)" -ForegroundColor Gray

$movedCount = 0
$notFoundCount = 0

foreach ($file in $filesToArchive) {
    $sourcePath = "$root\$file"

    if (Test-Path $sourcePath) {
        if ($DryRun) {
            Write-Host "  [WOULD MOVE] $file" -ForegroundColor Gray
        } else {
            Move-Item -Path $sourcePath -Destination "$archiveDir\$file" -Force
            Write-Host "  [MOVED] $file" -ForegroundColor Green
        }
        $movedCount++
    } else {
        Write-Host "  [NOT FOUND] $file" -ForegroundColor DarkGray
        $notFoundCount++
    }
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Files to move:   $movedCount" -ForegroundColor Green
Write-Host "Files not found: $notFoundCount" -ForegroundColor Gray

Write-Host ""
if ($DryRun) {
    Write-Host "DRY RUN COMPLETE - No files were actually moved" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To execute cleanup, run:" -ForegroundColor Cyan
    Write-Host "  cd D:\Neuroqaa Stuff\POS System\pos-system-GT" -ForegroundColor Cyan
    Write-Host "  .\scripts\cleanup_docs.ps1" -ForegroundColor Cyan
} else {
    Write-Host "Cleanup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Files have been moved to docs/archived_docs/" -ForegroundColor Green
}

Write-Host ""
