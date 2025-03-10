import os
from enum import Enum
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# 加载环境变量
load_dotenv()

class VideoGenerationModel(str, Enum):
    """可选的视频生成模型"""
    KELING = "keling"  # 可灵
    PIKA = "pika"
    RUNWAY = "runway"
    WAN = "wan"

class VoiceSynthesisTool(str, Enum):
    """可选的语音合成工具"""
    ELEVENLABS = "elevenlabs"
    PLAYHT = "playht"
    DEEPSEEK_TENCENT = "deepseek_tencent"

class MusicGenerationTool(str, Enum):
    """可选的音乐生成工具"""
    SUNO = "suno"
    AIVA = "aiva"
    SOUNDRAW = "soundraw"

class EditingTool(str, Enum):
    """可选的视频编辑工具"""
    RUNWAY = "runway"
    DESCRIPT = "descript"
    KAPWING = "kapwing"

# API配置
API_KEYS = {
    # 视频生成API密钥
    "keling": os.getenv("KELING_API_KEY", ""),
    "pika": os.getenv("PIKA_API_KEY", ""),
    "runway": os.getenv("RUNWAY_API_KEY", ""),
    "wan": os.getenv("WAN_API_KEY", ""),
    
    # 语音合成API密钥
    "elevenlabs": os.getenv("ELEVENLABS_API_KEY", ""),
    "playht": os.getenv("PLAYHT_API_KEY", ""),
    "deepseek_tencent": os.getenv("DEEPSEEK_TENCENT_API_KEY", ""),
    
    # 音乐生成API密钥
    "suno": os.getenv("SUNO_API_KEY", ""),
    "aiva": os.getenv("AIVA_API_KEY", ""),
    "soundraw": os.getenv("SOUNDRAW_API_KEY", ""),
    
    # 编辑工具API密钥
    "runway_edit": os.getenv("RUNWAY_EDIT_API_KEY", ""),
    "descript": os.getenv("DESCRIPT_API_KEY", ""),
    "kapwing": os.getenv("KAPWING_API_KEY", ""),
    
    # TikTok API密钥
    "tiktok": os.getenv("TIKTOK_API_KEY", ""),
    
    # OpenAI API密钥 (用于代理的推理)
    "openai": os.getenv("OPENAI_API_KEY", ""),
}

# 系统配置
SYSTEM_CONFIG = {
    "temp_dir": "./temp",
    "output_dir": "./output",
    "log_dir": "./logs",
    "max_retries": 3,
    "request_timeout": 60,
    "default_video_model": "wan",
    "default_voice_tool": "elevenlabs",
    "default_music_tool": "suno",
    "default_editing_tool": "runway",
    "default_resolution": "1080x1920",  # TikTok竖屏视频
    "default_language": "zh",
    "api_rate_limit": {
        "max_requests_per_minute": 60,
        "max_requests_per_day": 1000
    },
    "cache_enabled": True,
    "cache_ttl": 3600,  # 缓存有效期（秒）
    "debug_mode": True
}

# 模型具体配置
MODEL_CONFIG = {
    "keling": {
        "name": "可灵视频生成",
        "base_url": "https://api.keling.ai/v1",
        "version": "1.0",
        "max_duration": 60,  # 最大视频时长（秒）
        "supported_resolutions": ["720x1280", "1080x1920", "2160x3840"],
        "supported_styles": ["realistic", "anime", "cartoon", "3d", "stylized"],
        "default_style": "realistic",
        "fps": 24,
        "temperature": 0.7,
        "top_p": 0.9,
        "timeout": 120,
        "max_retries": 3,
        "rate_limit": {
            "requests_per_minute": 10,
            "requests_per_day": 100
        }
    },
    "pika": {
        "name": "Pika Labs",
        "base_url": "https://api.pika.art/v1",
        "version": "1.0",
        "max_duration": 30,
        "supported_resolutions": ["720x1280", "1080x1920"],
        "supported_styles": ["realistic", "anime", "cinematic", "stylized"],
        "default_style": "cinematic",
        "fps": 30,
        "temperature": 0.8,
        "top_p": 0.95,
        "timeout": 180,
        "max_retries": 3,
        "rate_limit": {
            "requests_per_minute": 5,
            "requests_per_day": 50
        }
    },
    "runway": {
        "name": "Runway Gen-2",
        "base_url": "https://api.runwayml.com/v1",
        "version": "2.0",
        "max_duration": 20,
        "supported_resolutions": ["768x1344", "1080x1920"],
        "supported_styles": ["cinematic", "realistic", "stylized"],
        "default_style": "cinematic",
        "fps": 24,
        "temperature": 0.75,
        "top_p": 0.9,
        "timeout": 150,
        "max_retries": 3,
        "rate_limit": {
            "requests_per_minute": 6,
            "requests_per_day": 60
        }
    },
    "wan": {
        "name": "Wan动画生成",
        "base_url": "https://api.wan.video/v1",
        "version": "2.1",
        "max_duration": 45,
        "supported_resolutions": ["720x1280", "1080x1920"],
        "supported_styles": ["anime", "cartoon", "3d", "pixel"],
        "default_style": "anime",
        "fps": 24,
        "temperature": 0.7,
        "top_p": 0.9,
        "timeout": 120,
        "max_retries": 3,
        "rate_limit": {
            "requests_per_minute": 8,
            "requests_per_day": 80
        }
    }
}

