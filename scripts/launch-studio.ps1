<# ShortSmash Studio launcher - started from the Desktop / Start Menu shortcut.
   Starts the server and opens the Studio in the default browser. #>
$ErrorActionPreference = "Stop"
$InstallDir = Split-Path $PSScriptRoot -Parent  # scripts/ -> repo root
if (-not (Test-Path (Join-Path $InstallDir "shortsmash"))) {
  $InstallDir = Join-Path $HOME "ShortSmash"  # fallback
}
$venvExe = Join-Path $InstallDir ".venv\Scripts\shortsmash.exe"
if (-not (Test-Path $venvExe)) { $venvExe = Join-Path $InstallDir ".venv\Scripts\python.exe" }

Write-Host ""
Write-Host "  ⚒️  ShortSmash Studio starting..." -ForegroundColor Cyan
Write-Host "  Opening http://127.0.0.1:8000 in your browser." -ForegroundColor Gray
Write-Host "  Close this window to stop the server." -ForegroundColor Gray
Write-Host ""

# Open the browser after a short delay (server boot), then run the server in front.
Start-Job -ScriptBlock {
  Start-Sleep -Seconds 4
  Start-Process "http://127.0.0.1:8000"
} | Out-Null

if ($venvExe -like "*shortsmash.exe") {
  & $venvExe serve
} else {
  & $venvExe -m shortsmash.cli serve
}
