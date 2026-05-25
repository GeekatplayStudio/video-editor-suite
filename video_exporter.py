import os
from fractions import Fraction

import av
import folder_paths
import numpy as np
import torch


CONTAINER_EXTENSIONS = {
    "mp4": "mp4",
    "mov": "mov",
    "webm": "webm",
    "mkv": "mkv",
    "gif": "gif",
}

CONTAINER_VIDEO_CODECS = {
    "mp4": ["libx264", "h264", "mpeg4"],
    "mov": ["libx264", "h264", "prores_ks", "mpeg4"],
    "webm": ["libvpx-vp9", "vp9", "libvpx"],
    "mkv": ["libx264", "h264", "libx265", "hevc", "ffv1"],
    "gif": ["gif"],
}

CONTAINER_AUDIO_CODECS = {
    "mp4": ["aac", "mp3", "pcm_s16le"],
    "mov": ["aac", "pcm_s16le", "mp3"],
    "webm": ["libopus", "opus", "libvorbis", "vorbis"],
    "mkv": ["aac", "libopus", "opus", "libvorbis", "vorbis", "pcm_s16le"],
    "gif": ["none"],
}

PIXEL_FORMAT_DEFAULTS = {
    "gif": "rgb8",
    "webm": "yuv420p",
    "mp4": "yuv420p",
    "mov": "yuv420p",
    "mkv": "yuv420p",
}


def _parse_bitrate(bitrate: str) -> int | None:
    value = str(bitrate or "").strip().lower()
    if not value:
        return None

    multiplier = 1
    if value.endswith("k"):
        multiplier = 1000
        value = value[:-1]
    elif value.endswith("m"):
        multiplier = 1000000
        value = value[:-1]

    try:
        return max(1, int(float(value) * multiplier))
    except ValueError:
        return None


def _unique_codec_candidates(requested: str, defaults: list[str]) -> list[str]:
    ordered: list[str] = []
    if requested and requested != "auto":
        ordered.append(requested)
    ordered.extend(defaults)

    unique: list[str] = []
    for codec in ordered:
        if codec not in unique:
            unique.append(codec)
    return unique


def _normalize_images(images: torch.Tensor) -> torch.Tensor:
    if images.ndim == 3:
        images = images.unsqueeze(0)
    if images.ndim != 4:
        raise ValueError(f"Expected IMAGE tensor with 3 or 4 dims, got shape {tuple(images.shape)}")
    return torch.nan_to_num(images.detach().float().cpu(), nan=0.0, posinf=1.0, neginf=0.0).clamp(0.0, 1.0)


def _normalize_audio(audio: dict | None) -> tuple[torch.Tensor, int] | tuple[None, None]:
    if not audio or "waveform" not in audio:
        return None, None

    waveform = audio["waveform"]
    if waveform.ndim == 2:
        waveform = waveform.unsqueeze(0)
    if waveform.ndim != 3:
        raise ValueError(f"Expected AUDIO waveform with 2 or 3 dims, got shape {tuple(waveform.shape)}")

    waveform = torch.nan_to_num(waveform[0].detach().float().cpu(), nan=0.0, posinf=0.0, neginf=0.0)
    if waveform.shape[0] > 2:
        waveform = waveform[:2]
    if waveform.shape[0] == 0 or waveform.shape[-1] == 0:
        return None, None

    return waveform.contiguous(), int(audio.get("sample_rate", 44100))


def _ensure_even_dimensions(images: torch.Tensor, pixel_format: str) -> torch.Tensor:
    if pixel_format not in {"yuv420p", "yuva420p"}:
        return images

    frame_count, height, width, channels = images.shape
    target_height = height + (height % 2)
    target_width = width + (width % 2)
    if target_height == height and target_width == width:
        return images

    padded = torch.zeros((frame_count, target_height, target_width, channels), dtype=images.dtype)
    padded[:, :height, :width, :] = images
    return padded


def _resolve_output_path(filename_prefix: str, width: int, height: int, extension: str) -> tuple[str, str]:
    full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
        filename_prefix,
        folder_paths.get_output_directory(),
        width,
        height,
    )

    os.makedirs(full_output_folder, exist_ok=True)
    base_name = filename.replace("%batch_num%", "0")
    file_name = f"{base_name}_{int(counter):05d}.{extension}"
    output_path = os.path.join(full_output_folder, file_name)
    relative_path = os.path.join(subfolder, file_name) if subfolder else file_name
    return output_path, relative_path.replace(os.sep, "/")


def _add_video_stream(container, container_name: str, requested_codec: str, frame_rate: int, width: int, height: int, pixel_format: str, preset: str, crf: int, bitrate: str):
    candidates = _unique_codec_candidates(requested_codec, CONTAINER_VIDEO_CODECS[container_name])
    last_error = None
    for codec in candidates:
        try:
            stream = container.add_stream(codec, rate=frame_rate)
            stream.width = width
            stream.height = height
            stream.pix_fmt = pixel_format

            bit_rate = _parse_bitrate(bitrate)
            if bit_rate is not None:
                stream.bit_rate = bit_rate

            options: dict[str, str] = {}
            if codec != "gif":
                options["crf"] = str(crf)
            if any(token in codec for token in ("264", "265")):
                options["preset"] = preset
            if codec in {"libvpx-vp9", "vp9", "libvpx"}:
                options.setdefault("deadline", "good")
            if options:
                stream.options = options

            return stream, codec
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Unable to create a video stream for {container_name}: {last_error}")


