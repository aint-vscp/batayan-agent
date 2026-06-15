<#
.SYNOPSIS
  Build the Batayan demo video end to end. Several voice modes:

    -Takes <dir>      Use your REAL per-segment recordings (Intro.m4a, Beat 1.m4a,
                      Beat 2.m4a, Beat 3.m4a, Outro.m4a). Literally your voice.
                      Also refreshes the reusable clone profile (-ProfileName).
    -Profile <name>   Render in your CLONED voice profile (works for ANY script).
    -Recording <file> Clone your voice from a single raw recording (or "auto").
    -Default          Default free neural voice.
    (none)            Reuse voice\reference.wav if present, else default voice.

.EXAMPLE
  ./build.ps1 -Takes "C:\Users\Vash\Documents\Sound Recordings"
.EXAMPLE
  ./build.ps1 -Profile vash      # reuse your cloned voice on a NEW script.json
#>
param(
  [string]$Takes,
  [string]$Profile,
  [string]$ProfileName = "vash",
  [string]$Recording,
  [string]$Ref,
  [switch]$Default,
  [string]$Rate = "-4%",
  [string]$Vault = "C:\Users\Vash\Documents\HackathonVault\Hackathons\Agents League 2026",
  [switch]$NoPublish
)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$tts        = Join-Path $HOME ".copilot\skills\tts\scripts\tts.py"
$venvDir    = Join-Path $HOME ".coqui-xtts"
$venvPy     = Join-Path $venvDir "Scripts\python.exe"
$refWav     = if ($Ref) { $Ref } else { Join-Path $PSScriptRoot "voice\reference.wav" }
$profileDir = Join-Path $HOME ".copilot\skills\tts\voices\$ProfileName"
if (-not (Test-Path $tts)) { throw "tts skill not found at $tts" }

if ($Recording -eq "auto") {
  $rec = Get-ChildItem "$HOME\Documents\Sound Recordings" -Include *.m4a,*.wav,*.mp3 -Recurse -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $rec) { throw "No recordings found in Documents\Sound Recordings." }
  $Recording = $rec.FullName
}

if     ($Takes)              { $mode = "takes" }
elseif ($Profile)            { $mode = "profile" }
elseif ($Default)            { $mode = "default" }
elseif ($Recording)          { $mode = "clone" }
elseif (Test-Path $refWav)   { $mode = "clone" }
else                         { $mode = "default" }

if (-not (Test-Path "node_modules")) {
  Write-Host "Installing Remotion deps..." -ForegroundColor Cyan
  npm install --no-audit --no-fund
}
python -c "import edge_tts" 2>$null
if ($LASTEXITCODE -ne 0) { pip install --quiet edge-tts }

function Ensure-CloneVenv {
  if (-not (Test-Path $venvPy)) {
    Write-Host "Setting up XTTS-v2 clone toolchain (downloads several GB once)..." -ForegroundColor Cyan
    pip install --quiet torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    pip install --quiet coqui-tts
    python -m venv $venvDir --system-site-packages
    & $venvPy -m pip install --quiet --upgrade pip
    & $venvPy -m pip install --quiet "transformers>=4.57,<5"
  }
  $env:COQUI_TOS_AGREED = "1"; $env:USE_TF = "0"; $env:USE_FLAX = "0"
}

switch ($mode) {
  "takes" {
    if (-not (Test-Path $Takes)) { throw "Takes folder not found: $Takes" }
    Write-Host "Using your REAL recordings + refreshing clone profile '$ProfileName'..." -ForegroundColor Cyan
    python $tts takes $Takes --script script.json --outdir public\audio --profile-out $profileDir
  }
  "profile" {
    if (-not (Test-Path (Join-Path $HOME ".copilot\skills\tts\voices\$Profile"))) {
      throw "Voice profile '$Profile' not found. Build it first with -Takes."
    }
    Ensure-CloneVenv
    Write-Host "Rendering in cloned voice profile '$Profile'..." -ForegroundColor Cyan
    & $venvPy $tts script script.json --outdir public\audio --engine clone --profile $Profile
  }
  "clone" {
    if ($Recording) {
      if (-not (Test-Path $Recording)) { throw "Recording not found: $Recording" }
      New-Item -ItemType Directory -Force -Path (Split-Path $refWav) | Out-Null
      Write-Host "Prepping reference (mono - 24kHz - normalized)..." -ForegroundColor Cyan
      ffmpeg -y -hide_banner -loglevel error -i $Recording -ac 1 -ar 24000 `
        -af "highpass=f=70,loudnorm=I=-18:TP=-1.5:LRA=11" $refWav
    }
    if (-not (Test-Path $refWav)) { throw "No reference.wav. Pass -Recording <file>." }
    Ensure-CloneVenv
    Write-Host "Synthesizing narration in YOUR cloned voice (GPU)..." -ForegroundColor Cyan
    & $venvPy $tts script script.json --outdir public\audio --engine clone --ref $refWav
  }
  default {
    Write-Host "Synthesizing narration with the default neural voice..." -ForegroundColor Cyan
    python $tts script script.json --outdir public\audio --engine edge "--rate=$Rate"
  }
}

Write-Host "Rendering video..." -ForegroundColor Cyan
npm run render

$out = Join-Path $PSScriptRoot "out\batayan-demo.mp4"
$published = $null
if (-not $NoPublish -and (Test-Path $Vault)) {
  Copy-Item $out (Join-Path $Vault "batayan-demo.mp4") -Force
  if ($mode -in @("takes", "profile", "clone")) { Copy-Item $out (Join-Path $Vault "batayan-demo-myvoice.mp4") -Force }
  $published = Join-Path $Vault "batayan-demo.mp4"
}

Write-Host "`n==================== DONE ====================" -ForegroundColor Green
Write-Host ("Voice mode : {0}" -f $mode)
Write-Host ("Video      : {0}" -f $out)
if ($mode -eq "takes") { Write-Host ("Profile    : {0}  (reuse on any script: ./build.ps1 -Profile {1})" -f $profileDir, $ProfileName) }
if ($published) { Write-Host ("Published  : {0}" -f $published) }
Write-Host "=============================================" -ForegroundColor Green
