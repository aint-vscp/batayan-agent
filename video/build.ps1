param(
  [string]$Ref,          # path to your reference WAV -> clones your voice
  [switch]$Install,      # also install the clone toolchain (coqui-tts + torch CUDA)
  [string]$Rate = "-4%"  # edge voice speaking rate
)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$ttsScript = Join-Path $HOME ".copilot\skills\tts\scripts\tts.py"
if (-not (Test-Path $ttsScript)) { throw "tts skill not found at $ttsScript" }

if (-not (Test-Path "node_modules")) {
  Write-Host "Installing Remotion deps..." -ForegroundColor Cyan
  npm install --no-audit --no-fund
}

if ($Ref) {
  if (-not (Test-Path $Ref)) { throw "Reference audio not found: $Ref" }
  if ($Install) {
    Write-Host "Installing voice-clone toolchain (this downloads several GB once)..." -ForegroundColor Cyan
    pip install --quiet coqui-tts
    pip install --quiet torch --index-url https://download.pytorch.org/whl/cu124
  }
  Write-Host "Synthesizing narration in YOUR cloned voice..." -ForegroundColor Cyan
  python $ttsScript script script.json --outdir public\audio --engine clone --ref $Ref
} else {
  Write-Host "Synthesizing narration with the default neural voice..." -ForegroundColor Cyan
  python $ttsScript script script.json --outdir public\audio --engine edge "--rate=$Rate"
}

Write-Host "Rendering the video..." -ForegroundColor Cyan
npm run render

Write-Host "`nDone -> out\batayan-demo.mp4" -ForegroundColor Green
