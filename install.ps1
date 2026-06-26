# install.ps1 — Install pokanop/scripts on Windows
#
# Usage:
#   irm https://raw.githubusercontent.com/pokanop/scripts/main/install.ps1 | iex
#   .\install.ps1 [-Update] [-Tools medcat,pluck] [-Dir PATH] [-InPlace]

param(
    [switch]$Update,
    [switch]$InPlace,
    [switch]$NoPath,
    [string]$Dir = "",
    [string]$BinDir = "",
    [string]$Tools = ""
)

$ErrorActionPreference = "Stop"

$RepoUrl = if ($env:SCRIPTS_REPO_URL) { $env:SCRIPTS_REPO_URL } else { "https://github.com/pokanop/scripts.git" }
$RepoRef = if ($env:SCRIPTS_REPO_REF) { $env:SCRIPTS_REPO_REF } else { "main" }

$InstallDir = if ($Dir) {
    $Dir
} elseif ($env:SCRIPTS_HOME) {
    $env:SCRIPTS_HOME
} else {
    Join-Path $env:LOCALAPPDATA "scripts"
}

$BinDirResolved = if ($BinDir) {
    $BinDir
} elseif ($env:SCRIPTS_BIN) {
    $env:SCRIPTS_BIN
} else {
    Join-Path $env:LOCALAPPDATA "bin"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($InPlace) {
    $InstallDir = $ScriptDir
} elseif ((Test-Path (Join-Path $ScriptDir "scripts")) -and (Test-Path (Join-Path $ScriptDir "requirements")) -and (Test-Path (Join-Path $ScriptDir ".git"))) {
    $InstallDir = $ScriptDir
    $InPlace = $true
}

Write-Host "==> pokanop/scripts installer"
Write-Host "    Install dir: $InstallDir"
Write-Host "    Bin dir:     $BinDirResolved"
Write-Host ""

if (-not $InPlace -and -not (Test-Path (Join-Path $InstallDir ".git"))) {
    if (Test-Path $InstallDir) {
        Write-Host "==> Using existing directory: $InstallDir"
    } else {
        Write-Host "==> Cloning $RepoUrl (ref: $RepoRef)"
        git clone --depth 1 --branch $RepoRef $RepoUrl $InstallDir
    }
} elseif ($Update -and (Test-Path (Join-Path $InstallDir ".git"))) {
    Write-Host "==> Pulling latest changes"
    git -C $InstallDir pull --ff-only
}

$ScriptsMeta = Join-Path $InstallDir "scripts"
if (-not (Test-Path $ScriptsMeta)) {
    throw "Install directory is incomplete: $InstallDir"
}

$Python = if ($env:SCRIPTS_PYTHON) { $env:SCRIPTS_PYTHON } else { "python" }

$InstallArgs = @("install", "--dir", $InstallDir, "--bin-dir", $BinDirResolved)
if ($NoPath) { $InstallArgs += "--no-path" }
if ($Update) { $InstallArgs += "--upgrade" }
if ($Tools) { $InstallArgs += ($Tools -split ",") }

Write-Host "==> Running scripts install"
& $Python $ScriptsMeta @InstallArgs