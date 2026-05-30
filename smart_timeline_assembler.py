import json

import torch
import torch.nn.functional as F


MAX_SMART_TIMELINE_SEGMENTS = 12
TARGET_AUDIO_RATE = 44100


def _frame_samples(frame_count: int, frame_rate: int, sample_rate: int) -> int:
    return max(1, int(round(max(0, frame_count) / float(frame_rate) * sample_rate)))


def _fit_waveform_samples(waveform: torch.Tensor, target_samples: int) -> torch.Tensor:
    target_samples = max(1, int(target_samples))
    if waveform.shape[-1] == target_samples:
        return waveform
    resized = F.interpolate(waveform.unsqueeze(0), size=target_samples, mode="linear", align_corners=False)
    return resized[0]


class GAPSmartTimelineAssembler:
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
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 240, "step": 1}),
                "resize_mode": (["planner defaults", "match first clip"], {"default": "planner defaults"}),
                "gap_policy": (["trim gaps", "black frames", "hold last frame"], {"default": "trim gaps"}),
                "segment_fit": (["hold last", "loop", "strict"], {"default": "hold last"}),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "FLOAT", "INT", "STRING")
    RETURN_NAMES = ("images", "audio", "duration", "frame_count", "summary")
    FUNCTION = "assemble_timeline"
    CATEGORY = "Geekatplay Studio/Video Editor Suite"

    @staticmethod
    def _active_plan_text(timeline_plan, timeline_plan_input=None):
        if isinstance(timeline_plan_input, str) and timeline_plan_input.strip():
            return timeline_plan_input
        return timeline_plan

    @staticmethod
    def _parse_plan(timeline_plan):
        try:
            parsed = json.loads(timeline_plan)
        except Exception as exc:
            raise ValueError(f"Smart Timeline Assembler: invalid plan JSON - {exc}") from exc

        if isinstance(parsed, list):
            return {"segments": parsed}
        if not isinstance(parsed, dict):
            raise ValueError("Smart Timeline Assembler expects a planner manifest object or a raw segment array.")
        return parsed

    @staticmethod
    def _ensure_image_batch(images: torch.Tensor) -> torch.Tensor:
        if images.ndim == 3:
            images = images.unsqueeze(0)
        if images.ndim != 4:
            raise ValueError(f"Expected IMAGE tensor with 3 or 4 dims, got shape {tuple(images.shape)}")
        return torch.nan_to_num(images.detach().float(), nan=0.0, posinf=1.0, neginf=0.0).clamp(0.0, 1.0)

    @staticmethod
    def _resize_images(images: torch.Tensor, height: int, width: int) -> torch.Tensor:
        if images.shape[1] == height and images.shape[2] == width:
            return images.contiguous()
        nchw = images.permute(0, 3, 1, 2)
        resized = F.interpolate(nchw, size=(height, width), mode="bilinear", align_corners=False)
        return resized.permute(0, 2, 3, 1).contiguous()

    @staticmethod
    def _normalize_audio(audio: dict | None, target_rate: int, target_device: torch.device) -> torch.Tensor | None:
        if not audio or "waveform" not in audio:
            return None

        waveform = audio["waveform"]
        if waveform.ndim == 2:
            waveform = waveform.unsqueeze(0)
        if waveform.ndim != 3:
            raise ValueError(f"Expected AUDIO waveform with 2 or 3 dims, got shape {tuple(waveform.shape)}")

        waveform = torch.nan_to_num(waveform[0].detach().float(), nan=0.0, posinf=0.0, neginf=0.0)
        if waveform.shape[0] > 2:
            waveform = waveform[:2]

        sample_rate = int(audio.get("sample_rate", target_rate))
        if sample_rate != target_rate and waveform.shape[-1] > 0:
            target_samples = max(1, int(round(waveform.shape[-1] * target_rate / float(sample_rate))))
            waveform = _fit_waveform_samples(waveform, target_samples)

        return waveform.to(device=target_device).contiguous()

    @staticmethod
    def _match_channels(waveform: torch.Tensor, channels: int) -> torch.Tensor:
        if waveform.shape[0] == channels:
            return waveform
        if waveform.shape[0] == 1 and channels == 2:
            return waveform.repeat(2, 1)
        return waveform[:channels]

    @staticmethod
    def _silence(channels: int, samples: int, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
        return torch.zeros((channels, max(1, int(samples))), dtype=dtype, device=device)

    @staticmethod
    def _repeat_last_frame(frame: torch.Tensor, count: int) -> torch.Tensor:
        if count <= 0:
            return frame[:0].clone()
        return frame.repeat(count, 1, 1, 1)

    @staticmethod
    def _extend_images(images: torch.Tensor, target_frames: int, fit_mode: str) -> torch.Tensor:
        current_frames = int(images.shape[0])
        if current_frames == target_frames:
            return images.contiguous()
        if current_frames > target_frames:
            return images[:target_frames].contiguous()
        if fit_mode == "strict":
            raise ValueError(
                f"Smart Timeline Assembler: segment clip is {current_frames} frames but the plan expects {target_frames}."
            )
        if fit_mode == "loop":
            repeats = max(1, (target_frames + current_frames - 1) // current_frames)
            tiled = images.repeat(repeats, 1, 1, 1)
            return tiled[:target_frames].contiguous()
        extension = GAPSmartTimelineAssembler._repeat_last_frame(images[-1:], target_frames - current_frames)
        return torch.cat((images, extension), dim=0).contiguous()

    @classmethod
    def _fit_audio_segment(cls, waveform: torch.Tensor | None, target_samples: int, fit_mode: str, channels: int, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
        if waveform is None:
            return cls._silence(channels, target_samples, device, dtype)

        waveform = cls._match_channels(waveform.to(device=device, dtype=dtype), channels)
        current_samples = int(waveform.shape[-1])
        if current_samples == target_samples:
            return waveform.contiguous()
        if current_samples > target_samples:
            return waveform[:, :target_samples].contiguous()
        if fit_mode == "strict":
            raise ValueError(
                f"Smart Timeline Assembler: segment audio is {current_samples} samples but the plan expects {target_samples}."
            )
        if fit_mode == "loop":
            repeats = max(1, (target_samples + current_samples - 1) // current_samples)
            tiled = waveform.repeat(1, repeats)
            return tiled[:, :target_samples].contiguous()

        padded = cls._silence(channels, target_samples, device, dtype)
        padded[:, :current_samples] = waveform
        return padded.contiguous()

    @staticmethod
    def _segment_input_name(index: int, prefix: str) -> str:
        return f"{prefix}_{index}"

    @staticmethod
    def _target_dimensions(plan: dict, resize_mode: str, first_images: torch.Tensor | None) -> tuple[int, int]:
        defaults = plan.get("defaults", {}) if isinstance(plan.get("defaults"), dict) else {}
        if resize_mode == "planner defaults":
            height = int(defaults.get("height", 0) or 0)
            width = int(defaults.get("width", 0) or 0)
            if height > 0 and width > 0:
                return height, width
        if first_images is None:
            raise ValueError("Smart Timeline Assembler: at least one segment clip is required to determine the output resolution.")
        return int(first_images.shape[1]), int(first_images.shape[2])

    def assemble_timeline(
        self,
        timeline_plan,
        frame_rate,
        resize_mode,
        gap_policy,
        segment_fit,
        timeline_plan_input=None,
        **kwargs,
    ):
        active_plan_text = self._active_plan_text(timeline_plan, timeline_plan_input)
        plan = self._parse_plan(active_plan_text)
        segments = plan.get("segments", [])
        if not isinstance(segments, list) or not segments:
            raise ValueError("Smart Timeline Assembler: the plan must contain at least one segment.")
        if len(segments) > MAX_SMART_TIMELINE_SEGMENTS:
            raise ValueError(
                f"Smart Timeline Assembler supports up to {MAX_SMART_TIMELINE_SEGMENTS} segments per node; the plan contains {len(segments)}."
            )

        effective_frame_rate = max(1, int(plan.get("frame_rate", frame_rate) or frame_rate))
        first_images = None
        prepared_images = {}
        prepared_audio = {}
        channel_count = 1

        for index in range(1, len(segments) + 1):
            images_value = kwargs.get(self._segment_input_name(index, "images"))
            if images_value is not None:
                images_batch = self._ensure_image_batch(images_value)
                prepared_images[index] = images_batch
                if first_images is None:
                    first_images = images_batch

        if first_images is None:
            raise ValueError("Smart Timeline Assembler: connect at least one images_n input that matches the planned segments.")

        target_height, target_width = self._target_dimensions(plan, resize_mode, first_images)
        base_device = first_images.device
        base_dtype = first_images.dtype

        for index in range(1, len(segments) + 1):
            audio_value = kwargs.get(self._segment_input_name(index, "audio"))
            if audio_value is not None:
                waveform = self._normalize_audio(audio_value, TARGET_AUDIO_RATE, base_device)
                if waveform is not None:
                    prepared_audio[index] = waveform
                    channel_count = max(channel_count, int(waveform.shape[0]))

        frame_blocks = []
        audio_blocks = []
        summary_lines = [
            f"Smart Timeline Assembler | fps={effective_frame_rate} | output={target_width}x{target_height}",
        ]
        current_frame = 0
        last_frame = None

        for default_index, segment in enumerate(segments, start=1):
            slot = int(segment.get("assembly_slot", default_index) or default_index)
            images = prepared_images.get(slot)
            if images is None:
                raise ValueError(
                    f"Smart Timeline Assembler: missing images_{slot} for segment '{segment.get('id', f'segment_{default_index:03d}')}'."
                )

            planned_start = int(segment.get("start", current_frame) or current_frame)
            planned_length = max(1, int(segment.get("length", images.shape[0]) or images.shape[0]))

            if gap_policy != "trim gaps" and planned_start > current_frame:
                gap_frames = planned_start - current_frame
                if gap_policy == "hold last frame" and last_frame is not None:
                    gap_images = self._repeat_last_frame(last_frame, gap_frames)
                else:
                    gap_images = torch.zeros((gap_frames, target_height, target_width, 3), dtype=base_dtype, device=base_device)
                frame_blocks.append(gap_images)
                audio_blocks.append(self._silence(channel_count, _frame_samples(gap_frames, effective_frame_rate, TARGET_AUDIO_RATE), base_device, base_dtype))
                current_frame += gap_frames
                summary_lines.append(f"- inserted {gap_frames} gap frames before slot {slot} using policy '{gap_policy}'")
            elif planned_start < current_frame:
                summary_lines.append(
                    f"- slot {slot} starts at {planned_start}f in the plan but is assembled sequentially after frame {current_frame}"
                )

            images = self._resize_images(images.to(device=base_device, dtype=base_dtype), target_height, target_width)
            original_frames = int(images.shape[0])
            images = self._extend_images(images, planned_length, segment_fit)
            target_samples = _frame_samples(planned_length, effective_frame_rate, TARGET_AUDIO_RATE)
            audio_wave = self._fit_audio_segment(prepared_audio.get(slot), target_samples, segment_fit, channel_count, base_device, base_dtype)

            frame_blocks.append(images)
            audio_blocks.append(audio_wave)
            current_frame += planned_length
            last_frame = images[-1:]

            mode = str(segment.get("mode", "clip"))
            prompt = str(segment.get("prompt", "") or "").strip()
            prompt_preview = prompt[:48] + ("..." if len(prompt) > 48 else "")
            summary_lines.append(
                f"- slot {slot} | mode={mode} | planned={planned_length}f | source={original_frames}f | prompt='{prompt_preview or '(none)'}'"
            )

        total_duration_frames = int(plan.get("duration_frames", current_frame) or current_frame)
        if gap_policy != "trim gaps" and total_duration_frames > current_frame:
            tail_gap = total_duration_frames - current_frame
            if gap_policy == "hold last frame" and last_frame is not None:
                tail_images = self._repeat_last_frame(last_frame, tail_gap)
            else:
                tail_images = torch.zeros((tail_gap, target_height, target_width, 3), dtype=base_dtype, device=base_device)
            frame_blocks.append(tail_images)
            audio_blocks.append(self._silence(channel_count, _frame_samples(tail_gap, effective_frame_rate, TARGET_AUDIO_RATE), base_device, base_dtype))
            current_frame += tail_gap
            summary_lines.append(f"- appended trailing gap of {tail_gap} frames to match plan duration")

        if not frame_blocks:
            raise ValueError("Smart Timeline Assembler: nothing was assembled from the provided segments.")

        images_out = torch.cat(frame_blocks, dim=0).contiguous()
        waveform = torch.cat(audio_blocks, dim=1).contiguous() if audio_blocks else self._silence(channel_count, 1, base_device, base_dtype)
        target_total_samples = _frame_samples(images_out.shape[0], effective_frame_rate, TARGET_AUDIO_RATE)
        waveform = _fit_waveform_samples(waveform, target_total_samples)
        duration_seconds = float(images_out.shape[0] / float(effective_frame_rate))
        audio_output = {"waveform": waveform.unsqueeze(0), "sample_rate": TARGET_AUDIO_RATE}
        return images_out, audio_output, duration_seconds, int(images_out.shape[0]), "\n".join(summary_lines)