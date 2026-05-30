# Geekatplay Video Editor Suite

Geekatplay Video Editor Suite is a dedicated ComfyUI package for clip loading, timeline-driven prompt work, clip editing, transitions, motion text effects, and direct video export. It keeps the copied LTX and timeline tools in a separate GAP namespace so the suite can live beside the source package without node-id collisions.

## Highlights

- Dedicated `GAP*` node IDs for side-by-side installation with the source node pack.
- Safer branded upload and preview routes for the interactive video loader.
- Practical video-editing nodes for trimming, retiming, looping, ping-pong playback, layered video compositing, transitions, text overlays, freeze holds, speed ramps, audio ducking, muxed export, and LTX timeline safety checks.
- Example workflows that open directly in ComfyUI and give you a starting point for multi-clip edits.

## Why This Fork Is Better

- It stays additive. You can install it beside the original pack without node-ID collisions because every copied node is published under the `GAP*` namespace.
- It goes beyond the original LTX utilities by bundling a full editorial finishing stack: `GAPClipEditor`, `GAPLayerComposer`, `GAPTransitionComposer`, `GAPMotionTextFX`, and `GAPVideoExporter`.
- It is harder to break in day-to-day use. `GAPLoadVideoUI` uses safer upload and preview handling, `GAPLoadAudioUI` falls back to silence instead of crashing, and `GAPDirector` now preflights PromptRelay memory budgets before expensive LTX jobs start.
- It ships with workflow-ready installation. `install.bat` handles dependencies, ffmpeg setup, `ComfyUI-KJNodes`, and the LTX 2.3 model layout used by the bundled workflows.
- It keeps workflow compatibility in mind. The copied LTX workflows use the same `GUIDE_DATA` socket type, include in-canvas FAQ notes, and now track the local package metadata correctly.

## What This Fork Added

- A dedicated editorial toolchain for trimming, transitions, overlays, titles, freeze holds, speed ramps, and muxed export.
- Safer media-loading routes and more resilient workflow behavior around missing or invalid source files.
- PromptRelay budget guards for large LTX 2.3 timeline jobs, including early matrix-size estimates for video and audio attention masks.
- A one-click installer path that sets up the bundled LTX 2.3 workflows instead of leaving model and dependency wiring to the user.
- Refreshed bundled workflows and docs so the local package identity, setup notes, and workflow metadata stay in sync.

## README Maintenance Rule

- Every new node, bundled workflow, or user-facing LTX feature added to this fork should also be added to this README.
- When a workflow gains a new mode, dependency, or setup requirement, update both this README and the in-canvas workflow FAQ note in the same change.
- If a new feature is experimental or depends on an external node pack, label it clearly here instead of implying that it is built in.

## One-Click Install

1. Place `ComfyUI-Geekatplay-VideoEditorSuite` inside `ComfyUI/custom_nodes`.
2. Double-click `install.bat` from the package folder.
3. Wait for dependency installation, ffmpeg setup, and model downloads to finish.
4. Restart ComfyUI.

### What `install.bat` does

- Installs the Python requirements from `requirements.txt` into your ComfyUI Python environment.
- Downloads an ffmpeg build into the ComfyUI root if ffmpeg is not already available.
- Sets `VHS_FORCE_FFMPEG_PATH` and `IMAGEIO_FFMPEG_EXE` for future runs.
- Downloads the bundled LTX workflow model set into `ComfyUI/models`.
- Creates the workflow-compatible LoRA alias at `models/loras/ltx2/ltx-2.3-22b-distilled-lora-dynamic_fro09_avg_rank_105_bf16.safetensors`.

### Optional Installer Modes

- `install.bat --deps-only`
  Install only Python requirements.
- `install.bat --models-only`
  Download only the bundled LTX workflow models.
- `install.bat --skip-ffmpeg`
  Skip ffmpeg setup if you already manage it yourself.
- `install.bat --no-pause`
  Useful when running from an existing terminal.

## Node Groups

### Timeline And Guide Tools

- `GAPDirector`: visual prompt timeline editor.
- `GAPDirectorGuide`: guide-image application node for timeline data.
- `GAPSequencer`: guide-frame sequencing across a latent timeline.
- `GAPKeyframer`: in-place frame replacement for keyframe workflows.
- `GAPMultiImageLoader`: gallery-driven multi-image loading.

### Media Loading And Utility

- `GAPLoadVideoUI`: video trimming, preview, crop, resize, and audio extraction.
- `GAPLoadAudioUI`: audio trimming with interactive controls.
- `GAPSpeechLengthCalculator`: quote-aware speech timing helper.

### Editing And Export

- `GAPClipEditor`: trim, reverse, loop, ping-pong, retime, frame blend, fades, and audio gain.
- `GAPLayerComposer`: timed video-on-video overlays with blend modes, fades, and audio ducking.
- `GAPTransitionComposer`: crossfades, wipes, slides, hold frames, and audio crossfades between clips.
- `GAPMotionTextFX`: text overlays, freeze inserts, and speed ramps.
- `GAPVideoExporter`: container, codec, preset, bitrate, and audio mux controls.

## Example Workflows

- `example_workflows/Geekatplay Video Editor Suite - Overlay Showcase.json`
  A base clip feeds `GAPLayerComposer`, then `GAPMotionTextFX`, then `GAPVideoExporter` for picture-in-picture and overlay-style edits.
- `example_workflows/Geekatplay Video Editor Suite - Transition Showcase.json`
  Two loaded clips feed `GAPTransitionComposer`, then `GAPMotionTextFX`, then `GAPVideoExporter`.
- `example_workflows/Geekatplay Video Editor Suite - Clip Editor Export.json`
  A single loaded clip feeds `GAPClipEditor` and then `GAPVideoExporter` for trim, retime, loop, and fade workflows.
