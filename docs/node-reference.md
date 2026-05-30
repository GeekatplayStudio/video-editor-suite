# Node Reference

## Timeline And Guide Nodes

### `GAPDirector`

Visual prompt timeline editor for LTX workflows.

Use it when:
- You want to build prompt segments visually instead of typing comma-separated prompt blocks by hand.
- You want guide-image timing, guide strengths, and audio timing to stay aligned to one timeline.
- You want a single node to output `positive`, `video_latent`, `audio_latent`, `guide_data`, `frame_rate`, and `combined_audio`.

Important controls:
- `model` and `clip` are the core generation inputs.
- `audio_vae` is optional and only matters when the workflow uses audio latents.
- `optional_latent` lets you override the auto-generated latent.
- `global_prompt` is the persistent context that should remain true across the whole shot.
- `duration_frames` controls the visual scale of the editor UI. The actual latent length still comes from the latent path in the workflow.
- `timeline_data`, `local_prompts`, `segment_lengths`, and `guide_strength` are auto-managed by the UI and should normally be left alone.
- `custom_width`, `custom_height`, `resize_method`, `divisible_by`, and `img_compression` control how image segments are prepared before being injected as guides.

Safety behavior:
- `GAPDirector` now runs a PromptRelay preflight budget check before generation starts.
- Oversized video or scaled-audio attention masks are blocked early with an error that reports the predicted matrix size and suggests reducing duration, lowering guide resolution, shortening the shot, or disconnecting the audio VAE when audio latents are not needed.
- Large but still allowed jobs emit warnings in the ComfyUI log before mask allocation.

How to use it:
- Connect the model, CLIP, and any LTX latent path the workflow expects.
- Build segments directly inside the timeline UI.
- Use `global_prompt` for character, scene, or style anchors that must stay consistent.
- Use the timeline blocks for local prompt changes, insert points, and guide strength changes.
- Feed `guide_data` into `GAPDirectorGuide` when the workflow needs guide frames applied to a latent.

### `GAPSmartTimelinePlanner`

Compiles a mixed-mode shot manifest into a normalized plan before you wire the actual render lanes.

Use it when:
- You want one planning surface that mixes text-to-video, image-to-video, video-to-video, and first/last-frame shots.
- You want durations, frame ranges, prompts, seeds, and asset references normalized before you build a larger workflow.
- You want to know whether the whole manifest can collapse into `GAPDirector` today or whether some segments still need dedicated v2v or first/last-frame branches.

Important controls:
- `timeline_json` is the source manifest. It accepts either a top-level object with `defaults` and `segments`, or a raw array of segment objects.
- `frame_rate`, `default_width`, `default_height`, and `default_segment_seconds` supply fallback values when the JSON omits them.
- `strict_validation` switches between note-only planning and hard validation failures.
- `timeline_json_input` lets another node feed the manifest in as a string.

Outputs:
- `timeline_plan` is the normalized JSON manifest with frame ranges, execution lanes, validation notes per segment, plus grouped `lane_exports` and a flat `render_queue` for downstream render lanes.
- `director_timeline_data`, `local_prompts`, `segment_lengths`, and `guide_strength` are only populated when every segment is compatible with `GAPDirector` today.
- `summary` is a human-readable routing report intended for quick debugging inside ComfyUI.

Behavior note:
- `t2v` and `i2v` segments can be compiled into `GAPDirector`-compatible timeline data.
- `v2v` and `fflf` segments are planned and validated here, but this first version does not render them internally; they still need their own guide-video or first/last-frame lane downstream.
- The normalized plan also includes `assembly_slot` per segment plus top-level `assembly_export_ready` metadata for `GAPSmartTimelineAssembler`.
- `timeline_plan.lane_exports.director_shots`, `guide_video_shots`, and `first_last_frame_shots` are standalone shot contracts intended to be rendered individually and then sent into `GAPSmartTimelineAssembler`.

Minimal manifest example:

