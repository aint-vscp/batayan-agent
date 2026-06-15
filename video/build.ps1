<#
.SYNOPSIS
  One command to build the Batayan demo video end to end:
  (raw recording) -> normalize reference -> clone voice (or default neural voice)
  -> render 1080p video -> publish into the submission folder.

.EXAMPLE
  ./build.ps1 -Recording "C:\Users\Vash\Documents\Sound Recordings\Recording.m4a"
      Clone your voice from that recording, render, and publish.

.EXAMPLE
  ./build.ps1 -Recording auto
      Use the newest file in Documents\Sound Recordings as the voice reference.

.EXAMPLE
  ./build.ps1
      Reuse voice\reference.wav if present, otherwise the default neural voice.

.EXAMPLE
  ./build.ps1 -Default
      Force the default free neural voice (no cloning).
#>
param(
  [string]$Recording,                               # raw recording (m4a/mp3/wav) or "auto"
  [string]$Ref,                                     # advanced: already-prepped reference wav
  [switch]$Default,                                 # force default neural voice
  [string]$Rate = "-4%",                            # default-voice speaking rate
  [string]$Vault = "C:\Users\Vash\Documents\HackathonVault\Hackathons\Agents League 2026",
  [switch]$NoPublish
)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$tts     = Join-Path $HOME ".copilot\skills\tts\scripts\tts.py"
$venvDir = Join-Path $HOME ".coqui-xtts"
$venvPy  = Join-Path $venvDir "Scripts\python.exe"
$refWav  = Join-Path $PSScriptRoot "voice\reference.wav"
if ($Ref) { $refWav = $Ref }

if (-not (Test-Path $tts)) { throw "tts skill not found at $tts" }

# ---- resolve "auto" recording -------------------------------------------
if ($Recording -eq "auto") {
  $rec = Get-ChildItem "$HOME\Documents\Sound Recordings" -Include *.m4a,*.wav,*.mp3 -Recurse -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $rec) { throw "No recordings found in Documents\Sound Recordings." }
  $Recording = $rec.FullName
  Write-Host "Auto-selected recording: $Recording" -ForegroundColor DarkCyan
}

# ---- decide voice mode --------------------------------------------------
if ($Default)              { $mode = "default" }
elseif ($Recording)        { $mode = "clone" }
elseif (Test-Path $refWav) { $mode = "clone" }
else                       { $mode = "default" }

# ---- ensure tooling -----------------------------------------------------
if (-not (Test-Path "node_modules")) {
  Write-Host "Installing Remotion deps..." -ForegroundColor Cyan
  npm install --no-audit --no-fund
}
python -c "import edge_tts" 2>$null
if ($LASTEXITCODE -ne 0) { pip install --quiet edge-tts }

# ---- narrate ------------------------------------------------------------
if ($mode -eq "clone") {
  if ($Recording) {
    if (-not (Test-Path $Recording)) { throw "Recording not found: $Recording" }
    New-Item -ItemType Directory -Force -Path (Split-Path $refWav) | Out-Null
    Write-Host "Prepping reference (mono - 24kHz - normalized)..." -ForegroundColor Cyan
    ffmpeg -y -hide_banner -loglevel error -i $Recording -ac 1 -ar 24000 `
      -af "highpass=f=70,loudnorm=I=-18:TP=-1.5:LRA=11" $refWav
  }
  if (-not (Test-Path $refWav)) { throw "No reference.wav. Pass -Recording <file>." }

  if (-not (Test-Path $venvPy)) {
    Write-Host "Setting up XTTS-v2 clone toolchain (downloads several GB once)..." -ForegroundColor Cyan
    pip install --quiet torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    pip install --quiet coqui-tts
    python -m venv $venvDir --system-site-packages
    & $venvPy -m pip install --quiet --upgrade pip
    & $venvPy -m pip install --quiet "transformers>=4.57,<5"
  }
  $env:COQUI_TOS_AGREED = "1"; $env:USE_TF = "0"; $env:USE_FLAX = "0"
  Write-Host "Synthesizing narration in YOUR voice (GPU)..." -ForegroundColor Cyan
  & $venvPy $tts script script.json --outdir public\audio --engine clone --ref $refWav
}
else {
  Write-Host "Synthesizing narration with the default neural voice..." -ForegroundColor Cyan
  python $tts script script.json --outdir public\audio --engine edge "--rate=$Rate"
}

# ---- render -------------------------------------------------------------
Write-Host "Rendering video..." -ForegroundColor Cyan
npm run render

# ---- publish ------------------------------------------------------------
$out = Join-Path $PSScriptRoot "out\batayan-demo.mp4"
$published = $null
if (-not $NoPublish -and (Test-Path $Vault)) {
  Copy-Item $out (Join-Path $Vault "batayan-demo.mp4") -Force
  if ($mode -eq "clone") { Copy-Item $out (Join-Path $Vault "batayan-demo-myvoice.mp4") -Force }
  $published = Join-Path $Vault "batayan-demo.mp4"
}

# ---- report -------------------------------------------------------------
Write-Host "`n==================== DONE ====================" -ForegroundColor Green
Write-Host ("Voice mode : {0}" -f $mode)
Write-Host ("Video      : {0}" -f $out)
if ($published) { Write-Host ("Published  : {0}" -f $published) }
Write-Host "=============================================" -ForegroundColor Green
