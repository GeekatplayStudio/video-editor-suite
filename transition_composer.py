import torch
import torch.nn.functional as F


def _frame_samples(frame_count: int, frame_rate: int, sample_rate: int) -> int:
    return max(1, int(round(max(0, frame_count) / float(frame_rate) * sample_rate)))


def _fit_waveform_samples(waveform: torch.Tensor, target_samples: int) -> torch.Tensor:
    target_samples = max(1, int(target_samples))
    if waveform.shape[-1] == target_samples:
        return waveform
    resized = F.interpolate(waveform.unsqueeze(0), size=target_samples, mode="linear", align_corners=False)
    return resized[0]


class GAPTransitionComposer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "primary_images": ("IMAGE",),
                "secondary_images": ("IMAGE",),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 240, "step": 1}),
                "transition_type": (["cut", "crossfade", "wipe_left", "wipe_right", "slide_left", "slide_right"], {"default": "crossfade"}),
                "transition_frames": ("INT", {"default": 12, "min": 0, "max": 240, "step": 1}),
                "hold_before_transition": ("INT", {"default": 0, "min": 0, "max": 240, "step": 1}),
                "hold_after_transition": ("INT", {"default": 0, "min": 0, "max": 240, "step": 1}),
                "resize_mode": (["match primary", "match secondary"], {"default": "match primary"}),
                "audio_crossfade": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "primary_audio": ("AUDIO",),
                "secondary_audio": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "FLOAT", "INT")
    RETURN_NAMES = ("images", "audio", "duration", "frame_count")
    FUNCTION = "compose_transition"
    CATEGORY = "Geekatplay Studio/Video Editor Suite"

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
            return images
        nchw = images.permute(0, 3, 1, 2)
        resized = F.interpolate(nchw, size=(height, width), mode="bilinear", align_corners=False)
        return resized.permute(0, 2, 3, 1).contiguous()

    @staticmethod
    def _empty_like(images: torch.Tensor) -> torch.Tensor:
        return images[:0].clone()

    @staticmethod
    def _repeat_frame(frame: torch.Tensor, count: int) -> torch.Tensor:
        if count <= 0 or frame.shape[0] == 0:
            return frame[:0].clone()
        return frame.repeat(count, 1, 1, 1)

    @staticmethod
    def _transition_window(images: torch.Tensor, count: int, from_end: bool) -> torch.Tensor:
        if count <= 0:
            return images[:0].clone()
        if images.shape[0] == 0:
            raise ValueError("Cannot build a transition from an empty clip")

        indices = []
        for index in range(count):
            source_index = images.shape[0] - count + index if from_end else index
            source_index = max(0, min(source_index, images.shape[0] - 1))
            indices.append(source_index)
        return images[torch.tensor(indices, dtype=torch.long, device=images.device)]

    @staticmethod
    def _make_transition_frame(primary_frame: torch.Tensor, secondary_frame: torch.Tensor, progress: float, transition_type: str) -> torch.Tensor:
        if transition_type == "crossfade":
            return primary_frame * (1.0 - progress) + secondary_frame * progress

        if transition_type in {"wipe_left", "wipe_right"}:
            width = primary_frame.shape[1]
            split = max(0, min(width, int(round(width * progress))))
            output = primary_frame.clone()
            if transition_type == "wipe_left":
                output[:, :split, :] = secondary_frame[:, :split, :]
            else:
                output[:, width - split:, :] = secondary_frame[:, width - split:, :]
            return output

        if transition_type in {"slide_left", "slide_right"}:
            width = primary_frame.shape[1]
            shift = max(0, min(width, int(round(width * progress))))
            output = torch.zeros_like(primary_frame)
            if transition_type == "slide_left":
                if shift < width:
                    output[:, :width - shift, :] = primary_frame[:, shift:, :]
                if shift > 0:
                    output[:, width - shift:, :] = secondary_frame[:, :shift, :]
            else:
                if shift < width:
                    output[:, shift:, :] = primary_frame[:, :width - shift, :]
                if shift > 0:
                    output[:, :shift, :] = secondary_frame[:, width - shift:, :]
            return output

        return secondary_frame.clone()

    @classmethod
    def _build_transition_frames(cls, primary_images: torch.Tensor, secondary_images: torch.Tensor, transition_frames: int, transition_type: str) -> torch.Tensor:
        if transition_frames <= 0 or transition_type == "cut":
            return cls._empty_like(primary_images)

        primary_window = cls._transition_window(primary_images, transition_frames, from_end=True)
        secondary_window = cls._transition_window(secondary_images, transition_frames, from_end=False)

        frames = []
        for index in range(transition_frames):
            progress = (index + 1) / float(transition_frames + 1)
            frames.append(
                cls._make_transition_frame(primary_window[index], secondary_window[index], progress, transition_type).unsqueeze(0)
            )
        return torch.cat(frames, dim=0)

    @staticmethod
    def _normalize_audio(audio: dict | None, target_rate: int) -> torch.Tensor | None:
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

        return waveform.contiguous()

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

    @classmethod
    def compose_transition(
        cls,
        primary_images,
        secondary_images,
        frame_rate,
        transition_type,
        transition_frames,
        hold_before_transition,
        hold_after_transition,
        resize_mode,
        audio_crossfade,
        primary_audio=None,
        secondary_audio=None,
    ):
        primary_images = cls._ensure_image_batch(primary_images)
        secondary_images = cls._ensure_image_batch(secondary_images)

        if resize_mode == "match primary":
            secondary_images = cls._resize_images(secondary_images, primary_images.shape[1], primary_images.shape[2])
        else:
            primary_images = cls._resize_images(primary_images, secondary_images.shape[1], secondary_images.shape[2])

        transition_frames = 0 if transition_type == "cut" else max(0, int(transition_frames))
        lead_primary = primary_images if transition_frames == 0 else primary_images[:-transition_frames] if primary_images.shape[0] > transition_frames else cls._empty_like(primary_images)
        transition_block = cls._build_transition_frames(primary_images, secondary_images, transition_frames, transition_type)
        secondary_tail = secondary_images if transition_frames == 0 else secondary_images[transition_frames:] if secondary_images.shape[0] > transition_frames else cls._empty_like(secondary_images)

        hold_before = cls._repeat_frame(primary_images[-1:], int(hold_before_transition)) if primary_images.shape[0] > 0 else cls._empty_like(primary_images)

        hold_after_source = secondary_tail[:1] if secondary_tail.shape[0] > 0 else transition_block[-1:] if transition_block.shape[0] > 0 else secondary_images[:1]
        hold_after = cls._repeat_frame(hold_after_source, int(hold_after_transition)) if hold_after_source.shape[0] > 0 else cls._empty_like(primary_images)
        if hold_after.shape[0] > 0 and secondary_tail.shape[0] > 0:
            secondary_tail = secondary_tail[1:]

        blocks = [block for block in (lead_primary, hold_before, transition_block, hold_after, secondary_tail) if block.shape[0] > 0]
        if not blocks:
            blocks = [primary_images[:1]]
        images = torch.cat(blocks, dim=0).contiguous()

        target_rate = 44100
        primary_wave = cls._normalize_audio(primary_audio, target_rate)
        secondary_wave = cls._normalize_audio(secondary_audio, target_rate)
        target_channels = max(primary_wave.shape[0] if primary_wave is not None else 0, secondary_wave.shape[0] if secondary_wave is not None else 0, 1)

        primary_samples = _frame_samples(primary_images.shape[0], frame_rate, target_rate)
        secondary_samples = _frame_samples(secondary_images.shape[0], frame_rate, target_rate)
        lead_samples = _frame_samples(lead_primary.shape[0], frame_rate, target_rate)
        transition_samples = _frame_samples(transition_block.shape[0], frame_rate, target_rate) if transition_block.shape[0] > 0 else 0
        hold_before_samples = _frame_samples(int(hold_before_transition), frame_rate, target_rate)
        hold_after_samples = _frame_samples(int(hold_after_transition), frame_rate, target_rate)

        if primary_wave is None:
            primary_wave = cls._silence(target_channels, primary_samples, images.device, images.dtype)
        else:
            primary_wave = cls._match_channels(primary_wave, target_channels)
            primary_wave = _fit_waveform_samples(primary_wave, primary_samples)

        if secondary_wave is None:
            secondary_wave = cls._silence(target_channels, secondary_samples, images.device, images.dtype)
        else:
            secondary_wave = cls._match_channels(secondary_wave, target_channels)
            secondary_wave = _fit_waveform_samples(secondary_wave, secondary_samples)

        if transition_block.shape[0] > 0:
            primary_lead_audio = primary_wave[:, :lead_samples]
            primary_transition_audio = _fit_waveform_samples(primary_wave[:, lead_samples:], transition_samples)
            secondary_transition_audio = _fit_waveform_samples(secondary_wave[:, :transition_samples], transition_samples)

            if audio_crossfade and transition_samples > 1:
                alpha = torch.linspace(0.0, 1.0, transition_samples, dtype=primary_wave.dtype, device=primary_wave.device).view(1, -1)
                transition_audio = primary_transition_audio * (1.0 - alpha) + secondary_transition_audio * alpha
            elif audio_crossfade and transition_samples == 1:
                transition_audio = (primary_transition_audio + secondary_transition_audio) * 0.5
            else:
                transition_audio = secondary_transition_audio

            audio_blocks = [
                primary_lead_audio,
                cls._silence(target_channels, hold_before_samples, primary_wave.device, primary_wave.dtype),
                transition_audio,
                cls._silence(target_channels, hold_after_samples, primary_wave.device, primary_wave.dtype),
                secondary_wave[:, transition_samples:],
            ]
        else:
            audio_blocks = [
                primary_wave,
                cls._silence(target_channels, hold_before_samples + hold_after_samples, primary_wave.device, primary_wave.dtype),
                secondary_wave,
            ]

        waveform = torch.cat(audio_blocks, dim=1).contiguous()
        target_total_samples = _frame_samples(images.shape[0], frame_rate, target_rate)
        waveform = _fit_waveform_samples(waveform, target_total_samples)
        audio_output = {"waveform": waveform.unsqueeze(0), "sample_rate": target_rate}
        duration_seconds = float(images.shape[0] / float(frame_rate))
        return images, audio_output, duration_seconds, int(images.shape[0])