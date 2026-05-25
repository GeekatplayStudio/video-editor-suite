# Geekatplay Video Editor Suite

Geekatplay Video Editor Suite is a dedicated ComfyUI package for clip loading, timeline-driven prompt work, clip editing, transitions, motion text effects, and direct video export. It keeps the copied LTX and timeline tools in a separate GAP namespace so the suite can live beside the source package without node-id collisions.

## Highlights

- Dedicated `GAP*` node IDs for side-by-side installation with the source node pack.
- Safer branded upload and preview routes for the interactive video loader.
- Practical video-editing nodes for trimming, retiming, looping, ping-pong playback, layered video compositing, transitions, text overlays, freeze holds, speed ramps, audio ducking, muxed export, and LTX timeline safety checks.
- Example workflows that open directly in ComfyUI and give you a starting point for multi-clip edits.

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

## Preview GIFs

### Transition Showcase

![Transition Showcase Preview](docs/assets/transition-showcase.gif)

### Clip Editor Export

![Clip Editor Export Preview](docs/assets/clip-editor-export.gif)

### Full Edit Chain

![Full Edit Chain Preview](docs/assets/full-edit-chain.gif)

## Workflow Starting Points

- If you only want editorial tools, start with the four Geekatplay editor/export demo workflows. They do not need checkpoints, VAEs, or text encoders.
- If you want timeline-driven LTX generation, use the bundled LTX workflows after running `install.bat` so the required models and `ComfyUI-KJNodes` dependency land in the correct places.
- The copied LTX workflows still include in-canvas FAQ notes so you can confirm every expected filename directly inside ComfyUI.
- `GAPDirector` now runs a PromptRelay preflight safety check before large timeline jobs so oversized video or audio attention masks fail early with guidance instead of trying to allocate huge penalty matrices.

## Documentation

- [Getting Started](docs/getting-started.md)
- [Node Reference](docs/node-reference.md)
- [Workflows](docs/workflows.md)
- [Development And Validation](docs/development-and-validation.md)

## Compatibility

- This package is additive and does not replace the original WhatDreamsCost package.
- The bundled LTX workflows expect the LTX-capable nodes plus `ComfyUI-KJNodes`; `install.bat` now installs that node pack automatically.
- The custom guide socket type remains `GUIDE_DATA` for workflow compatibility.
- PromptRelay safety guards now block oversized video/audio attention masks before expensive allocation and report the estimated matrix size in the error.

## Repository

- GitHub: `https://github.com/GeekatplayStudio/video-editor-suite`
