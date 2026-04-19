#requires -Version 5.1
<#
Push the current branch to origin, then git pull that branch on the Jetson over SSH.

Prereqs: OpenSSH (ssh), git; SSH to the Nano works; commit desktop changes first.

Example (from repo root):
  .\jetson-hcv-risk-poc\scripts\Sync-GitPullOnNano.ps1 -SshHost isha@isha-desktop

To edit files directly on the Nano from Cursor, use Remote - SSH instead of this script.
#>
param(
    [string] $SshHost = "isha@isha-desktop",
    [string] $RemoteRepoPath = "~/hcv-v2x-predictive-risk-mitigation",
    [string] $Branch = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
Set-Location $repoRoot
if (-not (Test-Path ".git")) {
    Write-Error "No .git at $repoRoot — adjust script path if your layout differs."
}

if (-not $Branch) {
    $Branch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($Branch -eq "HEAD") {
        Write-Error "Detached HEAD — checkout a branch or pass -Branch."
    }
}

Write-Host "Pushing branch '$Branch' to origin..."
git push origin $Branch

# One bash line: fetch, ensure we're on $Branch tracking origin, pull with merge (matches your Nano workflow).
$remoteBash = "cd $RemoteRepoPath && git fetch origin && " +
    "if git show-ref --verify --quiet refs/heads/$Branch; then git checkout $Branch; " +
    "else git checkout -b $Branch origin/$Branch; fi && " +
    "git pull origin $Branch --no-rebase"

Write-Host "SSH $SshHost -> $RemoteRepoPath (pull $Branch)..."
ssh $SshHost $remoteBash

Write-Host "Done."
