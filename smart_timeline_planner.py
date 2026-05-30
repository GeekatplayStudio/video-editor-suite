import json
import os

import folder_paths


SAMPLE_TIMELINE = json.dumps(
    {
        "defaults": {
            "width": 768,
            "height": 512,
            "duration_seconds": 2.0,
            "guide_strength": 0.85,
        },
        "segments": [
            {
                "mode": "t2v",
                "prompt": "wide establishing shot of a rainy neon street",
                "duration_seconds": 2.0,
            },
            {
                "mode": "i2v",
                "prompt": "camera pushes into the storefront",
                "image": "reference_storefront.png",
                "duration_seconds": 2.0,
                "guide_strength": 0.9,
            },
            {
                "mode": "v2v",
                "prompt": "keep the dancer silhouette and amplify stage lighting",
                "video": "guide_dancer.mp4",
                "duration_seconds": 2.0,
            },
            {
                "mode": "fflf",
                "prompt": "sunrise over the canyon",
                "first_frame": "canyon_start.png",
                "last_frame": "canyon_end.png",
                "duration_seconds": 2.0,
            },
        ],
    },
    indent=2,
)


MAX_SMART_TIMELINE_SEGMENTS = 12


MODE_ALIASES = {
    "t2v": "t2v",
    "text_to_video": "t2v",
    "text-to-video": "t2v",
    "text": "t2v",
    "prompt": "t2v",
    "i2v": "i2v",
    "image_to_video": "i2v",
    "image-to-video": "i2v",
    "guide_image": "i2v",
    "guide-image": "i2v",
    "image": "i2v",
    "v2v": "v2v",
    "video_to_video": "v2v",
    "video-to-video": "v2v",
    "guide_video": "v2v",
    "guide-video": "v2v",
    "video": "v2v",
    "fflf": "fflf",
    "first_last_frame": "fflf",
    "first-last-frame": "fflf",
    "firstlastframe": "fflf",
}


def _coerce_int(value, fallback):
    try:
        return int(round(float(value)))
    except Exception:
        return int(fallback)


def _coerce_float(value, fallback):
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def _looks_like_data_uri(value):
    if not isinstance(value, str):
        return False
    return value.startswith("data:") or value.startswith("/view?")


def _asset_exists(path):
    if not isinstance(path, str) or not path.strip() or _looks_like_data_uri(path):
        return False

    cleaned = path.strip()
    if os.path.exists(cleaned):
        return True

    input_path = os.path.join(folder_paths.get_input_directory(), cleaned)
    return os.path.exists(input_path)


DIRECTOR_WORKFLOW_HINTS = [
    "Geekatplay Video Editor Suite - LTX 2.3 Director Lab.json",
    "LTX Director Example Workflow (Fixed).json",
]

GUIDE_VIDEO_WORKFLOW_HINTS = [
    "LTX I2V First Last Frame 2 Stage Workflow v6.json",
    "LTX I2V First Last Frame 3 Stage Workflow v6.json",
]

FIRST_LAST_WORKFLOW_HINTS = [
    "LTX I2V First Last Frame 2 Stage Workflow v6.json",
    "LTX I2V First Last Frame 3 Stage Workflow v6.json",
]


