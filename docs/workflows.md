# Workflows

## Included Example Files

### `Geekatplay Video Editor Suite - Transition Showcase.json`

![Transition Showcase Preview](assets/transition-showcase.gif)

Purpose:
Two source clips are loaded, transitioned together, passed through text and motion effects, and exported.

Use this workflow when:
- You want to join two clips with a visible transition.
- You want a quick place to test `GAPTransitionComposer` and `GAPMotionTextFX` together.
- You want a reference export chain that preserves audio.

### `Geekatplay Video Editor Suite - Clip Editor Export.json`

![Clip Editor Export Preview](assets/clip-editor-export.gif)

Purpose:
One source clip is loaded, edited with `GAPClipEditor`, and exported with `GAPVideoExporter`.

Use this workflow when:
- You want to trim or retime a single clip.
- You want to test loop and ping-pong playback.
- You want a quick export path without the transition stack.

### `Geekatplay Video Editor Suite - Full Edit Chain.json`

![Full Edit Chain Preview](assets/full-edit-chain.gif)

Purpose:
Two source clips are transitioned together, refined with `GAPClipEditor`, styled with `GAPMotionTextFX`, and exported with `GAPVideoExporter`.

Use this workflow when:
- You want one example that demonstrates the longer editorial chain.
- You want to trim or retime after the transition instead of before it.
- You want a ready-made reference for multi-step clip finishing inside the suite.

## Existing Legacy-Compatible Workflows

The package also keeps the copied LTX workflows from the original suite under `example_workflows/`. Those files were bulk-updated to GAP node IDs and remain useful for timeline-driven LTX generation.
