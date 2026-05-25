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


class GAPLayerComposer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_images": ("IMAGE",),
                "overlay_images": ("IMAGE",),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 240, "step": 1}),
                "overlay_start_frame": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "overlay_end_frame": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "overlay_scale": ("FLOAT", {"default": 1.0, "min": 0.05, "max": 8.0, "step": 0.05}),
                "position": (["top-left", "top-center", "top-right", "center", "bottom-left", "bottom-center", "bottom-right", "custom"], {"default": "top-right"}),
                "margin_x": ("INT", {"default": 32, "min": 0, "max": 4096, "step": 1}),
                "margin_y": ("INT", {"default": 32, "min": 0, "max": 4096, "step": 1}),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05}),
                "fade_in_frames": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "fade_out_frames": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "blend_mode": (["normal", "screen", "add", "multiply", "overlay"], {"default": "normal"}),
                "playback_mode": (["trim", "loop", "hold last"], {"default": "trim"}),
                "extend_output": ("BOOLEAN", {"default": False}),
                "base_audio_gain": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 4.0, "step": 0.05}),
                "overlay_audio_gain": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 4.0, "step": 0.05}),
                "audio_ducking": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05}),
            },
            "optional": {
                "base_audio": ("AUDIO",),
                "overlay_audio": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "FLOAT", "INT")
    RETURN_NAMES = ("images", "audio", "duration", "frame_count")
    FUNCTION = "compose_layers"
    CATEGORY = "Geekatplay Studio/Video Editor Suite"

    @staticmethod
    def _ensure_image_batch(images: torch.Tensor) -> torch.Tensor:
        if images.ndim == 3:
            images = images.unsqueeze(0)
        if images.ndim != 4:
            raise ValueError(f"Expected IMAGE tensor with 3 or 4 dims, got shape {tuple(images.shape)}")
        return torch.nan_to_num(images.detach().float(), nan=0.0, posinf=1.0, neginf=0.0).clamp(0.0, 1.0)

    @staticmethod
    def _resize_images(images: torch.Tensor, scale: float) -> torch.Tensor:
        scale = max(0.05, float(scale))
        if abs(scale - 1.0) < 1e-6:
            return images
        target_h = max(1, int(round(images.shape[1] * scale)))
        target_w = max(1, int(round(images.shape[2] * scale)))
        nchw = images.permute(0, 3, 1, 2)
        resized = F.interpolate(nchw, size=(target_h, target_w), mode="bilinear", align_corners=False)
        return resized.permute(0, 2, 3, 1).contiguous()

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

    @staticmethod
    def _position(position: str, frame_size: tuple[int, int], overlay_size: tuple[int, int], margin_x: int, margin_y: int) -> tuple[int, int]:
        frame_w, frame_h = frame_size
        overlay_w, overlay_h = overlay_size
        positions = {
            "top-left": (margin_x, margin_y),
            "top-center": ((frame_w - overlay_w) // 2, margin_y),
            "top-right": (frame_w - overlay_w - margin_x, margin_y),
            "center": ((frame_w - overlay_w) // 2, (frame_h - overlay_h) // 2),
            "bottom-left": (margin_x, frame_h - overlay_h - margin_y),
            "bottom-center": ((frame_w - overlay_w) // 2, frame_h - overlay_h - margin_y),
            "bottom-right": (frame_w - overlay_w - margin_x, frame_h - overlay_h - margin_y),
            "custom": (margin_x, margin_y),
        }
        return positions.get(position, positions["top-right"])

    @staticmethod
    def _blend(base_region: torch.Tensor, overlay_region: torch.Tensor, opacity: float, blend_mode: str) -> torch.Tensor:
        opacity = max(0.0, min(1.0, float(opacity)))
        if opacity <= 0.0:
            return base_region

        if blend_mode == "screen":
            blended = 1.0 - (1.0 - base_region) * (1.0 - overlay_region)
        elif blend_mode == "add":
            blended = torch.clamp(base_region + overlay_region, 0.0, 1.0)
        elif blend_mode == "multiply":
            blended = base_region * overlay_region
        elif blend_mode == "overlay":
            blended = torch.where(
                base_region <= 0.5,
                2.0 * base_region * overlay_region,
                1.0 - 2.0 * (1.0 - base_region) * (1.0 - overlay_region),
            )
        else:
            blended = overlay_region

        return torch.clamp(base_region * (1.0 - opacity) + blended * opacity, 0.0, 1.0)

    @classmethod
    def _apply_overlay(cls, base_frame: torch.Tensor, overlay_frame: torch.Tensor, opacity: float, blend_mode: str, position: str, margin_x: int, margin_y: int) -> torch.Tensor:
        frame_h, frame_w = base_frame.shape[0], base_frame.shape[1]
        overlay_h, overlay_w = overlay_frame.shape[0], overlay_frame.shape[1]
        pos_x, pos_y = cls._position(position, (frame_w, frame_h), (overlay_w, overlay_h), margin_x, margin_y)

        dest_x0 = max(0, pos_x)
        dest_y0 = max(0, pos_y)
        dest_x1 = min(frame_w, pos_x + overlay_w)
        dest_y1 = min(frame_h, pos_y + overlay_h)
        if dest_x0 >= dest_x1 or dest_y0 >= dest_y1:
            return base_frame

        src_x0 = max(0, -pos_x)
        src_y0 = max(0, -pos_y)
        src_x1 = src_x0 + (dest_x1 - dest_x0)
        src_y1 = src_y0 + (dest_y1 - dest_y0)

        composited = base_frame.clone()
        base_region = composited[dest_y0:dest_y1, dest_x0:dest_x1, :]
        overlay_region = overlay_frame[src_y0:src_y1, src_x0:src_x1, :]
        composited[dest_y0:dest_y1, dest_x0:dest_x1, :] = cls._blend(base_region, overlay_region, opacity, blend_mode)
        return composited

    @staticmethod
    def _envelope(length: int, fade_in_frames: int, fade_out_frames: int, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
        length = max(0, int(length))
        if length <= 0:
            return torch.zeros((0,), dtype=dtype, device=device)

        envelope = torch.ones(length, dtype=dtype, device=device)
        fade_in = min(length, max(0, int(fade_in_frames)))
        fade_out = min(length, max(0, int(fade_out_frames)))

        if fade_in > 1:
            envelope[:fade_in] = torch.linspace(0.0, 1.0, fade_in, dtype=dtype, device=device)
        if fade_out > 1:
            envelope[-fade_out:] = torch.minimum(
                envelope[-fade_out:],
                torch.linspace(1.0, 0.0, fade_out, dtype=dtype, device=device),
            )
        return envelope

    @staticmethod
    def _overlay_indices(active_length: int, overlay_length: int, playback_mode: str) -> torch.Tensor:
        if active_length <= 0:
            return torch.zeros((0,), dtype=torch.long)
        if playback_mode == "loop":
            return torch.arange(active_length, dtype=torch.long) % overlay_length
        if playback_mode == "hold last":
            return torch.clamp(torch.arange(active_length, dtype=torch.long), max=overlay_length - 1)
        return torch.arange(active_length, dtype=torch.long)

    @staticmethod
    def _repeat_audio(waveform: torch.Tensor, target_samples: int) -> torch.Tensor:
        if waveform.shape[-1] >= target_samples:
            return waveform[:, :target_samples]
        repeats = max(1, (target_samples + waveform.shape[-1] - 1) // waveform.shape[-1])
        tiled = waveform.repeat(1, repeats)
        return tiled[:, :target_samples]

    def compose_layers(
        self,
        base_images,
        overlay_images,
        frame_rate,
        overlay_start_frame,
        overlay_end_frame,
        overlay_scale,
        position,
        margin_x,
        margin_y,
        opacity,
        fade_in_frames,
        fade_out_frames,
        blend_mode,
        playback_mode,
        extend_output,
        base_audio_gain,
        overlay_audio_gain,
        audio_ducking,
        base_audio=None,
        overlay_audio=None,
    ):
        base_images = self._ensure_image_batch(base_images)
        overlay_images = self._resize_images(self._ensure_image_batch(overlay_images), overlay_scale)

        if base_images.shape[0] == 0:
            raise ValueError("Base clip is empty")
        if overlay_images.shape[0] == 0:
            raise ValueError("Overlay clip is empty")

        base_count = int(base_images.shape[0])
        overlay_count = int(overlay_images.shape[0])
        overlay_start_frame = max(0, int(overlay_start_frame))

        requested_length = overlay_count if int(overlay_end_frame) <= 0 else max(0, int(overlay_end_frame) - overlay_start_frame)
        if playback_mode == "trim":
            active_length = min(requested_length, overlay_count)
        else:
            active_length = requested_length

        output_count = max(base_count, overlay_start_frame + active_length) if extend_output else base_count
        active_length = max(0, min(active_length, output_count - overlay_start_frame))

        if output_count > base_count:
            extension = base_images[-1:].repeat(output_count - base_count, 1, 1, 1)
            images = torch.cat((base_images, extension), dim=0)
        else:
            images = base_images[:output_count].clone()

        if active_length > 0:
            indices = self._overlay_indices(active_length, overlay_count, playback_mode)
            envelope = self._envelope(active_length, fade_in_frames, fade_out_frames, images.device, images.dtype)
            for offset, overlay_index in enumerate(indices.tolist()):
                composite_index = overlay_start_frame + offset
                if composite_index >= images.shape[0]:
                    break
                frame_opacity = float(opacity) * float(envelope[offset].item())
                images[composite_index] = self._apply_overlay(
                    images[composite_index],
                    overlay_images[overlay_index],
                    frame_opacity,
                    blend_mode,
                    position,
                    int(margin_x),
                    int(margin_y),
                )

        target_rate = 44100
        base_wave = self._normalize_audio(base_audio, target_rate)
        overlay_wave = self._normalize_audio(overlay_audio, target_rate)

        base_samples = _frame_samples(base_count, frame_rate, target_rate)
        output_samples = _frame_samples(output_count, frame_rate, target_rate)
        overlay_clip_samples = _frame_samples(overlay_count, frame_rate, target_rate)

        channel_count = max(
            base_wave.shape[0] if base_wave is not None else 0,
            overlay_wave.shape[0] if overlay_wave is not None else 0,
            1,
        )
        mix = self._silence(channel_count, output_samples, images.device, images.dtype)

        if base_wave is None:
            base_wave = self._silence(channel_count, base_samples, images.device, images.dtype)
        else:
            base_wave = self._match_channels(base_wave, channel_count)
            base_wave = _fit_waveform_samples(base_wave, base_samples)
        mix[:, :base_samples] = base_wave[:, :base_samples] * float(base_audio_gain)

        if active_length > 0:
            start_sample = min(output_samples, _frame_samples(overlay_start_frame, frame_rate, target_rate))
            active_samples = max(0, min(output_samples - start_sample, _frame_samples(active_length, frame_rate, target_rate)))
            if active_samples > 0:
                audio_envelope = self._envelope(active_samples, fade_in_frames, fade_out_frames, mix.device, mix.dtype)
                duck = 1.0 - max(0.0, min(1.0, float(audio_ducking))) * audio_envelope.view(1, -1)
                mix[:, start_sample:start_sample + active_samples] *= duck

                if overlay_wave is not None and float(overlay_audio_gain) > 0.0:
                    overlay_wave = self._match_channels(overlay_wave, channel_count)
                    overlay_wave = _fit_waveform_samples(overlay_wave, overlay_clip_samples)

                    if playback_mode == "loop":
                        overlay_buffer = self._repeat_audio(overlay_wave, active_samples)
                    else:
                        overlay_buffer = self._silence(channel_count, active_samples, mix.device, mix.dtype)
                        copy_samples = min(active_samples, overlay_wave.shape[-1])
                        overlay_buffer[:, :copy_samples] = overlay_wave[:, :copy_samples]

                    overlay_buffer = overlay_buffer * float(overlay_audio_gain)
                    overlay_buffer = overlay_buffer * audio_envelope.view(1, -1)
                    mix[:, start_sample:start_sample + active_samples] += overlay_buffer[:, :active_samples]

        duration_seconds = float(output_count / float(frame_rate))
        audio_output = {"waveform": mix.unsqueeze(0).contiguous(), "sample_rate": target_rate}
        return images.contiguous(), audio_output, duration_seconds, int(output_count)
