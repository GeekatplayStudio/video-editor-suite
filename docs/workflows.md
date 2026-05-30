# Workflows

## Included Example Files

### `Geekatplay Video Editor Suite - Overlay Showcase.json`

Purpose:
Two source clips are loaded, one is layered on top of the other with `GAPLayerComposer`, titles are added with `GAPMotionTextFX`, and the result is exported with `GAPVideoExporter`.

Use this workflow when:
- You want picture-in-picture, commentary cam, logo bug, or reaction-overlay style edits.
- You want to test overlay fade timing, audio ducking, and title placement in one file.
- You want a direct reference for the recommended finishing chain: `GAPLayerComposer -> GAPMotionTextFX -> GAPVideoExporter`.

Requirements:
- No extra checkpoints, VAEs, or text encoders are required.
- Source clips can come from `ComfyUI/input` or from direct upload inside `GAPLoadVideoUI`.

### `Geekatplay Video Editor Suite - Transition Showcase.json`

![Transition Showcase Preview](assets/transition-showcase.gif)

Purpose:
Two source clips are loaded, transitioned together, passed through text and motion effects, and exported.

Use this workflow when:
- You want to join two clips with a visible transition.
- You want a quick place to test `GAPTransitionComposer` and `GAPMotionTextFX` together.
- You want a reference export chain that preserves audio.

Requirements:
- No extra checkpoints, VAEs, or text encoders are required.
- Source clips can come from `ComfyUI/input` or from direct upload inside `GAPLoadVideoUI`.

### `Geekatplay Video Editor Suite - Clip Editor Export.json`

![Clip Editor Export Preview](assets/clip-editor-export.gif)

Purpose:
One source clip is loaded, edited with `GAPClipEditor`, and exported with `GAPVideoExporter`.

Use this workflow when:
- You want to trim or retime a single clip.
- You want to test loop and ping-pong playback.
- You want a quick export path without the transition stack.

Requirements:
- No extra checkpoints, VAEs, or text encoders are required.

### `Geekatplay Video Editor Suite - Full Edit Chain.json`

![Full Edit Chain Preview](assets/full-edit-chain.gif)

Purpose:
Two source clips are transitioned together, refined with `GAPClipEditor`, styled with `GAPMotionTextFX`, and exported with `GAPVideoExporter`.

Use this workflow when:
- You want one example that demonstrates the longer editorial chain.
- You want to trim or retime after the transition instead of before it.
- You want a ready-made reference for multi-step clip finishing inside the suite.

Requirements:
- No extra checkpoints, VAEs, or text encoders are required.

### `Geekatplay Video Editor Suite - LTX 2.3 Director Lab.json`

Purpose:
Keeps the fully expanded `LTX Director Example Workflow (Fixed)` canvas under a Geekatplay entry-point filename, then adds a hub note that points to the companion first/last-frame, custom-audio, and lip-sync workflows.

Use this workflow when:
- You want the expanded Director workflow without the newer UUID-style core wrapper nodes used by the subgraph-based canvases.
- You want a compatibility-safe starting point for text-to-video and timeline prompt work.
- You want an in-canvas map that tells you which companion workflow to open next for first/last-frame, custom-audio, or lip-sync work.

Requirements:
- Run `install.bat` first so the bundled LTX model pack and `ComfyUI-KJNodes` dependency are present.
- This workflow intentionally stays on the expanded Director canvas instead of embedding the newer subgraph-based first/last-frame lane.

### `Geekatplay Video Editor Suite - LipSync GAP Bridge.json`

Purpose:
Loads a talking-head source clip and target audio, runs them through `GapLipSyncModelLoader` plus `GapLipSyncSampler`, and exports the result with `GAPVideoExporter`.

Use this workflow when:
- You already have a generated or edited source clip and now need stricter mouth-shape matching than the lighter audio-driven LTX path provides.
- You want a Geekatplay-native bridge that uses `GAPLoadVideoUI`, `GAPLoadAudioUI`, and `GAPVideoExporter` instead of depending on VideoHelperSuite nodes.

Requirements:
- Install `GeekatplayStudio/ComfyUI-LipSync-GAP` separately under `ComfyUI/custom_nodes`.
- Run the LipSync GAP `install.bat` so the `GapLipSyncModelLoader` and `GapLipSyncSampler` nodes load and the `latentsync` model assets are present.

## Bundled LTX Workflow Model Pack

Running `install.bat` installs the `ComfyUI-KJNodes` dependency plus the model set used by the bundled LTX workflows into the correct ComfyUI folders:

