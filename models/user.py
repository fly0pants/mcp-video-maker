from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from config.config import VideoGenerationModel, VoiceSynthesisTool, MusicGenerationTool, EditingTool
from models.video import VideoStyle, ScriptType


class UserProfile(BaseModel):
    """用户个人资料模型"""
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="电子邮件")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="偏好设置")
    api_usage: Dict[str, int] = Field(default_factory=dict, description="API使用情况")
    projects: List[str] = Field(default_factory=list, description="项目ID列表")
    avatar: Optional[str] = Field(None, description="头像URL")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class VideoCreationRequest(BaseModel):
    """视频创建请求模型"""
    theme: str = Field(..., description="视频主题")
    style: VideoStyle = Field(..., description="视频风格")
    script_type: ScriptType = Field(..., description="脚本类型")
    target_audience: List[str] = Field(..., description="目标受众")
    duration: float = Field(..., description="目标时长（秒）")
    language: str = Field("zh", description="语言")
    
    # 模型和工具选择
    video_model: VideoGenerationModel = Field(VideoGenerationModel.WAN, description="视频生成模型")
    voice_tool: VoiceSynthesisTool = Field(VoiceSynthesisTool.DEEPSEEK_TENCENT, description="语音合成工具")
    music_tool: MusicGenerationTool = Field(MusicGenerationTool.SUNO, description="音乐生成工具")
    editing_tool: EditingTool = Field(EditingTool.RUNWAY, description="编辑工具")
    
    # 附加选项
    references: List[str] = Field(default_factory=list, description="参考链接")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    special_requirements: Optional[str] = Field(None, description="特殊要求")
    resolution: str = Field("1080x1920", description="分辨率")
    include_captions: bool = Field(True, description="是否包含字幕")
    music_style: Optional[str] = Field(None, description="音乐风格")
    voice_character: Optional[str] = Field(None, description="语音角色")
    
    class Config:
        json_schema_extra = {
            "example": {
                "theme": "上海城市探索",
                "style": "vlog",
                "script_type": "narrative",
                "target_audience": ["年轻旅行者", "城市文化爱好者"],
                "duration": 45.0,
                "language": "zh",
                "video_model": "pika",
                "voice_tool": "elevenlabs",
                "music_tool": "suno",
                "editing_tool": "runway",
                "references": ["https://example.com/shanghai_travel"],
                "keywords": ["上海", "旅行", "城市探索", "美食"],
                "special_requirements": "展示上海的现代建筑与传统文化对比",
                "resolution": "1080x1920",
                "include_captions": True,
                "music_style": "轻快现代",
                "voice_character": "女性，热情"
            }
        }


class ProjectMetadata(BaseModel):
    """项目元数据模型"""
    id: str = Field(..., description="项目ID")
    name: str = Field(..., description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    owner_id: str = Field(..., description="所有者ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    status: str = Field("draft", description="状态")
    video_ids: List[str] = Field(default_factory=list, description="视频ID列表")
    collaborators: List[str] = Field(default_factory=list, description="协作者ID列表")
    tags: List[str] = Field(default_factory=list, description="标签")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据") 