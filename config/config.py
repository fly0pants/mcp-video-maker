"""
系统配置管理
支持环境变量覆盖和动态更新
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class VideoModelConfig:
    """视频生成模型配置"""
    name: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    default_params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 1  # 优先级，数字越小优先级越高


@dataclass
class VoiceModelConfig:
    """语音合成模型配置"""
    name: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    default_params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 1


@dataclass
class MusicModelConfig:
    """音乐生成模型配置"""
    name: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    default_params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 1


@dataclass
class EditingToolConfig:
    """视频编辑工具配置"""
    name: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    default_params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 1


@dataclass
class ModelConfig:
    """所有模型配置"""
    video_models: List[VideoModelConfig] = field(default_factory=list)
    voice_models: List[VoiceModelConfig] = field(default_factory=list)
    music_models: List[MusicModelConfig] = field(default_factory=list)
    editing_tools: List[EditingToolConfig] = field(default_factory=list)
    
    def get_preferred_video_model(self) -> Optional[VideoModelConfig]:
        """获取首选视频模型"""
        enabled_models = [m for m in self.video_models if m.enabled]
        return sorted(enabled_models, key=lambda x: x.priority)[0] if enabled_models else None
    
    def get_preferred_voice_model(self) -> Optional[VoiceModelConfig]:
        """获取首选语音模型"""
        enabled_models = [m for m in self.voice_models if m.enabled]
        return sorted(enabled_models, key=lambda x: x.priority)[0] if enabled_models else None
    
    def get_preferred_music_model(self) -> Optional[MusicModelConfig]:
        """获取首选音乐模型"""
        enabled_models = [m for m in self.music_models if m.enabled]
        return sorted(enabled_models, key=lambda x: x.priority)[0] if enabled_models else None
    
    def get_preferred_editing_tool(self) -> Optional[EditingToolConfig]:
        """获取首选编辑工具"""
        enabled_tools = [t for t in self.editing_tools if t.enabled]
        return sorted(enabled_tools, key=lambda x: x.priority)[0] if enabled_tools else None


@dataclass
class AgentConfig:
    """代理配置"""
    heartbeat_interval: int = 10  # 心跳间隔（秒）
    command_timeout: int = 60  # 命令超时时间（秒）
    max_retries: int = 3  # 最大重试次数
    retry_delay: float = 2.0  # 重试延迟（秒）
    max_concurrent_tasks: int = 5  # 最大并发任务数


@dataclass
class MessageBusConfig:
    """消息总线配置"""
    max_history_size: int = 1000  # 最大历史消息数量
    heartbeat_timeout: int = 30  # 心跳超时时间（秒）
    cleanup_interval: int = 60  # 清理间隔（秒）
    default_message_ttl: int = 300  # 默认消息存活时间（秒）


@dataclass
class WorkflowConfig:
    """工作流配置"""
    default_video_duration: float = 60.0  # 默认视频时长（秒）
    max_video_duration: float = 180.0  # 最大视频时长（秒）
    default_aspect_ratio: str = "9:16"  # 默认宽高比（TikTok风格）
    output_quality: str = "high"  # 输出质量
    supported_styles: List[str] = field(default_factory=lambda: [
        "幽默", "励志", "教育", "娱乐", "科技", "生活", "美食", "旅行", "音乐", "创意"
    ])


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    ui_port: int = 8080
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])


@dataclass
class StorageConfig:
    """存储配置"""
    base_path: str = "./storage"
    temp_path: str = "./storage/temp"
    output_path: str = "./storage/output"
    scripts_path: str = "./storage/scripts"
    assets_path: str = "./storage/assets"
    max_storage_size_gb: float = 10.0  # 最大存储空间（GB）
    cleanup_after_days: int = 7  # 自动清理天数


@dataclass
class SystemConfig:
    """系统总配置"""
    models: ModelConfig = field(default_factory=ModelConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    message_bus: MessageBusConfig = field(default_factory=MessageBusConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    
    @classmethod
    def from_env(cls) -> "SystemConfig":
        """从环境变量加载配置"""
        config = cls()
        
        # 加载视频模型配置
        config.models.video_models = [
            VideoModelConfig(
                name="keling",
                api_key=os.getenv("KELING_API_KEY"),
                endpoint=os.getenv("KELING_ENDPOINT", "https://api.keling.ai"),
                default_params={"quality": "high", "style": "realistic"},
                priority=1
            ),
            VideoModelConfig(
                name="pika",
                api_key=os.getenv("PIKA_API_KEY"),
                endpoint=os.getenv("PIKA_ENDPOINT", "https://api.pika.art"),
                default_params={"style": "creative"},
                priority=2
            ),
            VideoModelConfig(
                name="runway",
                api_key=os.getenv("RUNWAY_API_KEY"),
                endpoint=os.getenv("RUNWAY_ENDPOINT", "https://api.runwayml.com"),
                default_params={"quality": "cinematic"},
                priority=3
            ),
            VideoModelConfig(
                name="wan",
                api_key=os.getenv("WAN_API_KEY"),
                endpoint=os.getenv("WAN_ENDPOINT", "https://api.wan.ai"),
                default_params={"style": "anime"},
                priority=4
            ),
        ]
        
        # 加载语音模型配置
        config.models.voice_models = [
            VoiceModelConfig(
                name="elevenlabs",
                api_key=os.getenv("ELEVENLABS_API_KEY"),
                endpoint=os.getenv("ELEVENLABS_ENDPOINT", "https://api.elevenlabs.io"),
                default_params={"voice_id": "default", "stability": 0.75},
                priority=1
            ),
            VoiceModelConfig(
                name="playht",
                api_key=os.getenv("PLAYHT_API_KEY"),
                endpoint=os.getenv("PLAYHT_ENDPOINT", "https://api.play.ht"),
                default_params={"quality": "high"},
                priority=2
            ),
            VoiceModelConfig(
                name="tencent",
                api_key=os.getenv("TENCENT_API_KEY"),
                endpoint=os.getenv("TENCENT_ENDPOINT", "https://tts.cloud.tencent.com"),
                default_params={"language": "zh-CN"},
                priority=3
            ),
        ]
        
        # 加载音乐模型配置
        config.models.music_models = [
            MusicModelConfig(
                name="suno",
                api_key=os.getenv("SUNO_API_KEY"),
                endpoint=os.getenv("SUNO_ENDPOINT", "https://api.suno.ai"),
                default_params={"duration": 60},
                priority=1
            ),
            MusicModelConfig(
                name="aiva",
                api_key=os.getenv("AIVA_API_KEY"),
                endpoint=os.getenv("AIVA_ENDPOINT", "https://api.aiva.ai"),
                default_params={"mood": "upbeat"},
                priority=2
            ),
            MusicModelConfig(
                name="soundraw",
                api_key=os.getenv("SOUNDRAW_API_KEY"),
                endpoint=os.getenv("SOUNDRAW_ENDPOINT", "https://api.soundraw.io"),
                default_params={"copyright_free": True},
                priority=3
            ),
        ]
        
        # 加载编辑工具配置
        config.models.editing_tools = [
            EditingToolConfig(
                name="runway_edit",
                api_key=os.getenv("RUNWAY_API_KEY"),
                endpoint=os.getenv("RUNWAY_ENDPOINT", "https://api.runwayml.com"),
                default_params={"effects": ["color_grade", "stabilize"]},
                priority=1
            ),
            EditingToolConfig(
                name="descript",
                api_key=os.getenv("DESCRIPT_API_KEY"),
                endpoint=os.getenv("DESCRIPT_ENDPOINT", "https://api.descript.com"),
                default_params={"auto_caption": True},
                priority=2
            ),
            EditingToolConfig(
                name="kapwing",
                api_key=os.getenv("KAPWING_API_KEY"),
                endpoint=os.getenv("KAPWING_ENDPOINT", "https://api.kapwing.com"),
                default_params={"text_effects": True},
                priority=3
            ),
        ]
        
        # 加载服务器配置
        config.server.host = os.getenv("SERVER_HOST", "0.0.0.0")
        config.server.port = int(os.getenv("SERVER_PORT", "8000"))
        config.server.ui_port = int(os.getenv("UI_PORT", "8080"))
        config.server.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # 加载存储配置
        config.storage.base_path = os.getenv("STORAGE_PATH", "./storage")
        config.storage.temp_path = os.path.join(config.storage.base_path, "temp")
        config.storage.output_path = os.path.join(config.storage.base_path, "output")
        config.storage.scripts_path = os.path.join(config.storage.base_path, "scripts")
        config.storage.assets_path = os.path.join(config.storage.base_path, "assets")
        
        return config
    
    def update(self, **kwargs):
        """动态更新配置"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_available_video_models(self) -> List[str]:
        """获取可用的视频模型列表"""
        return [m.name for m in self.models.video_models if m.enabled and m.api_key]
    
    def get_available_voice_models(self) -> List[str]:
        """获取可用的语音模型列表"""
        return [m.name for m in self.models.voice_models if m.enabled and m.api_key]
    
    def get_available_music_models(self) -> List[str]:
        """获取可用的音乐模型列表"""
        return [m.name for m in self.models.music_models if m.enabled and m.api_key]


# 全局配置实例
config = SystemConfig.from_env()