```json
{
	"defaults": {
		"width": 768,
		"height": 512,
		"duration_seconds": 2.0,
		"guide_strength": 0.85
	},
	"segments": [
		{
			"mode": "t2v",
			"prompt": "wide establishing shot of a rainy neon street"
		},
		{
			"mode": "i2v",
			"prompt": "camera pushes into the storefront",
			"image": "reference_storefront.png"
		},
		{
			"mode": "v2v",
			"prompt": "keep the dancer silhouette and amplify stage lighting",
			"video": "guide_dancer.mp4"
		},
		{
			"mode": "fflf",
			"prompt": "sunrise over the canyon",
			"first_frame": "canyon_start.png",
			"last_frame": "canyon_end.png"
		}
	]
}
```

### `GAPSmartTimelineAssembler`

Stitches pre-rendered smart-timeline segment clips back into one editorial clip using the normalized planner manifest.

Use it when:
- You already rendered each segment through its own t2v, i2v, v2v, or first/last-frame lane.
- You want one node to place those clips in planned order and preserve or trim any intentional gaps.
- You want a lightweight assembly stage before you move into transitions, overlays, or export.

Important controls:
- `timeline_plan` should come from `GAPSmartTimelinePlanner` `timeline_plan` whenever possible.
- `resize_mode` decides whether all assembled clips should match the planner defaults or the first connected segment clip.
- `gap_policy` decides whether planned gaps are removed, filled with black frames, or filled by holding the previous frame.
- `segment_fit` decides how clips are stretched to the planned segment length when the rendered clip is shorter than expected.
- `images_1` / `audio_1` through `images_12` / `audio_12` are ordered assembly slots. Slot `n` corresponds to planner segment `assembly_slot=n`.

Behavior note:
- This node assembles clips sequentially in planner order. It does not layer or overlap segments; for overlapping editorial effects, move the stitched output into `GAPLayerComposer` or `GAPTransitionComposer` afterward.
- Audio gaps are filled with silence even when `gap_policy` holds the previous frame visually.
- The current node supports up to 12 segments per assembly pass.

### `GAPSmartTimelineSupervisor`

Checks a smart-timeline plan against the currently connected rendered segment clips so you can see which assembly slots are still missing.

Use it when:
- You already have `timeline_plan` from `GAPSmartTimelinePlanner` and want a quick readiness check before assembly.
- You want to know which `images_n` slots are still blocking `GAPSmartTimelineAssembler`.
- You want audio coverage reported separately, without treating missing audio as a hard block.

Important controls:
- `timeline_plan` or `timeline_plan_input` should come from `GAPSmartTimelinePlanner`.
- `images_1` / `audio_1` through `images_12` / `audio_12` are checked against planner `assembly_slot` values.

Outputs:
- `timeline_plan` passes the manifest through unchanged so it can continue into `GAPSmartTimelineAssembler`.
- `summary` lists each slot, whether image and audio clips are connected, and whether assembly is ready.
- `missing_image_slots` and `missing_audio_slots` are comma-separated slot lists for quick debugging.
- `next_missing_slot` points at the first missing image slot.
- `ready_to_assemble` is `1` only when all required image slots are connected and the planner says assembly is export-ready.
- `image_completion_ratio` reports how many planned image slots are already filled.

### `GAPDirectorGuide`

Applies `guide_data` from `GAPDirector` to positive conditioning, negative conditioning, and a latent.

Use it when:
- You already have timeline data from `GAPDirector`.
- You want the guide images inserted at the exact frames defined by the timeline editor.

Important controls:
- `positive`, `negative`, `vae`, `latent`, and `guide_data` are all required.
- `scale_by` lets you resize the latent before inserting guides.
- `upscale_method` controls how latent resizing is performed.

### `GAPSequencer`

Places multiple guide images at chosen frame or second positions in a latent timeline.

Use it when:
- You want manual guide placement without the full timeline UI.
- You are building first-frame, last-frame, or sparse multi-keyframe LTX workflows.

Important controls:
- `multi_input` comes from `GAPMultiImageLoader`.
- `num_images` decides how many insert and strength control groups are shown.
- `insert_mode` switches between frame-based and second-based placement.
- `frame_rate` matters only when you use seconds.
- `insert_frame_n` or `insert_second_n` sets the placement for each image.
- `strength_n` controls how strongly each guide influences the latent.

### `GAPKeyframer`

