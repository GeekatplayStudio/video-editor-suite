# Getting Started

## Install With `install.bat`

1. Copy `ComfyUI-Geekatplay-VideoEditorSuite` into `ComfyUI/custom_nodes`.
2. Close ComfyUI before the first install so files are not locked.
3. Open the package folder and run `install.bat`.
4. Wait for the script to finish installing Python packages, ffmpeg, and the bundled LTX workflow models.
5. Restart ComfyUI.

If you only want the editor nodes and do not want to download the LTX model pack yet, run:

```bat
install.bat --deps-only
```

If you already installed the suite and only want the model pack later, run:

```bat
install.bat --models-only
```

## What The Installer Adds

`install.bat` installs the Python dependencies listed in `requirements.txt`, provisions ffmpeg when needed, clones `ComfyUI-KJNodes` into `ComfyUI/custom_nodes`, installs its `requirements.txt` when Python is writable, and places these model files into your ComfyUI `models` folder for the bundled LTX workflows:

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

The last path is created automatically as a workflow-safe alias so the copied LTX workflows open without manual LoRA path edits.

The bundled LTX workflows also expect the `VAELoaderKJ` / `Video VAELoader` node from `ComfyUI-KJNodes`. The installer now clones that repo automatically so those workflows do not open with a missing node-pack error.

## First Launch Checklist

1. Start ComfyUI after the installer finishes.
2. Confirm that the `Geekatplay Studio/Video Editor Suite` category appears in the node picker.
3. Load one of the three editor/export demo workflows first if you want to validate the suite without touching AI models.
4. Use the bundled LTX workflows after that if you want the timeline-guided generation path.
5. If you skipped Python package installation because ComfyUI was open, close ComfyUI and rerun `install.bat --deps-only` before opening the LTX workflows.

## First Workflow To Open

If you want to start with a multi-clip edit, load:

- `example_workflows/Geekatplay Video Editor Suite - Transition Showcase.json`

If you want the longer transition -> clip edit -> text FX -> export pipeline, load:

- `example_workflows/Geekatplay Video Editor Suite - Full Edit Chain.json`

If you want to start with a single-clip trim and export workflow, load:

- `example_workflows/Geekatplay Video Editor Suite - Clip Editor Export.json`

These three workflows are the fastest way to confirm that `GAPLoadVideoUI`, `GAPClipEditor`, `GAPTransitionComposer`, `GAPMotionTextFX`, and `GAPVideoExporter` are all wired correctly. They do not require checkpoints, VAEs, or text encoders.

## Recommended First Pass: Clip Editing Only

1. Open `Geekatplay Video Editor Suite - Clip Editor Export.json`.
2. In `GAPLoadVideoUI`, either choose a file already in `ComfyUI/input` or upload one through the node UI.
3. Leave `display_mode` on seconds if you want to trim by time, or switch to frames if you want exact frame counts.
4. Set only the trim you need first. Keep `custom_width` and `custom_height` at `0` if you want the source resolution.
5. In `GAPClipEditor`, start with just `trim_start_frame`, `trim_end_frame`, and `playback_speed`.
6. Add `loop_count`, `reverse`, `ping_pong`, `frame_blend`, and audio fades only after the basic trim behaves correctly.
7. In `GAPVideoExporter`, keep `container=mp4`, `video_codec=auto`, `pixel_format=auto`, and `preset=medium` for the first test render.
8. Queue the workflow and confirm that the output lands under `ComfyUI/output/Geekatplay/VideoEditorSuite`.

## Transition Showcase Walkthrough

1. Open `Geekatplay Video Editor Suite - Transition Showcase.json`.
2. In the left `GAPLoadVideoUI`, upload or choose the first clip.
3. In the right `GAPLoadVideoUI`, upload or choose the second clip.
4. Keep both loaders on the same `frame_rate` so the transition and audio timing stay predictable.
5. Tune `GAPTransitionComposer` for `transition_type`, `transition_frames`, and any hold frames before or after the transition.
6. Use `resize_mode` to decide which source clip controls the final frame size inside the transition.
7. Tune `GAPMotionTextFX` only after the transition feels correct. Start with overlay text first, then add freeze or speed ramps.
8. Queue the workflow to export a preview file into `ComfyUI/output/Geekatplay/VideoEditorSuite`.

## Clip Editor Export Walkthrough

1. Open `Geekatplay Video Editor Suite - Clip Editor Export.json`.
2. Load one source clip with `GAPLoadVideoUI`.
3. Adjust `GAPClipEditor` for trim range, playback speed, looping, ping-pong playback, frame blending, audio gain, and fades.
4. Keep `trim_end_frame=0` if you want to use the rest of the clip after the start frame.
5. Use `frame_blend` only when `playback_speed` is not `1.0`; otherwise it has no visible effect.
6. Queue the workflow to export the edited clip.

## Full Edit Chain Walkthrough

1. Open `Geekatplay Video Editor Suite - Full Edit Chain.json`.
2. Load the first and second source clips with the two `GAPLoadVideoUI` nodes.
3. Tune `GAPTransitionComposer` for the transition style and overlap.
4. Tune `GAPClipEditor` for trim, retime, loop, or fade behavior on the combined clip.
5. Tune `GAPMotionTextFX` for text overlays, freeze inserts, and speed ramps.
6. Tune `GAPVideoExporter` last, because container and codec changes do not affect editorial timing.
7. Queue the workflow to export the final composite clip.

## LTX Workflow Quick Start

1. Run `install.bat` first so the bundled LTX model pack lands in the correct folders.
2. Open one of the LTX workflows from `example_workflows/`.
3. Read the in-canvas FAQ note inside that workflow before queueing anything.
4. Confirm that the loader nodes inside the workflow are pointed at the downloaded checkpoint, text encoders, VAEs, and upscalers.
5. If you swap in your own files, keep them in the same ComfyUI model folder type so the workflow structure stays valid.

## Notes

- `GAPLoadVideoUI` extracts both `IMAGE` and `AUDIO` outputs, so you can keep audio aligned through editing and export.
- `GAPVideoExporter` writes to the standard ComfyUI output folder using `folder_paths.get_save_image_path`.
- `GAPLoadAudioUI` falls back to silence instead of crashing if an audio file is missing or fails to decode.
- For large videos, work on trimmed sections first and then expand your render range once the edit behaves the way you want.
