import torch
import torch.nn.functional as F


class GAPClipEditor:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 240, "step": 1}),
                "trim_start_frame": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "trim_end_frame": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "playback_speed": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 8.0, "step": 0.05}),
                "loop_count": ("INT", {"default": 1, "min": 1, "max": 16, "step": 1}),
                "reverse": ("BOOLEAN", {"default": False}),
                "ping_pong": ("BOOLEAN", {"default": False}),
                "frame_blend": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05}),
                "audio_gain": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 4.0, "step": 0.05}),
                "fade_in_frames": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "fade_out_frames": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
            },
            "optional": {
                "audio": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "FLOAT", "INT")
    RETURN_NAMES = ("images", "audio", "duration", "frame_count")
    FUNCTION = "edit_clip"
    CATEGORY = "Geekatplay Studio/Video Editor Suite"

    @staticmethod
    def _ensure_image_batch(images: torch.Tensor) -> torch.Tensor:
        if images.ndim == 3:
            return images.unsqueeze(0)
        if images.ndim != 4:
            raise ValueError(f"Expected IMAGE tensor with 3 or 4 dims, got shape {tuple(images.shape)}")
        return images

    @staticmethod
    def _trim_images(images: torch.Tensor, start_frame: int, end_frame: int) -> tuple[torch.Tensor, int, int]:
        total_frames = images.shape[0]
        if total_frames == 0:
            raise ValueError("Input image batch is empty")

        start_frame = max(0, min(start_frame, total_frames - 1))
        end_frame = total_frames if end_frame <= 0 else max(start_frame + 1, min(end_frame, total_frames))
        return images[start_frame:end_frame], start_frame, end_frame

    @staticmethod
    def _ping_pong_images(images: torch.Tensor) -> torch.Tensor:
        if images.shape[0] < 2:
            return images
        return torch.cat((images, torch.flip(images[:-1], dims=[0])), dim=0)

    @staticmethod
    def _retime_images(images: torch.Tensor, playback_speed: float, frame_blend: float) -> torch.Tensor:
        if images.shape[0] <= 1 or abs(playback_speed - 1.0) < 1e-6:
            return images

        target_frames = max(1, int(round(images.shape[0] / playback_speed)))
        positions = torch.linspace(0, images.shape[0] - 1, steps=target_frames, device=images.device, dtype=torch.float32)

        if frame_blend <= 0.0:
            return images[positions.round().long()]

        idx0 = positions.floor().long()
        idx1 = torch.clamp(idx0 + 1, max=images.shape[0] - 1)
        alpha = (positions - idx0.float()) * min(frame_blend, 1.0)
        return images[idx0] * (1.0 - alpha).view(-1, 1, 1, 1) + images[idx1] * alpha.view(-1, 1, 1, 1)

    @staticmethod
    def _ensure_waveform(audio: dict | None, duration_seconds: float) -> tuple[torch.Tensor, int]:
        if not audio or "waveform" not in audio:
            sample_rate = 44100
            sample_count = max(1, int(round(duration_seconds * sample_rate)))
            return torch.zeros((1, 1, sample_count), dtype=torch.float32), sample_rate

        waveform = audio["waveform"]
        if waveform.ndim == 2:
            waveform = waveform.unsqueeze(0)
        if waveform.ndim != 3:
            raise ValueError(f"Expected AUDIO waveform with 2 or 3 dims, got shape {tuple(waveform.shape)}")
        return waveform.clone(), int(audio.get("sample_rate", 44100))

    @staticmethod
    def _ping_pong_audio(waveform: torch.Tensor) -> torch.Tensor:
        if waveform.shape[-1] < 2:
            return waveform
        return torch.cat((waveform, torch.flip(waveform[..., :-1], dims=[-1])), dim=-1)

    @staticmethod
    def _retime_audio(waveform: torch.Tensor, playback_speed: float) -> torch.Tensor:
        if waveform.shape[-1] <= 1 or abs(playback_speed - 1.0) < 1e-6:
            return waveform

        target_samples = max(1, int(round(waveform.shape[-1] / playback_speed)))
        flat_waveform = waveform.reshape(-1, 1, waveform.shape[-1])
        resized = F.interpolate(flat_waveform, size=target_samples, mode="linear", align_corners=False)
        return resized.reshape(waveform.shape[0], waveform.shape[1], target_samples)

    @staticmethod
    def _apply_audio_fades(waveform: torch.Tensor, frame_rate: int, sample_rate: int, fade_in_frames: int, fade_out_frames: int) -> torch.Tensor:
        fade_in_samples = min(waveform.shape[-1], int(round((fade_in_frames / frame_rate) * sample_rate)))
        fade_out_samples = min(waveform.shape[-1], int(round((fade_out_frames / frame_rate) * sample_rate)))

        if fade_in_samples <= 1 and fade_out_samples <= 1:
            return waveform

        envelope = torch.ones(waveform.shape[-1], dtype=waveform.dtype, device=waveform.device)
        if fade_in_samples > 1:
            envelope[:fade_in_samples] = torch.linspace(0.0, 1.0, fade_in_samples, dtype=waveform.dtype, device=waveform.device)
        if fade_out_samples > 1:
            envelope[-fade_out_samples:] = torch.minimum(
                envelope[-fade_out_samples:],
                torch.linspace(1.0, 0.0, fade_out_samples, dtype=waveform.dtype, device=waveform.device),
            )

        return waveform * envelope.view(1, 1, -1)

    def edit_clip(
        self,
        images,
        frame_rate,
        trim_start_frame,
        trim_end_frame,
        playback_speed,
        loop_count,
        reverse,
        ping_pong,
        frame_blend,
        audio_gain,
        fade_in_frames,
        fade_out_frames,
        audio=None,
    ):
        images = self._ensure_image_batch(images).clone()
        images, start_frame, end_frame = self._trim_images(images, trim_start_frame, trim_end_frame)

        if reverse:
            images = torch.flip(images, dims=[0])
        if ping_pong:
            images = self._ping_pong_images(images)
        if loop_count > 1:
            images = images.repeat(loop_count, 1, 1, 1)

        images = self._retime_images(images, playback_speed, frame_blend)
        images = torch.clamp(images.contiguous(), 0.0, 1.0)
        duration_seconds = float(images.shape[0] / frame_rate)

        waveform, sample_rate = self._ensure_waveform(audio, duration_seconds)
        start_sample = int(round((start_frame / frame_rate) * sample_rate))
        end_sample = waveform.shape[-1] if trim_end_frame <= 0 else int(round((end_frame / frame_rate) * sample_rate))
        end_sample = max(start_sample + 1, min(end_sample, waveform.shape[-1]))
        waveform = waveform[..., start_sample:end_sample]

        if reverse:
            waveform = torch.flip(waveform, dims=[-1])
        if ping_pong:
            waveform = self._ping_pong_audio(waveform)
        if loop_count > 1:
            waveform = waveform.repeat(1, 1, loop_count)

        waveform = self._retime_audio(waveform, playback_speed)
        waveform = self._apply_audio_fades(waveform, frame_rate, sample_rate, fade_in_frames, fade_out_frames)
        waveform = waveform * audio_gain

        target_samples = max(1, int(round(duration_seconds * sample_rate)))
        if waveform.shape[-1] != target_samples:
            waveform = self._retime_audio(waveform, waveform.shape[-1] / target_samples)

        audio_output = {"waveform": waveform.contiguous(), "sample_rate": sample_rate}
        return images, audio_output, duration_seconds, int(images.shape[0])