Directly replaces portions of an existing latent sequence with encoded guide images.

Use it when:
- You already know the exact frame index where an image should replace the latent.
- You want more literal keyframe replacement instead of guide-based blending.

Important controls:
- `multi_input` again comes from `GAPMultiImageLoader`.
- `num_images` controls how many `insert_frame_n` and `strength_n` widget groups appear.
- Negative insert frames are supported and count backward from the end of the pixel-space sequence.

### `GAPMultiImageLoader`

Loads multiple images and exposes them both as a batch and as individual outputs.

Use it when:
- You want to feed several guide images into `GAPSequencer` or `GAPKeyframer`.
- You want one loader that can resize, crop, pad, or compress images before guide insertion.

Important controls:
- `image_paths` is a newline-separated list of input images.
- `width`, `height`, `interpolation`, `resize_method`, and `multiple_of` control resizing behavior.
- `img_compression` adds JPEG-style degradation after resize to mimic compressed source material.

Behavior note:
- `multi_output` is only built when all loaded images end up at the same size.
- If resize settings produce mixed sizes, the batch output falls back to a placeholder tensor but the individual outputs still work.

## Media Input And Utility Nodes

### `GAPLoadVideoUI`

Interactive video loader with preview, trim, crop, resize, and audio extraction.

Use it when:
- You want a single node to load a source clip and keep video and audio aligned.
- You want to trim and crop before the clip enters the editor stack.

Important controls:
- `video` can point at a file already inside `ComfyUI/input`, an annotated ComfyUI path, or a file uploaded through the node UI.
- `display_mode` switches the trim UI between seconds and frames.
- `start_time`, `end_time`, and `duration` are the second-based trim controls.
- `start_frame`, `end_frame`, and `duration_frames` are the frame-based trim controls.
- `frame_rate` forces a consistent extraction rate even when the source clip uses a different native FPS.
- `resize_method`, `custom_width`, `custom_height`, and the crop controls determine the output frame size.

How to use it:
- Leave `custom_width` and `custom_height` at `0` if you want the source size.
- Use seconds mode for rough trimming and frames mode for precise cut points.
- Use crop first, then resize.
- Treat `end_time=0` or `end_frame=0` as "go to the end of the clip."

Outputs:
- `images`
- `audio`
- `duration`
- `frame_count`

### `GAPLoadAudioUI`

Interactive audio loader with trim controls.

Use it when:
- You need a standalone audio source for a workflow.
- You want a safer loader that falls back to silence instead of hard-failing.

Important controls:
- `audio` can be an audio file or a video file with an audio stream.
- `start_time`, `end_time`, and `duration` trim the loaded waveform.

Behavior note:
- Missing or undecodable files return one second of silence so the workflow can continue.

### `GAPSpeechLengthCalculator`

Estimates spoken duration from quoted text.

Use it when:
- You want a fast frame estimate before building a talking-head or narration-driven timeline.

Important controls:
- Put spoken lines inside quotes. Only quoted text is counted.
- `fps` converts the estimate into frames.
- `additional_time` adds padding on top of the speech estimate.

Outputs:
- Slow, average, and fast frame counts.
- The active text string that was measured.

## Editing And Export Nodes

### `GAPClipEditor`

Single-clip editing node for trimming, retiming, looping, reversing, ping-pong playback, frame blending, audio gain, and fades.

Use it when:
- You already have one clip and want to reshape its timing before export.
- You want a quick editorial node without needing a full NLE.

Important controls:
- `trim_start_frame` and `trim_end_frame` define the source range.
- `trim_end_frame=0` means use the rest of the clip.
- `playback_speed` retimes both video and audio.
- `loop_count` repeats the processed clip.
- `reverse` flips the clip before looping.
- `ping_pong` appends a mirrored playback pass.
- `frame_blend` only matters during retiming and softens frame jumps.
- `audio_gain`, `fade_in_frames`, and `fade_out_frames` shape the resulting audio.

Ordering note:
- The node trims first, then reverses, then applies ping-pong, then loops, and finally retimes.

### `GAPTransitionComposer`

Combines two clips with one of several visual transitions.

Use it when:
- You want a simple editorial join between two source clips.
- You want audio to remain aligned through the transition.

