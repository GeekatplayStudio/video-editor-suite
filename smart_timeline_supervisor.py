import json

import torch


MAX_SMART_TIMELINE_SEGMENTS = 12


class GAPSmartTimelineSupervisor:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "timeline_plan_input": ("STRING", {"forceInput": True}),
        }
        for index in range(1, MAX_SMART_TIMELINE_SEGMENTS + 1):
            optional[f"images_{index}"] = ("IMAGE",)
            optional[f"audio_{index}"] = ("AUDIO",)

        return {
            "required": {
                "timeline_plan": ("STRING", {"multiline": True, "default": "{}"}),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT", "INT", "FLOAT")
    RETURN_NAMES = (
        "timeline_plan",
        "summary",
        "missing_image_slots",
        "missing_audio_slots",
        "next_missing_slot",
        "ready_to_assemble",
        "image_completion_ratio",
    )
    FUNCTION = "inspect_timeline"
    CATEGORY = "Geekatplay Studio/Video Editor Suite"

    @staticmethod
    def _active_plan_text(timeline_plan, timeline_plan_input=None):
        if isinstance(timeline_plan_input, str) and timeline_plan_input.strip():
            return timeline_plan_input
        return timeline_plan

    @staticmethod
    def _parse_plan(active_plan):
        try:
            parsed = json.loads(active_plan)
        except Exception as exc:
            raise ValueError(f"Smart Timeline Supervisor: invalid plan JSON - {exc}") from exc

        if isinstance(parsed, list):
            return {"segments": parsed}
        if not isinstance(parsed, dict):
            raise ValueError("Smart Timeline Supervisor expects a planner manifest object or a raw segment array.")
        return parsed

    @staticmethod
    def _has_image_clip(value):
        return isinstance(value, torch.Tensor) and value.ndim in (3, 4) and value.shape[0] != 0

    @staticmethod
    def _has_audio_clip(value):
        return isinstance(value, dict) and "waveform" in value

    @staticmethod
    def _slot_name(prefix: str, index: int) -> str:
        return f"{prefix}_{index}"

    def inspect_timeline(self, timeline_plan, timeline_plan_input=None, **kwargs):
        active_plan = self._active_plan_text(timeline_plan, timeline_plan_input)
        plan = self._parse_plan(active_plan)
        segments = plan.get("segments", [])
        if not isinstance(segments, list):
            raise ValueError("Smart Timeline Supervisor: planner manifest is missing a valid 'segments' array.")

        assembly_export_ready = bool(plan.get("assembly_export_ready", False))
        assembly_max_segments = int(plan.get("assembly_max_segments", MAX_SMART_TIMELINE_SEGMENTS) or MAX_SMART_TIMELINE_SEGMENTS)

        if len(segments) > MAX_SMART_TIMELINE_SEGMENTS:
            raise ValueError(
                f"Smart Timeline Supervisor supports up to {MAX_SMART_TIMELINE_SEGMENTS} segments per node; the plan contains {len(segments)}."
            )

        connected_image_slots = []
        connected_audio_slots = []
        missing_image_slots = []
        missing_audio_slots = []
        summary_lines = [
            f"Smart Timeline Supervisor | segments={len(segments)} | assembly_export_ready={1 if assembly_export_ready else 0}",
            f"Planner assembly max segments={assembly_max_segments}",
        ]

        for default_index, segment in enumerate(segments, start=1):
            slot = int(segment.get("assembly_slot", default_index) or default_index)
            mode = str(segment.get("mode", "clip"))
            segment_id = str(segment.get("id", f"segment_{default_index:03d}"))
            has_images = self._has_image_clip(kwargs.get(self._slot_name("images", slot)))
            has_audio = self._has_audio_clip(kwargs.get(self._slot_name("audio", slot)))

            if has_images:
                connected_image_slots.append(slot)
            else:
                missing_image_slots.append(slot)

            if has_audio:
                connected_audio_slots.append(slot)
            else:
                missing_audio_slots.append(slot)

            summary_lines.append(
                f"- slot {slot} | id={segment_id} | mode={mode} | images={'yes' if has_images else 'no'} | audio={'yes' if has_audio else 'no'}"
            )

        segment_count = len(segments)
        ready_to_assemble = int(segment_count > 0 and assembly_export_ready and len(missing_image_slots) == 0)
        completion_ratio = 0.0 if segment_count == 0 else float(len(connected_image_slots) / float(segment_count))
        next_missing_slot = int(missing_image_slots[0]) if missing_image_slots else 0

        if not assembly_export_ready:
            summary_lines.append("Planner says assembly is not ready yet. Check lane exports or segment count before stitching.")
        elif ready_to_assemble:
            summary_lines.append("All required image slots are connected. Assembly can run now.")
        else:
            summary_lines.append(
                f"Assembly is waiting on image slots: {', '.join(str(slot) for slot in missing_image_slots)}"
            )

        if missing_audio_slots:
            summary_lines.append(
                f"Audio is optional. Missing audio slots will assemble with silence: {', '.join(str(slot) for slot in missing_audio_slots)}"
            )

        return (
            active_plan,
            "\n".join(summary_lines),
            ",".join(str(slot) for slot in missing_image_slots),
            ",".join(str(slot) for slot in missing_audio_slots),
            next_missing_slot,
            ready_to_assemble,
            completion_ratio,
        )