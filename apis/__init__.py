import warnings

# Import APIs
from apis.video_generation_api import VideoGenerationAPI
from apis.voice_synthesis_api import VoiceSynthesisAPI
from apis.music_generation_api import MusicGenerationAPI
from apis.video_editing_api import VideoEditingAPI

# Deprecation warning
warnings.warn(
    "The APIs in this package are deprecated and will be removed in a future version. "
    "MCP agents now use their own internal API implementations.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    'VideoGenerationAPI',
    'VoiceSynthesisAPI',
    'MusicGenerationAPI',
    'VideoEditingAPI'
] 