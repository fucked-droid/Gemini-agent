<#
.SYNOPSIS
  Ralph Loop for Antigravity - Execution & State Tracker Helper Script
.DESCRIPTION
  Automates progress tracking, task verification gates, and atomic commits for Ralph Loop runs.
#>

param (
    [Parameter(Position=0)]
    [ValidateSet("init", "status", "verify", "advance")]
    [string]$Action = "status",

    [string]$TaskName = "",
    [string]$TestCommand = "npm test"
)

$PrdPath = "PRD.md"
$ProgressPath = "progress.txt"

switch ($Action) {
    "init" {
        if (-not (Test-Path $PrdPath)) {
            @"
# Product Requirements Document (PRD)

## Goal
Describe feature or objective here.

## Tasks
- [ ] Task 1: Initialize module architecture
- [ ] Task 2: Implement core logic
- [ ] Task 3: Write tests
- [ ] Task 4: Run full verification
"@ | Out-File -FilePath $PrdPath -Encoding utf8
            Write-Host "Created initial $PrdPath"
        }
        if (-not (Test-Path $ProgressPath)) {
            "[Ralph Loop Initialized: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')]" | Out-File -FilePath $ProgressPath -Encoding utf8
            Write-Host "Created initial $ProgressPath"
        }
    }

    "status" {
        if (Test-Path $PrdPath) {
            Write-Host "=== Current PRD Tasks ===" -ForegroundColor Cyan
            Get-Content $PrdPath | Select-String -Pattern "^\s*-\s*\[[ xX]\]" | ForEach-Object { $_.Line }
        } else {
            Write-Warning "$PrdPath does not exist. Run 'ralph-loop.ps1 init' to create one."
        }
        if (Test-Path $ProgressPath) {
            Write-Host "`n=== Latest Progress ===" -ForegroundColor Green
            Get-Content $ProgressPath -Tail 5
        }
    }

    "verify" {
        Write-Host "Executing Verification Test: $TestCommand" -ForegroundColor Yellow
        Invoke-Expression $TestCommand
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n>>> VERIFICATION PASSED <<<" -ForegroundColor Green
            exit 0
        } else {
            Write-Host "`n>>> VERIFICATION FAILED (Exit Code: $LASTEXITCODE) <<<" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }

    "advance" {
        if ([string]::IsNullOrWhiteSpace($TaskName)) {
            Write-Error "TaskName is required for advance action."
            exit 1
        }
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $logLine = "[$timestamp] COMPLETED: $TaskName"
        Add-Content -Path $ProgressPath -Value $logLine
        Write-Host "Progress updated: $logLine" -ForegroundColor Green
    }
}