# 音频工具配置
AUDIO_CONFIG = {
    "elevenlabs": {
        "name": "ElevenLabs",
        "base_url": "https://api.elevenlabs.io/v1",
        "version": "1.0",
        "timeout": 60,
        "max_retries": 3,
        "speed": 1.0,  # 语速（0.5-2.0）
        "pitch": 0,    # 音调调整（-10到10）
        "volume": 1.0, # 音量（0.1-2.0）
        "voices": {
            "zh": ["xiaoming", "xiaohong", "xiaohua"],
            "en": ["adam", "emily", "josh"]
        },
        "rate_limit": {
            "requests_per_minute": 20,
            "requests_per_day": 500
        }
    },
    "playht": {
        "name": "Play.ht",
        "base_url": "https://api.play.ht/v1",
        "version": "1.0",
        "timeout": 60,
        "max_retries": 3,
        "speed": 1.0,
        "pitch": 0,
        "volume": 1.0,
        "voices": {
            "zh": ["zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural"],
            "en": ["en-US-JennyNeural", "en-US-GuyNeural"]
        },
        "rate_limit": {
            "requests_per_minute": 15,
            "requests_per_day": 300
        }
    },
    "deepseek_tencent": {
        "name": "腾讯云语音合成",
        "base_url": "https://tts.tencentcloudapi.com",
        "version": "2.0",
        "timeout": 30,
        "max_retries": 2,
        "speed": 1.0,
        "pitch": 0,
        "volume": 1.0,
        "voices": {
            "zh": ["aixia", "aixiaonan", "aixiaoxing"],
            "en": ["aixijenny", "aixitom"]
        },
        "rate_limit": {
            "requests_per_minute": 30,
            "requests_per_day": 1000
        }
    },
    "suno": {
        "name": "Suno AI",
        "base_url": "https://api.suno.ai/v1",
        "version": "1.0",
        "timeout": 120,
        "max_retries": 3,
        "tempo": "medium",  # slow, medium, fast
        "intensity": 0.7,   # 0.1-1.0
        "styles": ["pop", "rock", "electronic", "ambient", "cinematic", "jazz"],
        "rate_limit": {
            "requests_per_minute": 5,
            "requests_per_day": 50
        }
    },
    "aiva": {
        "name": "AIVA",
        "base_url": "https://api.aiva.ai/v1",
        "version": "1.0",
        "timeout": 180,
        "max_retries": 3,
        "tempo": "medium",
        "intensity": 0.7,
        "styles": ["cinematic", "ambient", "electronic", "orchestral"],
        "rate_limit": {
            "requests_per_minute": 3,
            "requests_per_day": 30
        }
    },
    "soundraw": {
        "name": "SoundRaw",
        "base_url": "https://api.soundraw.io/v1",
        "version": "1.0",
        "timeout": 90,
        "max_retries": 3,
        "tempo": "medium",
        "intensity": 0.7,
        "styles": ["pop", "ambient", "cinematic", "lofi", "electronic"],
        "rate_limit": {
            "requests_per_minute": 6,
            "requests_per_day": 60
        }
    }
}

# 编辑工具配置
EDITING_CONFIG = {
    "runway": {
        "name": "Runway",
        "base_url": "https://api.runwayml.com/v1",
        "version": "1.0",
        "timeout": 180,
        "max_retries": 3,
        "supported_effects": ["color_grading", "stabilization", "transitions", "text_overlay"],
        "rate_limit": {
            "requests_per_minute": 5,
            "requests_per_day": 50
        }
    },
    "descript": {
        "name": "Descript",
        "base_url": "https://api.descript.com/v1",
        "version": "1.0",
        "timeout": 120,
        "max_retries": 3,
        "supported_effects": ["audio_enhancement", "noise_reduction", "captions"],
        "rate_limit": {
            "requests_per_minute": 8,
            "requests_per_day": 80
        }
    },
    "kapwing": {
        "name": "Kapwing",
        "base_url": "https://api.kapwing.com/v1",
        "version": "1.0",
        "timeout": 150,
        "max_retries": 3,
        "supported_effects": ["subtitles", "text_effects", "transitions", "filters"],
        "rate_limit": {
            "requests_per_minute": 6,
            "requests_per_day": 60
        }
    }
}