class GAPSmartTimelinePlanner:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "timeline_json": ("STRING", {"multiline": True, "default": SAMPLE_TIMELINE}),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 240, "step": 1}),
                "default_width": ("INT", {"default": 768, "min": 64, "max": 4096, "step": 32}),
                "default_height": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 32}),
                "default_segment_seconds": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 120.0, "step": 0.1}),
                "strict_validation": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "timeline_json_input": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "INT", "INT", "FLOAT", "STRING")
    RETURN_NAMES = (
        "timeline_plan",
        "director_timeline_data",
        "local_prompts",
        "segment_lengths",
        "guide_strength",
        "segment_count",
        "duration_frames",
        "duration_seconds",
        "summary",
    )
    FUNCTION = "plan_timeline"
    CATEGORY = "Geekatplay Studio/Video Editor Suite"

    @staticmethod
    def _active_timeline_text(timeline_json, timeline_json_input=None):
        if isinstance(timeline_json_input, str) and timeline_json_input.strip():
            return timeline_json_input
        return timeline_json

    @staticmethod
    def _normalize_mode(raw_mode):
        if raw_mode is None:
            return None
        key = str(raw_mode).strip().lower().replace(" ", "_")
        return MODE_ALIASES.get(key)

    @staticmethod
    def _resolve_duration_frames(segment, frame_rate, default_segment_frames, default_duration_seconds):
        if "duration_frames" in segment:
            return max(1, _coerce_int(segment.get("duration_frames"), default_segment_frames))
        if "length" in segment:
            return max(1, _coerce_int(segment.get("length"), default_segment_frames))
        if "duration_seconds" in segment:
            seconds = max(0.01, _coerce_float(segment.get("duration_seconds"), default_duration_seconds))
            return max(1, int(round(seconds * frame_rate)))
        return max(1, int(default_segment_frames))

    @staticmethod
    def _resolve_start_frame(segment, frame_rate, fallback_start):
        if "start" in segment:
            return max(0, _coerce_int(segment.get("start"), fallback_start))
        if "start_frame" in segment:
            return max(0, _coerce_int(segment.get("start_frame"), fallback_start))
        if "start_seconds" in segment:
            return max(0, int(round(_coerce_float(segment.get("start_seconds"), 0.0) * frame_rate)))
        return max(0, int(fallback_start))

    @staticmethod
    def _resolve_asset(segment, *keys):
        for key in keys:
            value = segment.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _build_director_segment(segment):
        director_segment = {
            "id": segment["id"],
            "start": segment["start"],
            "length": segment["length"],
            "prompt": segment["prompt"],
            "type": segment["director_type"],
        }
        if segment["director_type"] == "image" and segment["image"]:
            if _looks_like_data_uri(segment["image"]):
                director_segment["imageB64"] = segment["image"]
            else:
                director_segment["imageFile"] = segment["image"]
        return director_segment

    @classmethod
    def _build_director_shot_contract(cls, segment, frame_rate):
        isolated_segment = dict(segment)
        isolated_segment["start"] = 0
        director_segment = cls._build_director_segment(isolated_segment)
        return {
            "segment_id": segment["id"],
            "assembly_slot": segment["assembly_slot"],
            "mode": segment["mode"],
            "entrypoint": "GAPDirector",
            "recommended_workflows": DIRECTOR_WORKFLOW_HINTS,
            "duration_frames": segment["length"],
            "duration_seconds": segment["length"] / float(frame_rate),
            "width": segment["width"],
            "height": segment["height"],
            "prompt": segment["prompt"],
            "negative_prompt": segment["negative_prompt"],
            "seed": segment["seed"],
            "timeline_data": {"segments": [director_segment], "audioSegments": []},
            "local_prompts": segment["prompt"],
            "segment_lengths": str(segment["length"]),
            "guide_strength": f"{segment['guide_strength']:.2f}" if segment["director_type"] == "image" else "",
            "notes": list(segment["notes"]),
        }

    @staticmethod
    def _build_guide_video_shot_contract(segment, frame_rate):
        return {
            "segment_id": segment["id"],
            "assembly_slot": segment["assembly_slot"],
            "mode": segment["mode"],
            "entrypoint": "GAPLoadVideoUI + GAPSequencer",
            "recommended_workflows": GUIDE_VIDEO_WORKFLOW_HINTS,
            "duration_frames": segment["length"],
            "duration_seconds": segment["length"] / float(frame_rate),
            "width": segment["width"],
            "height": segment["height"],
            "prompt": segment["prompt"],
            "negative_prompt": segment["negative_prompt"],
            "seed": segment["seed"],
            "guide_video": segment["video"],
            "workflow_handoff": {
                "load_video_path": segment["video"],
                "use_case": "Guide-video or sparse reference video conditioning for this standalone shot.",
                "target_duration_frames": segment["length"],
                "target_resolution": {"width": segment["width"], "height": segment["height"]},
            },
            "notes": list(segment["notes"]),
        }

    @staticmethod
    def _build_first_last_shot_contract(segment, frame_rate):
        return {
            "segment_id": segment["id"],
            "assembly_slot": segment["assembly_slot"],
            "mode": segment["mode"],
            "entrypoint": "GAPSequencer or GAPKeyframer",
            "recommended_workflows": FIRST_LAST_WORKFLOW_HINTS,
            "duration_frames": segment["length"],
            "duration_seconds": segment["length"] / float(frame_rate),
            "width": segment["width"],
            "height": segment["height"],
            "prompt": segment["prompt"],
            "negative_prompt": segment["negative_prompt"],
            "seed": segment["seed"],
            "first_frame": segment["first_frame"],
            "last_frame": segment["last_frame"],
            "workflow_handoff": {
                "first_frame_path": segment["first_frame"],
                "last_frame_path": segment["last_frame"],
                "use_case": "First/last-frame or sparse keyframe conditioning for this standalone shot.",
                "target_duration_frames": segment["length"],
                "target_resolution": {"width": segment["width"], "height": segment["height"]},
            },
            "notes": list(segment["notes"]),
        }

    @classmethod
    def _build_lane_exports(cls, segments, frame_rate):
        director_shots = []
        guide_video_shots = []
        first_last_frame_shots = []
        render_queue = []

        for segment in segments:
            contract = None
            if segment["mode"] in {"t2v", "i2v"}:
                contract = cls._build_director_shot_contract(segment, frame_rate)
                director_shots.append(contract)
            elif segment["mode"] == "v2v":
                contract = cls._build_guide_video_shot_contract(segment, frame_rate)
                guide_video_shots.append(contract)
            elif segment["mode"] == "fflf":
                contract = cls._build_first_last_shot_contract(segment, frame_rate)
                first_last_frame_shots.append(contract)

            render_queue.append(
                {
                    "segment_id": segment["id"],
                    "assembly_slot": segment["assembly_slot"],
                    "mode": segment["mode"],
                    "execution_lane": segment["execution_lane"],
                    "duration_frames": segment["length"],
                    "duration_seconds": segment["length"] / float(frame_rate),
                    "entrypoint": contract["entrypoint"] if contract else segment["execution_lane"],
                    "prompt": segment["prompt"],
                }
            )

        return {
            "director_shots": director_shots,
            "guide_video_shots": guide_video_shots,
            "first_last_frame_shots": first_last_frame_shots,
            "render_queue": render_queue,
        }

    def plan_timeline(
        self,
        timeline_json,
        frame_rate,
        default_width,
        default_height,
        default_segment_seconds,
        strict_validation=False,
        timeline_json_input=None,
    ):
        active_timeline = self._active_timeline_text(timeline_json, timeline_json_input)
        try:
            parsed = json.loads(active_timeline)
        except Exception as exc:
            raise ValueError(f"Smart Timeline Planner: invalid JSON - {exc}") from exc

        if isinstance(parsed, list):
            root = {}
            raw_segments = parsed
        elif isinstance(parsed, dict):
            root = parsed
            raw_segments = parsed.get("segments", [])
        else:
            raise ValueError("Smart Timeline Planner expects a JSON object with a 'segments' array or a raw segment array.")

        if not isinstance(raw_segments, list) or not raw_segments:
            raise ValueError("Smart Timeline Planner needs at least one segment in the 'segments' array.")

        defaults = root.get("defaults", {}) if isinstance(root.get("defaults", {}), dict) else {}
        effective_frame_rate = max(1, _coerce_int(root.get("frame_rate", frame_rate), frame_rate))
        default_duration_seconds = max(0.1, _coerce_float(defaults.get("duration_seconds", default_segment_seconds), default_segment_seconds))
        default_segment_frames = max(1, int(round(default_duration_seconds * effective_frame_rate)))
        default_width = max(64, _coerce_int(defaults.get("width", default_width), default_width))
        default_height = max(64, _coerce_int(defaults.get("height", default_height), default_height))
        default_guide_strength = _clamp(_coerce_float(defaults.get("guide_strength", 1.0), 1.0), 0.0, 1.0)
        default_prompt = str(defaults.get("prompt", "") or "").strip()
        default_negative_prompt = str(defaults.get("negative_prompt", "") or "").strip()
        default_seed = defaults.get("seed")

        summary_lines = [
            f"Smart Timeline Planner | fps={effective_frame_rate} | defaults={default_width}x{default_height}",
        ]
        blocking_issues = []
        normalized_segments = []
        cursor = 0

        for index, raw_segment in enumerate(raw_segments, start=1):
            if not isinstance(raw_segment, dict):
                blocking_issues.append(f"Segment {index} must be a JSON object.")
                continue

            mode = self._normalize_mode(
                raw_segment.get("mode")
                or raw_segment.get("segment_mode")
                or raw_segment.get("shot_mode")
                or raw_segment.get("type")
            )
            if mode is None:
                blocking_issues.append(
                    f"Segment {index} uses an unsupported mode '{raw_segment.get('mode', raw_segment.get('type', ''))}'. "
                    "Use one of: t2v, i2v, v2v, fflf."
                )
                continue

            start = self._resolve_start_frame(raw_segment, effective_frame_rate, cursor)
            if start < cursor:
                blocking_issues.append(
                    f"Segment {index} starts at frame {start}, which overlaps the previous segment ending at frame {cursor}."
                )

            length = self._resolve_duration_frames(
                raw_segment,
                effective_frame_rate,
                default_segment_frames,
                default_duration_seconds,
            )
            end = start + length

            prompt = str(raw_segment.get("prompt", default_prompt) or "").strip()
            negative_prompt = str(raw_segment.get("negative_prompt", default_negative_prompt) or "").strip()
            width = max(64, _coerce_int(raw_segment.get("width", default_width), default_width))
            height = max(64, _coerce_int(raw_segment.get("height", default_height), default_height))
            guide_strength = _clamp(
                _coerce_float(raw_segment.get("guide_strength", default_guide_strength), default_guide_strength),
                0.0,
                1.0,
            )
            seed = raw_segment.get("seed", default_seed)

            image = self._resolve_asset(raw_segment, "image", "imageFile", "guide_image", "guideImage")
            video = self._resolve_asset(raw_segment, "video", "videoFile", "guide_video", "guideVideo")
            first_frame = self._resolve_asset(raw_segment, "first_frame", "firstFrame", "first_image", "firstImage")
            last_frame = self._resolve_asset(raw_segment, "last_frame", "lastFrame", "last_image", "lastImage")

            notes = []
            director_compatible = False
            director_type = ""
            execution_lane = ""

            if width % 32 != 0 or height % 32 != 0:
                notes.append("LTX-friendly resolutions are usually divisible by 32.")

            if mode == "t2v":
                execution_lane = "director_prompt"
                director_compatible = True
                director_type = "text"
                if not prompt:
                    blocking_issues.append(f"Segment {index} (t2v) is missing a prompt.")

            elif mode == "i2v":
                execution_lane = "director_guide_image"
                director_compatible = True
                director_type = "image"
                if not image:
                    blocking_issues.append(f"Segment {index} (i2v) is missing an image or imageFile reference.")
                if not prompt:
                    notes.append("No prompt provided; generation quality may depend entirely on the guide image.")

            elif mode == "v2v":
                execution_lane = "guide_video"
                if not video:
                    blocking_issues.append(f"Segment {index} (v2v) is missing a video or videoFile reference.")
                notes.append("Requires a dedicated guide-video render lane; GAPDirector cannot compile video guide segments directly yet.")

            elif mode == "fflf":
                execution_lane = "first_last_frame"
                if not first_frame or not last_frame:
                    blocking_issues.append(
                        f"Segment {index} (fflf) needs both first_frame and last_frame references."
                    )
                notes.append("Requires a first/last-frame lane such as GAPSequencer or GAPKeyframer; GAPDirector cannot compile it directly yet.")

            for label, asset in (("image", image), ("video", video), ("first_frame", first_frame), ("last_frame", last_frame)):
                if asset and not _looks_like_data_uri(asset) and not _asset_exists(asset):
                    notes.append(f"{label} reference '{asset}' was not found in ComfyUI/input at planning time.")

            normalized_segment = {
                "index": index,
                "id": str(raw_segment.get("id") or f"segment_{index:03d}"),
                "assembly_slot": index,
                "mode": mode,
                "execution_lane": execution_lane,
                "start": start,
                "length": length,
                "end": end,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "seed": seed,
                "guide_strength": guide_strength,
                "image": image,
                "video": video,
                "first_frame": first_frame,
                "last_frame": last_frame,
                "director_compatible": director_compatible,
                "director_type": director_type,
                "notes": notes,
            }
            normalized_segments.append(normalized_segment)
            cursor = max(cursor, end)

            prompt_preview = prompt[:48] + ("..." if len(prompt) > 48 else "")
            compatibility = "director" if director_compatible else execution_lane
            summary_lines.append(
                f"- #{index} {mode} {start}->{end}f | lane={compatibility} | prompt='{prompt_preview or '(none)'}'"
            )
            for note in notes:
                summary_lines.append(f"  note: {note}")

        requested_duration_frames = None
        if "duration_frames" in root:
            requested_duration_frames = max(1, _coerce_int(root.get("duration_frames"), cursor or default_segment_frames))
        elif "duration_seconds" in root:
            requested_duration_frames = max(
                1,
                int(round(_coerce_float(root.get("duration_seconds"), cursor / float(effective_frame_rate or 1)) * effective_frame_rate)),
            )

        total_duration_frames = cursor
        if requested_duration_frames is not None:
            if requested_duration_frames < cursor:
                blocking_issues.append(
                    f"Top-level duration ({requested_duration_frames} frames) is shorter than the planned content ({cursor} frames)."
                )
            total_duration_frames = max(cursor, requested_duration_frames)

        director_export_ready = bool(normalized_segments) and all(
            segment["director_compatible"] for segment in normalized_segments
        )
        assembly_export_ready = bool(normalized_segments) and len(normalized_segments) <= MAX_SMART_TIMELINE_SEGMENTS

        director_timeline_data = {}
        local_prompts = ""
        segment_lengths = ""
        guide_strengths = ""
        if director_export_ready and not blocking_issues:
            director_segments = [self._build_director_segment(segment) for segment in normalized_segments]
            director_timeline_data = {"segments": director_segments, "audioSegments": []}
            local_prompts = " | ".join(segment["prompt"] for segment in normalized_segments)
            segment_lengths = ",".join(str(segment["length"]) for segment in normalized_segments)
            guide_strengths = ",".join(
                f"{segment['guide_strength']:.2f}"
                for segment in normalized_segments
                if segment["director_type"] == "image"
            )
            summary_lines.append("Director export is ready: all segments map to GAPDirector today.")
        else:
            summary_lines.append(
                "Director export is not ready: at least one segment needs a non-Director render lane or validation still failed."
            )

        if assembly_export_ready:
            summary_lines.append(
                f"Assembly export is ready: feed rendered clips into images_1..images_{len(normalized_segments)} in Smart Timeline Assembler."
            )
        else:
            summary_lines.append(
                f"Assembly export is not ready in one node: the plan has {len(normalized_segments)} segments but Smart Timeline Assembler supports up to {MAX_SMART_TIMELINE_SEGMENTS}."
            )

        if blocking_issues:
            summary_lines.append("Blocking issues:")
            for issue in blocking_issues:
                summary_lines.append(f"- {issue}")

        lane_exports = self._build_lane_exports(normalized_segments, effective_frame_rate)
        summary_lines.append(
            "Lane exports: "
            f"director_shots={len(lane_exports['director_shots'])} | "
            f"guide_video_shots={len(lane_exports['guide_video_shots'])} | "
            f"first_last_frame_shots={len(lane_exports['first_last_frame_shots'])}"
        )

        plan = {
            "version": 2,
            "frame_rate": effective_frame_rate,
            "duration_frames": total_duration_frames,
            "duration_seconds": total_duration_frames / float(effective_frame_rate),
            "defaults": {
                "width": default_width,
                "height": default_height,
                "duration_frames": default_segment_frames,
                "guide_strength": default_guide_strength,
                "prompt": default_prompt,
                "negative_prompt": default_negative_prompt,
                "seed": default_seed,
            },
            "director_export_ready": director_export_ready and not blocking_issues,
            "assembly_export_ready": assembly_export_ready,
            "assembly_max_segments": MAX_SMART_TIMELINE_SEGMENTS,
            "blocking_issues": blocking_issues,
            "lane_exports": lane_exports,
            "render_queue": lane_exports["render_queue"],
            "segments": normalized_segments,
        }

        if strict_validation and blocking_issues:
            raise ValueError("Smart Timeline Planner validation failed:\n- " + "\n- ".join(blocking_issues))

        return (
            json.dumps(plan, indent=2),
            json.dumps(director_timeline_data, indent=2) if director_timeline_data else "{}",
            local_prompts,
            segment_lengths,
            guide_strengths,
            len(normalized_segments),
            int(total_duration_frames),
            float(total_duration_frames / float(effective_frame_rate)),
            "\n".join(summary_lines),
        )