- `example_workflows/Geekatplay Video Editor Suite - Full Edit Chain.json`
  Two source clips feed `GAPTransitionComposer`, then `GAPClipEditor`, then `GAPMotionTextFX`, then `GAPVideoExporter` for a longer editorial stack.
- `example_workflows/Geekatplay Video Editor Suite - LTX 2.3 Director Lab.json`
  A compatibility-safe Director hub built from the fully expanded `LTX Director Example Workflow (Fixed)` canvas, with an in-canvas note that points you to the companion first/last-frame, custom-audio, and lip-sync workflows.
- `example_workflows/Geekatplay Video Editor Suite - LipSync GAP Bridge.json`
  An optional post-generation bridge workflow for exact mouth-sync work when `GeekatplayStudio/ComfyUI-LipSync-GAP` is installed.

## Preview GIFs

### Transition Showcase

![Transition Showcase Preview](docs/assets/transition-showcase.gif)

### Clip Editor Export

![Clip Editor Export Preview](docs/assets/clip-editor-export.gif)

### Full Edit Chain

![Full Edit Chain Preview](docs/assets/full-edit-chain.gif)

## Workflow Starting Points

- If you only want editorial tools, start with the four Geekatplay editor/export demo workflows. They do not need checkpoints, VAEs, or text encoders.
- If you want the compatibility-safe bundled LTX entry point, start with `Geekatplay Video Editor Suite - LTX 2.3 Director Lab.json`. It keeps the full expanded Director canvas and points to the companion workflows for the other modes.
- If you want timeline-driven LTX generation on a smaller canvas, use the other bundled LTX workflows after running `install.bat` so the required models and `ComfyUI-KJNodes` dependency land in the correct places.
- The copied LTX workflows still include in-canvas FAQ notes so you can confirm every expected filename directly inside ComfyUI.
- `GAPDirector` now runs a PromptRelay preflight safety check before large timeline jobs so oversized video or audio attention masks fail early with guidance instead of trying to allocate huge penalty matrices.

## LTX 2.3 Coverage

The current fork already exposes most of the practical LTX 2.3 workflow surface:

- Text to video:
  Use `Geekatplay Video Editor Suite - LTX 2.3 Director Lab.json` or `GAPDirector` directly for timeline-driven prompt changes, then fall back to the smaller bundled LTX examples when you want a narrower canvas.
- Image to video:
  Use the companion `LTX I2V First Last Frame` workflows, or `GAPDirector` with guide-image timeline segments or `GAPSequencer` plus `GAPMultiImageLoader` for first-frame, last-frame, and multi-keyframe guide workflows.
- Video to video:
  Use `GAPLoadVideoUI` to trim a guide clip and feed its `IMAGE` output into the guide-driven LTX path, typically through `GAPSequencer` in the bundled first/last-frame workflows.
- First/last frame and sparse keyframes:
  Use the bundled `LTX I2V First Last Frame` workflows, or build your own with `GAPSequencer` or `GAPKeyframer`.
- Custom audio and audio-driven shots:
  Use `GAPLoadAudioUI` with the bundled custom-audio LTX workflow, or use the `combined_audio` / `audio_latent` outputs from `GAPDirector` when the workflow uses the LTX audio path.
- Editorial finishing after generation:
  Run the generated clip through `GAPClipEditor`, `GAPTransitionComposer`, `GAPLayerComposer`, `GAPMotionTextFX`, and `GAPVideoExporter` instead of rebuilding finishing steps in separate tools.
- Exact lip-sync post pass:
  Use `Geekatplay Video Editor Suite - LipSync GAP Bridge.json` after installing `GeekatplayStudio/ComfyUI-LipSync-GAP` when you need a dedicated mouth-sync stage instead of the lighter audio-driven LTX path.

## Lip-Sync And Stability Notes

- This fork is audio-ready by itself, and now includes a bundled bridge workflow for the org's dedicated lip-sync add-on: `GeekatplayStudio/ComfyUI-LipSync-GAP`.
- The existing LTX workflows support custom audio, audio latents, and audio-aligned export, which is the correct base for audio-driven shots before a stricter mouth-sync pass.
- If you need strict mouth-shape matching, install `ComfyUI-LipSync-GAP` and use `Geekatplay Video Editor Suite - LipSync GAP Bridge.json`. That exact solver is still an optional add-on rather than a built-in node set in this repo.
- The stability work in this fork is focused on predictable workflow opening, safer media I/O, resilient editorial nodes, and early PromptRelay memory checks for long LTX jobs.

## Optional Lip-Sync Add-On

- Recommended add-on: `https://github.com/GeekatplayStudio/ComfyUI-LipSync-GAP`
- Install it under `ComfyUI/custom_nodes/ComfyUI-LipSync-GAP` and run its `install.bat`.
- The bridge workflow expects the LipSync GAP add-on to provide `GapLipSyncModelLoader` and `GapLipSyncSampler`, plus the `latentsync_unet.pt`, Whisper checkpoint, and Mediapipe face landmarker assets described in that repo.

## Documentation

- [Getting Started](docs/getting-started.md)
- [Node Reference](docs/node-reference.md)
- [Workflows](docs/workflows.md)
- [Development And Validation](docs/development-and-validation.md)

## Compatibility

- This package is additive and does not replace the original WhatDreamsCost package.
- The bundled LTX workflows expect the LTX-capable nodes plus `ComfyUI-KJNodes`; `install.bat` now installs that node pack automatically.
- The custom guide socket type remains `GUIDE_DATA` for workflow compatibility.
- PromptRelay safety guards now block oversized video and scaled-audio attention masks before expensive allocation and report the estimated matrix size in the error.

## Repository

- GitHub: `https://github.com/GeekatplayStudio/video-editor-suite`