def _add_audio_stream(container, container_name: str, requested_codec: str, sample_rate: int, bitrate: str):
    candidates = _unique_codec_candidates(requested_codec, CONTAINER_AUDIO_CODECS[container_name])
    last_error = None
    for codec in candidates:
        if codec == "none":
            return None, "none"
        try:
            stream = container.add_stream(codec, rate=sample_rate)
            bit_rate = _parse_bitrate(bitrate)
            if bit_rate is not None:
                stream.bit_rate = bit_rate
            return stream, codec
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Unable to create an audio stream for {container_name}: {last_error}")


def _encode_video_frames(container, stream, images: torch.Tensor, frame_rate: int) -> None:
    time_base = Fraction(1, frame_rate)
    image_array = (images.numpy() * 255.0).round().astype(np.uint8)
    for frame_index, image in enumerate(image_array):
        video_frame = av.VideoFrame.from_ndarray(image, format="rgb24")
        video_frame.pts = frame_index
        video_frame.time_base = time_base
        for packet in stream.encode(video_frame):
            container.mux(packet)

    for packet in stream.encode(None):
        container.mux(packet)


def _encode_audio_frames(container, stream, waveform: torch.Tensor, sample_rate: int) -> None:
    if stream is None:
        return

    layout = "mono" if waveform.shape[0] == 1 else "stereo"
    time_base = Fraction(1, sample_rate)
    audio_array = waveform.numpy().astype(np.float32, copy=False)

    chunk_size = 2048
    sample_cursor = 0
    for start in range(0, audio_array.shape[1], chunk_size):
        chunk = audio_array[:, start:start + chunk_size]
        if chunk.shape[1] == 0:
            continue

        audio_frame = av.AudioFrame.from_ndarray(chunk, format="fltp", layout=layout)
        audio_frame.sample_rate = sample_rate
        audio_frame.pts = sample_cursor
        audio_frame.time_base = time_base
        sample_cursor += chunk.shape[1]

        for packet in stream.encode(audio_frame):
            container.mux(packet)

    for packet in stream.encode(None):
        container.mux(packet)


class GAPVideoExporter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 240, "step": 1}),
                "filename_prefix": ("STRING", {"default": "Geekatplay/VideoEditorSuite/render"}),
                "container": (["mp4", "mov", "webm", "mkv", "gif"], {"default": "mp4"}),
                "video_codec": (["auto", "libx264", "h264", "mpeg4", "prores_ks", "libx265", "hevc", "libvpx-vp9", "vp9", "gif", "ffv1"], {"default": "auto"}),
                "pixel_format": (["auto", "yuv420p", "yuv444p", "rgb24", "rgb8"], {"default": "auto"}),
                "preset": (["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"], {"default": "medium"}),
                "crf": ("INT", {"default": 18, "min": 0, "max": 51, "step": 1}),
                "video_bitrate": ("STRING", {"default": ""}),
                "audio_codec": (["auto", "aac", "libopus", "opus", "libvorbis", "vorbis", "pcm_s16le", "mp3", "none"], {"default": "auto"}),
                "audio_bitrate": ("STRING", {"default": "192k"}),
                "match_video_length": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "audio": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("file_path", "relative_path")
    FUNCTION = "export_video"
    OUTPUT_NODE = True
    CATEGORY = "Geekatplay Studio/Video Editor Suite"

    def export_video(
        self,
        images,
        frame_rate,
        filename_prefix,
        container,
        video_codec,
        pixel_format,
        preset,
        crf,
        video_bitrate,
        audio_codec,
        audio_bitrate,
        match_video_length,
        audio=None,
    ):
        images = _normalize_images(images)
        pixel_format = PIXEL_FORMAT_DEFAULTS[container] if pixel_format == "auto" else pixel_format
        images = _ensure_even_dimensions(images, pixel_format)

        frame_rate = max(1, int(frame_rate))
        duration_seconds = images.shape[0] / float(frame_rate)
        output_path, relative_path = _resolve_output_path(
            filename_prefix,
            int(images.shape[2]),
            int(images.shape[1]),
            CONTAINER_EXTENSIONS[container],
        )

        waveform, sample_rate = _normalize_audio(audio)
        if waveform is not None and match_video_length:
            target_samples = max(1, int(round(duration_seconds * sample_rate)))
            if waveform.shape[-1] < target_samples:
                padded = torch.zeros((waveform.shape[0], target_samples), dtype=waveform.dtype)
                padded[:, :waveform.shape[-1]] = waveform
                waveform = padded
            elif waveform.shape[-1] > target_samples:
                waveform = waveform[:, :target_samples]

        with av.open(output_path, mode="w", format=container) as output_container:
            video_stream, _selected_video_codec = _add_video_stream(
                output_container,
                container,
                video_codec,
                frame_rate,
                int(images.shape[2]),
                int(images.shape[1]),
                pixel_format,
                preset,
                int(crf),
                video_bitrate,
            )

            audio_stream = None
            if waveform is not None and container != "gif":
                audio_stream, _selected_audio_codec = _add_audio_stream(
                    output_container,
                    container,
                    audio_codec,
                    sample_rate,
                    audio_bitrate,
                )

            _encode_video_frames(output_container, video_stream, images, frame_rate)
            if waveform is not None and audio_stream is not None:
                _encode_audio_frames(output_container, audio_stream, waveform, sample_rate)

        return output_path, relative_path