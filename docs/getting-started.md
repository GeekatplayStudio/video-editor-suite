# Getting Started

## Install

1. Copy `ComfyUI-Geekatplay-VideoEditorSuite` into `ComfyUI/custom_nodes`.
2. Install the Python dependencies from `requirements.txt`, or let ComfyUI Manager install from `pyproject.toml`.
3. Restart ComfyUI.

## First Workflow To Open

If you want to start with a multi-clip edit, load:

- `example_workflows/Geekatplay Video Editor Suite - Transition Showcase.json`

If you want to start with a single-clip trim and export workflow, load:

- `example_workflows/Geekatplay Video Editor Suite - Clip Editor Export.json`

## Transition Showcase Walkthrough

1. Open `Geekatplay Video Editor Suite - Transition Showcase.json`.
2. In the left `GAPLoadVideoUI`, upload or choose the first clip.
3. In the right `GAPLoadVideoUI`, upload or choose the second clip.
4. Tune `GAPTransitionComposer` for the transition type, transition length, and hold frames.
5. Tune `GAPMotionTextFX` for overlay text, freeze inserts, or speed ramps.
6. Queue the workflow to export a preview file into `ComfyUI/output/Geekatplay/VideoEditorSuite`.

## Clip Editor Export Walkthrough

1. Open `Geekatplay Video Editor Suite - Clip Editor Export.json`.
2. Load one source clip with `GAPLoadVideoUI`.
3. Adjust `GAPClipEditor` for trim range, playback speed, looping, ping-pong playback, frame blending, and fades.
4. Queue the workflow to export the edited clip.

## Notes

- `GAPLoadVideoUI` extracts both `IMAGE` and `AUDIO` outputs, so you can keep audio aligned through editing and export.
- `GAPVideoExporter` writes to the standard ComfyUI output folder using `folder_paths.get_save_image_path`.
- For large videos, work on trimmed sections first and then expand your render range once the edit behaves the way you want.