Important controls:
- `transition_type` can be `cut`, `crossfade`, `wipe_left`, `wipe_right`, `slide_left`, or `slide_right`.
- `transition_frames` controls the overlap length. `cut` ignores it.
- `hold_before_transition` duplicates the final frame of the first clip before the transition block.
- `hold_after_transition` duplicates the first frame of the post-transition section.
- `resize_mode` decides whether the primary or secondary clip defines the output frame size.
- `audio_crossfade` crossfades the overlapping audio section when a real transition is present.

Usage note:
- Keep both source loaders on the same `frame_rate` for the most predictable result.

### `GAPLayerComposer`

Adds a second timed video layer on top of a base clip with blend modes, placement controls, and mixed audio.

Use it when:
- You want picture-in-picture, logo bugs, reaction cams, corner overlays, or split editorial builds.
- You want the overlay clip to fade in and out without baking that timing into the source media.
- You want base audio to duck automatically while the overlay layer is active.

Important controls:
- `overlay_start_frame` and `overlay_end_frame` define where the overlay appears. `overlay_end_frame=0` uses the overlay clip's native length.
- `overlay_scale`, `position`, `margin_x`, and `margin_y` place the second layer inside the base frame.
- `opacity`, `fade_in_frames`, and `fade_out_frames` shape the visual entrance and exit of the overlay.
- `blend_mode` supports `normal`, `screen`, `add`, `multiply`, and `overlay`.
- `playback_mode` controls how the overlay behaves when the requested range is longer than the source overlay clip: `trim`, `loop`, or `hold last`.
- `extend_output` decides whether the result can grow past the base clip length to keep the overlay visible.
- `base_audio_gain`, `overlay_audio_gain`, and `audio_ducking` shape the mixed soundtrack.

Usage note:
- A practical finishing chain is `GAPLayerComposer -> GAPMotionTextFX -> GAPVideoExporter`.
- The frame controls support long editorial spans up to `100000` frames, matching the rest of the suite's time-based nodes.
- `hold last` only freezes the overlay picture. Overlay audio stays natural and pads with silence instead of repeating the last audio sample.

### `GAPMotionTextFX`

Adds text overlays, freeze-frame inserts, and speed ramps.

Use it when:
- You want titles, captions, lower thirds, or simple hold-frame emphasis.
- You want a light finishing pass after clip assembly.

Important controls:
- `overlay_text` can be multiline.
- `font_size`, `position`, `margin_x`, and `margin_y` control text placement.
- `text_color`, `box_color`, `box_opacity`, `stroke_color`, and `stroke_width` style the title card.
- `text_start_frame` and `text_end_frame` define where the overlay appears. `text_end_frame=0` means run to the end.
- `freeze_frame_index=-1` disables the freeze insert.
- `freeze_duration_frames` inserts a still frame plus matching audio silence.
- `ramp_start_frame`, `ramp_end_frame`, `ramp_start_speed`, and `ramp_end_speed` retime part of the clip.

Usage note:
- Apply overlay text first when you are tuning layout.
- Add freeze inserts and speed ramps after the text placement is stable, because those operations change clip length.
- If you need text on top of a video overlay, place `GAPMotionTextFX` after `GAPLayerComposer` so the caption is rendered on the fully composited frame.

### `GAPVideoExporter`

Output node that encodes `IMAGE` plus optional `AUDIO` into a file.

Use it when:
- You are ready to render the final editorial result from the suite.

Important controls:
- `filename_prefix` can include subfolders inside the ComfyUI output directory.
- `container` chooses `mp4`, `mov`, `webm`, `mkv`, or `gif`.
- `video_codec` and `audio_codec` can stay on `auto` for the first render.
- `pixel_format=auto` chooses a sensible default for the selected container.
- `preset` and `crf` matter most for H.264 and H.265 style exports.
- `video_bitrate` and `audio_bitrate` accept strings such as `8000k` or `192k`.
- `match_video_length` trims or pads audio so it lands exactly on the exported frame range.

Behavior note:
- `gif` exports ignore audio.
- Output files are written using ComfyUI's normal output-path helper, so the prefix determines the final folder layout.
