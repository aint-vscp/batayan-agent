# 🎬 Batayan demo video — fully automated

This folder renders the Batayan demo video **end to end with no manual recording**:
a neural **voiceover** (TTS) drives a **Remotion** composition whose scenes are
auto-synced to the narration.

```
script.json            # the narration (text + on-screen captions per beat)
public/audio/          # generated: per-beat MP3 + timeline.json (durations/frames)
src/                   # the Remotion composition (intro · 3 beats · outro)
out/batayan-demo.mp4   # the rendered 1080p video (with audio)
build.ps1              # one command: narrate -> render
```

## One command

The **best fidelity** is to read each beat yourself (it's literally your voice),
which *also* builds a reusable cloned voice profile for future scripts:

```powershell
# 1) Record one clip per beat into a folder, named:
#    Intro.m4a · Beat 1.m4a · Beat 2.m4a · Beat 3.m4a · Outro.m4a
#    (read the lines in voice/recording-script.md)

# 2) Build with your REAL voice + auto-build the reusable "vash" clone profile:
./build.ps1 -Takes "C:\Users\Vash\Documents\Sound Recordings"
```

Other modes:

```powershell
# Reuse your cloned voice on ANY future/edited script (no re-recording):
./build.ps1 -Profile vash

# Clone from a single raw recording:
./build.ps1 -Recording "C:\path\Recording.m4a"      # or:  -Recording auto

# Default free neural voice (no GPU, no recording):
./build.ps1 -Default                                 # or just ./build.ps1
```

Output: `out/batayan-demo.mp4` (1920×1080, H.264 + AAC) plus a copy published to the
submission folder. The clone toolchain installs itself on first use (isolated venv,
reuses your global CUDA PyTorch).

### Reuse your voice on any hackathon
- `-Takes` saves cleaned reference clips to `~/.copilot/skills/tts/voices/vash/`.
- For a different project, copy this `video/` folder, edit `script.json`, and run
  `./build.ps1 -Profile vash` — every new line renders in your cloned voice.
- Build other profiles by recording into a folder and running `-Takes ... -ProfileName <name>`.

## How it works

1. **TTS** — the reusable `tts` skill (`~/.copilot/skills/tts`) synthesizes each
   segment in `script.json` into `public/audio/<id>.mp3` and writes
   `public/audio/timeline.json` with each segment's measured **duration** and
   **frame count** (at 30 fps).
   - Engine `edge` (default): free Microsoft neural voices, no GPU.
   - Engine `clone`: zero-shot voice cloning (XTTS-v2) from `-Ref voice.wav`,
     runs on your GPU.
2. **Remotion** — `src/Root.tsx` reads `timeline.json` and lays each beat in a
   `<Sequence>` whose duration equals the narration length, so visuals always
   stay in sync. `npm run render` produces the MP4.

## Make it sound like you

1. Record **30–60 s** of clear, natural speech (quiet room, consistent volume).
   Save as `voice/reference.wav`.
2. `./build.ps1 -Ref voice\reference.wav -Install`

Only clone a voice you have the right to use (your own, or with explicit consent).
The XTTS-v2 model is non-commercial; for commercial use, swap to a licensed voice.

## Edit the script or visuals

- Change wording/captions → edit `script.json`, rerun `build.ps1` (only changed
  lines are re-synthesized — the TTS skill is cached).
- Change what each beat shows → edit `src/scenes.ts`.
- Preview interactively → `npm run dev` (Remotion Studio).
