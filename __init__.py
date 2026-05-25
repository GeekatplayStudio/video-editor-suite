from .ltx_keyframer import GAPKeyframer
from .multi_image_loader import GAPMultiImageLoader
from .ltx_sequencer import GAPSequencer
from .speech_length_calculator import GAPSpeechLengthCalculator
from .load_audio_ui import GAPLoadAudioUI
from .load_video_ui import GAPLoadVideoUI
from .clip_editor import GAPClipEditor
from .video_exporter import GAPVideoExporter
from .transition_composer import GAPTransitionComposer
from .motion_text_fx import GAPMotionTextFX
from .ltx_director import GAPDirector
from .ltx_director_guide import GAPDirectorGuide
from comfy_api.latest import ComfyExtension, io
from typing_extensions import override

class PromptRelay(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            GAPDirector,
            GAPDirectorGuide
        ]

async def comfy_entrypoint() -> PromptRelay:
    return PromptRelay()
    
NODE_CLASS_MAPPINGS = {
    "GAPKeyframer": GAPKeyframer,
    "GAPMultiImageLoader": GAPMultiImageLoader,
    "GAPSequencer": GAPSequencer,
    "GAPSpeechLengthCalculator": GAPSpeechLengthCalculator,
    "GAPLoadAudioUI": GAPLoadAudioUI,
    "GAPLoadVideoUI": GAPLoadVideoUI,
    "GAPClipEditor": GAPClipEditor,
    "GAPVideoExporter": GAPVideoExporter,
    "GAPTransitionComposer": GAPTransitionComposer,
    "GAPMotionTextFX": GAPMotionTextFX,
    "GAPDirector": GAPDirector,
    "GAPDirectorGuide": GAPDirectorGuide,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GAPKeyframer": "Geekatplay Keyframer",
    "GAPMultiImageLoader": "Geekatplay Multi Image Loader",
    "GAPSequencer": "Geekatplay Sequencer",
    "GAPSpeechLengthCalculator": "Geekatplay Speech Timing",
    "GAPLoadAudioUI": "Geekatplay Audio Loader",
    "GAPLoadVideoUI": "Geekatplay Video Loader",
    "GAPClipEditor": "Geekatplay Clip Editor",
    "GAPVideoExporter": "Geekatplay Video Exporter",
    "GAPTransitionComposer": "Geekatplay Transition Composer",
    "GAPMotionTextFX": "Geekatplay Motion Text FX",
    "GAPDirector": "Geekatplay Timeline Director",
    "GAPDirectorGuide": "Geekatplay Director Guide",
}

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']