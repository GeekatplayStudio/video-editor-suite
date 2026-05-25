# Geekatplay Video Editor Suite

Geekatplay Video Editor Suite is a dedicated ComfyUI package for clip loading, timeline-driven prompt work, clip editing, transitions, motion text effects, and direct video export. It keeps the copied LTX and timeline tools in a separate GAP namespace so the suite can live beside the source package without node-id collisions.

## Highlights

- Dedicated `GAP*` node IDs for side-by-side installation with the source node pack.
- Safer branded upload and preview routes for the interactive video loader.
- Practical video-editing nodes for trimming, retiming, looping, ping-pong playback, transitions, text overlays, freeze holds, speed ramps, and muxed export.
- Example workflows that open directly in ComfyUI and give you a starting point for multi-clip edits.

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
- `GAPTransitionComposer`: crossfades, wipes, slides, hold frames, and audio crossfades between clips.
- `GAPMotionTextFX`: text overlays, freeze inserts, and speed ramps.
- `GAPVideoExporter`: container, codec, preset, bitrate, and audio mux controls.

## Example Workflows

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

## Quick Start

1. Place `ComfyUI-Geekatplay-VideoEditorSuite` inside `ComfyUI/custom_nodes`.
2. Install dependencies from `requirements.txt` or let ComfyUI Manager process `pyproject.toml`.
3. Restart ComfyUI.
4. Load one of the example workflows from the `example_workflows` folder.
5. Replace the empty `GAPLoadVideoUI` inputs with your own source clips and queue the workflow.

## Documentation

- [Getting Started](docs/getting-started.md)
- [Node Reference](docs/node-reference.md)
- [Workflows](docs/workflows.md)
- [Development And Validation](docs/development-and-validation.md)

## Compatibility

- This package is additive and does not replace the original WhatDreamsCost package.
- The copied LTX and timeline workflows still expect the broader ComfyUI and LTX ecosystem used by the source package.
- The custom guide socket type remains `GUIDE_DATA` for workflow compatibility.

## Repository

- GitHub: `https://github.com/GeekatplayStudio/video-editor-suite`
