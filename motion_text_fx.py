import os

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont


def _fit_audio_samples(waveform: torch.Tensor, target_samples: int) -> torch.Tensor:
    target_samples = max(1, int(target_samples))
    if waveform.shape[-1] == target_samples:
        return waveform
    resized = F.interpolate(waveform.unsqueeze(0), size=target_samples, mode="linear", align_corners=False)
    return resized[0]


class GAPMotionTextFX:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 240, "step": 1}),
                "overlay_text": ("STRING", {"default": "", "multiline": True}),
                "font_size": ("INT", {"default": 32, "min": 8, "max": 256, "step": 1}),
                "position": (["top-left", "top-center", "top-right", "center", "bottom-left", "bottom-center", "bottom-right", "custom"], {"default": "bottom-center"}),
                "margin_x": ("INT", {"default": 32, "min": 0, "max": 4096, "step": 1}),
                "margin_y": ("INT", {"default": 32, "min": 0, "max": 4096, "step": 1}),
                "text_color": ("STRING", {"default": "#FFFFFF"}),
                "box_color": ("STRING", {"default": "#101010"}),
                "box_opacity": ("FLOAT", {"default": 0.45, "min": 0.0, "max": 1.0, "step": 0.05}),
                "stroke_color": ("STRING", {"default": "#000000"}),
                "stroke_width": ("INT", {"default": 2, "min": 0, "max": 32, "step": 1}),
                "text_start_frame": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "text_end_frame": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "freeze_frame_index": ("INT", {"default": -1, "min": -1, "max": 100000, "step": 1}),
                "freeze_duration_frames": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "ramp_start_frame": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "ramp_end_frame": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "ramp_start_speed": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 8.0, "step": 0.05}),
                "ramp_end_speed": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 8.0, "step": 0.05}),
            },
            "optional": {
                "audio": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "FLOAT", "INT")
    RETURN_NAMES = ("images", "audio", "duration", "frame_count")
    FUNCTION = "apply_fx"
    CATEGORY = "Geekatplay Studio/Video Editor Suite"

    @staticmethod
    def _ensure_image_batch(images: torch.Tensor) -> torch.Tensor:
        if images.ndim == 3:
            images = images.unsqueeze(0)
        if images.ndim != 4:
            raise ValueError(f"Expected IMAGE tensor with 3 or 4 dims, got shape {tuple(images.shape)}")
        return torch.nan_to_num(images.detach().float(), nan=0.0, posinf=1.0, neginf=0.0).clamp(0.0, 1.0)

    @staticmethod
    def _normalize_audio(audio: dict | None, frame_count: int, frame_rate: int, target_rate: int = 44100) -> tuple[torch.Tensor, int]:
        target_samples = max(1, int(round(frame_count / float(frame_rate) * target_rate)))
        if not audio or "waveform" not in audio:
            return torch.zeros((1, target_samples), dtype=torch.float32), target_rate

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
            resampled_samples = max(1, int(round(waveform.shape[-1] * target_rate / float(sample_rate))))
            waveform = _fit_audio_samples(waveform, resampled_samples)

        waveform = _fit_audio_samples(waveform, target_samples)
        return waveform.contiguous(), target_rate

    @staticmethod
    def _parse_color(color: str, alpha_override: int | None = None) -> tuple[int, int, int, int]:
        value = str(color or "#FFFFFF").strip().lstrip("#")
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        if len(value) == 6:
            value += "FF"
        if len(value) != 8:
            value = "FFFFFFFF"

        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
        alpha = int(value[6:8], 16)
        if alpha_override is not None:
            alpha = max(0, min(255, int(alpha_override)))
        return red, green, blue, alpha

    @staticmethod
    def _load_font(font_size: int):
        windir = os.environ.get("WINDIR", r"C:\Windows")
        font_candidates = [
            os.path.join(windir, "Fonts", "arial.ttf"),
            os.path.join(windir, "Fonts", "segoeui.ttf"),
            os.path.join(windir, "Fonts", "verdana.ttf"),
            os.path.join(windir, "Fonts", "tahoma.ttf"),
            os.path.join(os.path.dirname(Image.__file__), "fonts", "DejaVuSans.ttf"),
            "arial.ttf",
            "DejaVuSans.ttf",
            "LiberationSans-Regular.ttf",
            "NotoSans-Regular.ttf",
        ]

        seen = set()
        for font_name in font_candidates:
            if font_name in seen:
                continue
            seen.add(font_name)
            try:
                return ImageFont.truetype(font_name, font_size)
            except Exception:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _text_position(position: str, frame_size: tuple[int, int], text_size: tuple[int, int], margin_x: int, margin_y: int) -> tuple[int, int]:
        frame_w, frame_h = frame_size
        text_w, text_h = text_size
        positions = {
            "top-left": (margin_x, margin_y),
            "top-center": ((frame_w - text_w) // 2, margin_y),
            "top-right": (frame_w - text_w - margin_x, margin_y),
            "center": ((frame_w - text_w) // 2, (frame_h - text_h) // 2),
            "bottom-left": (margin_x, frame_h - text_h - margin_y),
            "bottom-center": ((frame_w - text_w) // 2, frame_h - text_h - margin_y),
            "bottom-right": (frame_w - text_w - margin_x, frame_h - text_h - margin_y),
            "custom": (margin_x, margin_y),
        }
        x, y = positions.get(position, positions["bottom-center"])
        return max(0, x), max(0, y)

    @classmethod
    def _overlay_text(cls, frame: torch.Tensor, text: str, font_size: int, position: str, margin_x: int, margin_y: int, text_color: str, box_color: str, box_opacity: float, stroke_color: str, stroke_width: int) -> torch.Tensor:
        if not str(text or "").strip():
            return frame

        image = (frame.detach().cpu().numpy() * 255.0).round().astype(np.uint8)
        base = Image.fromarray(image, mode="RGB").convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = cls._load_font(font_size)
        text_bbox = draw.multiline_textbbox((0, 0), text, font=font, stroke_width=stroke_width, spacing=4)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        pos_x, pos_y = cls._text_position(position, base.size, (text_w, text_h), margin_x, margin_y)
        pad = max(8, font_size // 4)

        if box_opacity > 0.0:
            box_rgba = cls._parse_color(box_color, int(round(box_opacity * 255.0)))
            draw.rounded_rectangle(
                (pos_x - pad, pos_y - pad, pos_x + text_w + pad, pos_y + text_h + pad),
                radius=max(8, font_size // 3),
                fill=box_rgba,
            )

        draw.multiline_text(
            (pos_x, pos_y),
            text,
            font=font,
            fill=cls._parse_color(text_color),
            stroke_width=stroke_width,
            stroke_fill=cls._parse_color(stroke_color),
            spacing=4,
        )

        composited = Image.alpha_composite(base, overlay).convert("RGB")
        array = np.asarray(composited, dtype=np.float32) / 255.0
        return torch.from_numpy(array).to(frame.device, frame.dtype)

    @staticmethod
    def _insert_freeze(images: torch.Tensor, waveform: torch.Tensor, freeze_frame_index: int, freeze_duration_frames: int, frame_rate: int, sample_rate: int) -> tuple[torch.Tensor, torch.Tensor]:
        if freeze_duration_frames <= 0 or freeze_frame_index < 0:
            return images, waveform

        freeze_frame_index = max(0, min(freeze_frame_index, images.shape[0] - 1))
        freeze_frame = images[freeze_frame_index:freeze_frame_index + 1].repeat(freeze_duration_frames, 1, 1, 1)
        images = torch.cat((images[:freeze_frame_index + 1], freeze_frame, images[freeze_frame_index + 1:]), dim=0)

        insert_sample = max(1, int(round((freeze_frame_index + 1) / float(frame_rate) * sample_rate)))
        insert_sample = min(insert_sample, waveform.shape[-1])
        silence_samples = max(1, int(round(freeze_duration_frames / float(frame_rate) * sample_rate)))
        silence = torch.zeros((waveform.shape[0], silence_samples), dtype=waveform.dtype, device=waveform.device)
        waveform = torch.cat((waveform[:, :insert_sample], silence, waveform[:, insert_sample:]), dim=1)
        return images, waveform

    @staticmethod
    def _ramp_positions(frame_count: int, start_speed: float, end_speed: float) -> torch.Tensor:
        if frame_count <= 1:
            return torch.tensor([0.0], dtype=torch.float32)

        positions = [0.0]
        position = 0.0
        max_index = frame_count - 1
        while position < max_index:
            progress = position / float(max_index) if max_index > 0 else 1.0
            speed = start_speed + (end_speed - start_speed) * progress
            position += max(0.05, float(speed))
            if position < max_index:
                positions.append(position)
        positions.append(float(max_index))
        return torch.tensor(positions, dtype=torch.float32)

    @staticmethod
    def _sample_frames(images: torch.Tensor, positions: torch.Tensor) -> torch.Tensor:
        if positions.numel() == 1:
            return images[:1].clone()

        idx0 = positions.floor().long().clamp(0, images.shape[0] - 1)
        idx1 = (idx0 + 1).clamp(0, images.shape[0] - 1)
        alpha = (positions - idx0.float()).view(-1, 1, 1, 1)
        return images[idx0] * (1.0 - alpha) + images[idx1] * alpha

    @classmethod
    def _apply_speed_ramp(cls, images: torch.Tensor, waveform: torch.Tensor, frame_rate: int, sample_rate: int, ramp_start_frame: int, ramp_end_frame: int, ramp_start_speed: float, ramp_end_speed: float) -> tuple[torch.Tensor, torch.Tensor]:
        if images.shape[0] <= 1:
            return images, waveform

        ramp_start_frame = max(0, min(ramp_start_frame, images.shape[0] - 1))
        ramp_end_frame = images.shape[0] if ramp_end_frame <= 0 else max(ramp_start_frame + 1, min(ramp_end_frame, images.shape[0]))
        if ramp_end_frame - ramp_start_frame <= 1:
            return images, waveform

        if abs(ramp_start_speed - 1.0) < 1e-6 and abs(ramp_end_speed - 1.0) < 1e-6:
            return images, waveform

        segment = images[ramp_start_frame:ramp_end_frame]
        positions = cls._ramp_positions(segment.shape[0], ramp_start_speed, ramp_end_speed)
        retimed_segment = cls._sample_frames(segment, positions).contiguous()
        images = torch.cat((images[:ramp_start_frame], retimed_segment, images[ramp_end_frame:]), dim=0)

        start_sample = max(0, int(round(ramp_start_frame / float(frame_rate) * sample_rate)))
        end_sample = max(start_sample + 1, int(round(ramp_end_frame / float(frame_rate) * sample_rate)))
        end_sample = min(end_sample, waveform.shape[-1])
        retimed_audio_samples = max(1, int(round(retimed_segment.shape[0] / float(frame_rate) * sample_rate)))
        retimed_audio = _fit_audio_samples(waveform[:, start_sample:end_sample], retimed_audio_samples)
        waveform = torch.cat((waveform[:, :start_sample], retimed_audio, waveform[:, end_sample:]), dim=1)
        return images, waveform

    def apply_fx(
        self,
        images,
        frame_rate,
        overlay_text,
        font_size,
        position,
        margin_x,
        margin_y,
        text_color,
        box_color,
        box_opacity,
        stroke_color,
        stroke_width,
        text_start_frame,
        text_end_frame,
        freeze_frame_index,
        freeze_duration_frames,
        ramp_start_frame,
        ramp_end_frame,
        ramp_start_speed,
        ramp_end_speed,
        audio=None,
    ):
        images = self._ensure_image_batch(images)
        waveform, sample_rate = self._normalize_audio(audio, images.shape[0], frame_rate)
        images, waveform = self._insert_freeze(images, waveform, freeze_frame_index, freeze_duration_frames, frame_rate, sample_rate)
        images, waveform = self._apply_speed_ramp(images, waveform, frame_rate, sample_rate, ramp_start_frame, ramp_end_frame, ramp_start_speed, ramp_end_speed)

        text = str(overlay_text or "").strip()
        if text:
            start_frame = max(0, min(int(text_start_frame), images.shape[0] - 1))
            end_frame = images.shape[0] if int(text_end_frame) <= 0 else max(start_frame + 1, min(int(text_end_frame), images.shape[0]))
            for frame_index in range(start_frame, end_frame):
                images[frame_index] = self._overlay_text(
                    images[frame_index],
                    text,
                    int(font_size),
                    position,
                    int(margin_x),
                    int(margin_y),
                    text_color,
                    box_color,
                    float(box_opacity),
                    stroke_color,
                    int(stroke_width),
                )

        duration_seconds = float(images.shape[0] / float(frame_rate))
        target_samples = max(1, int(round(duration_seconds * sample_rate)))
        waveform = _fit_audio_samples(waveform, target_samples).contiguous()
        audio_output = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
        return images.contiguous(), audio_output, duration_seconds, int(images.shape[0])