# TikTok API配置
TIKTOK_CONFIG = {
    "base_url": "https://open.tiktokapis.com/v2",
    "version": "2.0",
    "timeout": 60,
    "max_retries": 3,
    "endpoints": {
        "upload_video": "/video/upload/",
        "publish_video": "/video/publish/",
        "get_video_info": "/video/info/",
        "get_analytics": "/analytics/video/"
    },
    "rate_limit": {
        "requests_per_minute": 10,
        "requests_per_day": 100
    }
}

# 用户可配置选项（可通过UI界面修改）
USER_CONFIG = {
    "preferred_video_model": SYSTEM_CONFIG["default_video_model"],
    "preferred_voice_tool": SYSTEM_CONFIG["default_voice_tool"],
    "preferred_music_tool": SYSTEM_CONFIG["default_music_tool"],
    "preferred_editing_tool": SYSTEM_CONFIG["default_editing_tool"],
    "preferred_resolution": SYSTEM_CONFIG["default_resolution"],
    "preferred_language": SYSTEM_CONFIG["default_language"],
    "auto_publish": False,
    "save_drafts": True,
    "notification_enabled": True,
    "theme": "light"
}

# 工作流配置
WORKFLOW_CONFIG = {
    "default_workflow": {
        "steps": [
            {
                "name": "content_generation",
                "type": "content",
                "timeout": 300,
                "retry_count": 3
            },
            {
                "name": "video_generation",
                "type": "video",
                "timeout": 600,
                "retry_count": 2
            },
            {
                "name": "voice_synthesis",
                "type": "voice",
                "timeout": 300,
                "retry_count": 3
            },
            {
                "name": "music_generation",
                "type": "music",
                "timeout": 300,
                "retry_count": 2
            },
            {
                "name": "video_editing",
                "type": "editing",
                "timeout": 600,
                "retry_count": 2
            }
        ],
        "parallel_processing": False,
        "max_total_time": 3600,
        "error_handling": {
            "retry_delay": 30,
            "fallback_enabled": True
        }
    },
    "fast_workflow": {
        "steps": [
            {
                "name": "content_generation",
                "type": "content",
                "timeout": 180,
                "retry_count": 2
            },
            {
                "name": "video_generation",
                "type": "video",
                "timeout": 300,
                "retry_count": 1
            },
            {
                "name": "voice_synthesis",
                "type": "voice",
                "timeout": 180,
                "retry_count": 2
            },
            {
                "name": "video_editing",
                "type": "editing",
                "timeout": 300,
                "retry_count": 1
            }
        ],
        "parallel_processing": True,
        "max_total_time": 1800,
        "error_handling": {
            "retry_delay": 15,
            "fallback_enabled": True
        }
    }
}

def update_user_config(new_config: Dict[str, Any]) -> None:
    """
    更新用户配置
    
    Args:
        new_config: 新的配置项
    """
    global USER_CONFIG
    USER_CONFIG.update(new_config)
    
def get_model_config(model_name: str) -> Dict[str, Any]:
    """
    获取指定模型的配置
    
    Args:
        model_name: 模型名称
        
    Returns:
        Dict[str, Any]: 模型配置
    """
    if model_name in MODEL_CONFIG:
        return MODEL_CONFIG[model_name]
    elif model_name in AUDIO_CONFIG:
        return AUDIO_CONFIG[model_name]
    elif model_name in EDITING_CONFIG:
        return EDITING_CONFIG[model_name]
    else:
        return {}
        
def get_available_models(model_type: str) -> List[str]:
    """
    获取指定类型的可用模型列表
    
    Args:
        model_type: 模型类型（video, voice, music, editing）
        
    Returns:
        List[str]: 可用模型列表
    """
    if model_type == "video":
        return [model for model in MODEL_CONFIG.keys() if API_KEYS.get(f"{model.upper()}_API_KEY")]
    elif model_type == "voice":
        return [tool for tool in AUDIO_CONFIG.keys() if tool in ["elevenlabs", "playht", "deepseek_tencent"] and API_KEYS.get(f"{tool.upper()}_API_KEY" if tool != "deepseek_tencent" else "TENCENT_API_KEY")]
    elif model_type == "music":
        return [tool for tool in AUDIO_CONFIG.keys() if tool in ["suno", "aiva", "soundraw"] and API_KEYS.get(f"{tool.upper()}_API_KEY")]
    elif model_type == "editing":
        return [tool for tool in EDITING_CONFIG.keys() if API_KEYS.get(f"{tool.upper()}_API_KEY")]
    else:
        return [] 