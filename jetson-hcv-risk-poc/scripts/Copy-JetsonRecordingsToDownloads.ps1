#Requires -Version 5.1
<#
.SYNOPSIS
  Copy all Phase 0 recordings from the Jetson to this PC's Downloads\recordings folder (SFTP).

.NOTES
  Set the SSH password in this session only (never commit secrets):
    $env:HCV_JETSON_PASSWORD = 'your-password'
  Prefer SSH keys so no password is needed.
  First run may prompt to install the Posh-SSH module (CurrentUser scope).

  Usage (PowerShell):
    cd ...\jetson-hcv-risk-poc\scripts
    $env:HCV_JETSON_PASSWORD = '...'
    .\Copy-JetsonRecordingsToDownloads.ps1
#>

$ErrorActionPreference = "Stop"

# --- Jetson connection (edit if needed) ---
$JetsonHost = "10.0.0.17"
$JetsonUser = "isha"
$JetsonPassword = $env:HCV_JETSON_PASSWORD
if (-not $JetsonPassword) {
    Write-Error "Set `$env:HCV_JETSON_PASSWORD to the Jetson SSH password (or use SSH keys and adjust this script)."
}

# Absolute path on the Jetson (matches ~/hcv-v2x-predictive-risk-mitigation/...)
$RemoteRecordingsPath = "/home/isha/hcv-v2x-predictive-risk-mitigation/jetson-hcv-risk-poc/edge/data/recordings"

# Local: %USERPROFILE%\Downloads\recordings (folder "recordings" is created under Downloads)
$LocalDownloadsRoot = Join-Path $env:USERPROFILE "Downloads"

if (-not (Test-Path -LiteralPath $LocalDownloadsRoot)) {
    New-Item -ItemType Directory -Path $LocalDownloadsRoot -Force | Out-Null
}

# Ensure TLS 1.2 for Install-Module on older Windows
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
    Write-Host "Installing Posh-SSH module (CurrentUser)..."
    Install-Module -Name Posh-SSH -Scope CurrentUser -Force -AllowClobber
}

Import-Module Posh-SSH

$secure = ConvertTo-SecureString $JetsonPassword -AsPlainText -Force
$credential = [pscredential]::new($JetsonUser, $secure)

Write-Host "Connecting to ${JetsonUser}@${JetsonHost} ..."
$session = New-SFTPSession -ComputerName $JetsonHost -Credential $credential -AcceptKey -ErrorAction Stop

try {
    Write-Host "Downloading remote folder:"
    Write-Host "  $RemoteRecordingsPath"
    Write-Host "to local folder:"
    Write-Host "  $LocalDownloadsRoot"
    Write-Host "(creates or updates Downloads\recordings\...)"
    Write-Host ""

    # Downloads the remote directory named 'recordings' into $LocalDownloadsRoot, preserving structure under it.
    Get-SFTPItem -SessionId $session.SessionId -Path $RemoteRecordingsPath -Destination $LocalDownloadsRoot -Force
}
finally {
    Remove-SFTPSession -SessionId $session.SessionId | Out-Null
}

$finalPath = Join-Path $LocalDownloadsRoot "recordings"
Write-Host ""
Write-Host "Done. Expect files under:"
Write-Host "  $finalPath"
