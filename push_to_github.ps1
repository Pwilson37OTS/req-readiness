# Push the latest req-scores.json to the GitHub repo that hosts the Streamlit app.
#
# Called by the daily Claude scheduled task after the readiness pipeline finishes.
# Requires:
#   - This folder ($here) is a checked-out git repo with origin set to GitHub
#   - A deploy key (~/.ssh/oaktree_streamlit_deploy_key) registered as a write-enabled
#     deploy key on the GitHub repo
#   - The req-readiness pipeline already wrote ../req-readiness/state/req-scores.json

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $here "..\req-readiness\state\req-scores.json"
$dest   = Join-Path $here "data\req-scores.json"

if (-not (Test-Path $source)) { Write-Error "Source missing: $source"; exit 1 }
Copy-Item $source $dest -Force

# Tell git to use the deploy key
$env:GIT_SSH_COMMAND = "ssh -i `"$HOME\.ssh\oaktree_streamlit_deploy_key`" -o StrictHostKeyChecking=accept-new"

Set-Location $here

# Skip if nothing changed (avoids empty commits)
git add data/req-scores.json
$diff = git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "no changes to req-scores.json; skipping push"
    exit 0
}

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git -c user.name="OakTree Pipeline" -c user.email="pipeline@oaktreestaffing.com" `
    commit -m "Auto: req-scores update $stamp" | Out-Null
git push origin HEAD
if ($LASTEXITCODE -eq 0) {
    Write-Host "pushed req-scores.json @ $stamp"
} else {
    Write-Error "git push failed"
    exit $LASTEXITCODE
}
