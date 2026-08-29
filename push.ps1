# push.ps1 — run inside poem-aesthetic-analysis-export/
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path ".env") {
    throw "Found .env — remove or move it before pushing"
}
$extraMd = Get-ChildItem -Recurse -Filter "*.md" | Where-Object { $_.Name -ne "README.md" }
if ($extraMd) {
    throw "Extra .md files found: $($extraMd.FullName -join ', ')"
}

git init
git branch -M main

$remoteUrl = "https://github.com/omega-c-sun/Poem-aesthetic-analysis.git"
$existing = git remote get-url origin 2>$null
if (-not $existing) {
    git remote add origin $remoteUrl
} elseif ($existing -ne $remoteUrl) {
    git remote set-url origin $remoteUrl
}

git add .
Write-Host "`n--- git status ---"
git status
Write-Host "`nConfirm no .env, no extra .md, no pdf/typ — then press Enter to continue..."
Read-Host

git commit -m "Initial release: poem survey data, analysis pipeline, and results"

# If remote already has an initial commit (e.g. LICENSE), uncomment the next two lines:
# git pull origin main --rebase --allow-unrelated-histories
# git push -u origin main

git push -u origin main
Write-Host "`nDone: https://github.com/omega-c-sun/Poem-aesthetic-analysis"