- `models/checkpoints/ltx-2.3-22b-dev-fp8.safetensors`
- `models/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors`
- `models/text_encoders/ltx-2.3_text_projection_bf16.safetensors`
- `models/vae/LTX23_audio_vae_bf16.safetensors`
- `models/vae/LTX23_video_vae_bf16.safetensors`
- `models/vae/taeltx2_3.safetensors`
- `models/latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.1.safetensors`
- `models/latent_upscale_models/ltx-2.3-spatial-upscaler-x1.5-1.0.safetensors`
- `models/loras/ltx-2.3-22b-distilled-lora-384.safetensors`
- `models/loras/ltx2/ltx-2.3-22b-distilled-lora-dynamic_fro09_avg_rank_105_bf16.safetensors`

That final `loras/ltx2/...` file is created as a workflow-safe alias so the copied workflow JSON files match the files on disk without manual edits.

The copied LTX workflows also use `VAELoaderKJ` from `ComfyUI-KJNodes` and will report a missing node pack if that repo is not present. The installer now clones `https://github.com/kijai/ComfyUI-KJNodes.git` automatically during the LTX setup path.

The timeline-driven LTX nodes now also run a PromptRelay safety preflight. If an edit would allocate an oversized video or audio attention mask, the workflow stops early with a matrix-size estimate and tuning guidance instead of failing later after heavy model staging.

## LTX 2.3 Mode Guide

Use the bundled LTX workflows based on the job you are actually trying to run:

- Text to video:
	Start with `Geekatplay Video Editor Suite - LTX 2.3 Director Lab.json` when you want the compatibility-safe Director hub, or `LTX Director Example Workflow (Fixed).json` when you want the original fixed canvas directly.
- Image to video:
	Use `LTX I2V First Last Frame 2 Stage Workflow v6.json` or `LTX I2V First Last Frame 3 Stage Workflow v6.json` when one or more guide frames should shape the shot.
- First frame, last frame, or sparse keyframes:
	Use the same `LTX I2V First Last Frame` workflows and drive guide placement with `GAPSequencer`.
- Custom audio or audio-driven shots:
	Use `LTX I2V FFLF Custom Audio Workflow - SUPPORTS LATEST COMFYUI VERSION - V3.json` when you want a bundled example that already exposes `GAPLoadAudioUI` and the custom-audio switch.
- Exact lip-sync post pass:
	Use `Geekatplay Video Editor Suite - LipSync GAP Bridge.json` after installing `GeekatplayStudio/ComfyUI-LipSync-GAP`.
- Editorial finishing after generation:
	Move the generated clip into the four Geekatplay editor/export workflows when you want trims, overlays, transitions, captions, or export tuning.

## Video-To-Video Recipe

There is no separate bundled file named "video to video," but the existing nodes already cover that guide-driven path:

- Load a source clip with `GAPLoadVideoUI`.
- Trim and crop it there so the guide clip length matches the motion reference you want.
- Feed the node's `IMAGE` output into the `multi_input` side of `GAPSequencer` in one of the bundled guide-based LTX workflows.
- Use `insert_mode`, frame placement, and strength controls to decide whether the source clip acts like dense motion guidance or sparse guide frames.

This is the stable way to do V2V-style motion transfer in this fork without pretending there is a separate solver hidden elsewhere.

## Lip-Sync Scope

The bundled workflows are audio-ready, not a full phoneme lip-sync package:

- `GAPLoadAudioUI`, `combined_audio`, and the LTX audio latent path give you a stable base for audio-driven shots.
- That is enough for narration-driven timing and for pipelines that need audio carried cleanly through generation and export.
- If you need strict mouth-shape tracking to speech, install `GeekatplayStudio/ComfyUI-LipSync-GAP` and use `Geekatplay Video Editor Suite - LipSync GAP Bridge.json` as the post-generation stage.

## Existing Legacy-Compatible Workflows

The package also keeps the copied LTX workflows from the original suite under `example_workflows/`. Those files were bulk-updated to GAP node IDs and remain useful for timeline-driven LTX generation.

Each LTX workflow now includes in-canvas FAQ notes with the exact filenames and destination folders used by that workflow family:
- `models/checkpoints/`
- `models/text_encoders/`
- `models/vae/`
- `models/loras/` or `models/loras/ltx2/`
- `models/latent_upscale_models/`

Use `install.bat` when you want those folders populated automatically and the required `ComfyUI-KJNodes` pack installed alongside them.

The three Geekatplay editor/export demo workflows do not need extra AI model downloads. They operate on source clips loaded from `ComfyUI/input` or uploaded directly through `GAPLoadVideoUI`.
