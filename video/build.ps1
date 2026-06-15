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
  # Voice cloning runs in an isolated venv (reuses global CUDA torch, but pins
  # transformers<5 so coqui-tts/XTTS works without disturbing the global env).
  $clonePy = Join-Path $HOME ".coqui-xtts\Scripts\python.exe"
  if ($Install -or -not (Test-Path $clonePy)) {
    Write-Host "Setting up the voice-clone toolchain (downloads several GB once)..." -ForegroundColor Cyan
    pip install --quiet torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    pip install --quiet coqui-tts
    python -m venv (Join-Path $HOME ".coqui-xtts") --system-site-packages
    & $clonePy -m pip install --quiet --upgrade pip
    & $clonePy -m pip install --quiet "transformers>=4.57,<5"
  }
  $env:COQUI_TOS_AGREED = "1"; $env:USE_TF = "0"; $env:USE_FLAX = "0"
  Write-Host "Synthesizing narration in YOUR cloned voice (GPU)..." -ForegroundColor Cyan
  & $clonePy $ttsScript script script.json --outdir public\audio --engine clone --ref $Ref
} else {
  Write-Host "Synthesizing narration with the default neural voice..." -ForegroundColor Cyan
  python $ttsScript script script.json --outdir public\audio --engine edge "--rate=$Rate"
}

Write-Host "Rendering the video..." -ForegroundColor Cyan
npm run render

Write-Host "`nDone -> out\batayan-demo.mp4" -ForegroundColor Green
