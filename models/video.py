from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, validator


class ScriptType(str, Enum):
    """脚本类型枚举"""
    NARRATIVE = "narrative"  # 叙事型
    TUTORIAL = "tutorial"  # 教程型
    COMEDY = "comedy"  # 喜剧型
    REVIEW = "review"  # 评测型
    TRENDING = "trending"  # 趋势型
    EMOTIONAL = "emotional"  # 情感型


class VideoStyle(str, Enum):
    """视频风格枚举"""
    REALISTIC = "realistic"  # 写实风格
    CARTOON = "cartoon"  # 卡通风格
    ANIME = "anime"  # 动漫风格
    CINEMATIC = "cinematic"  # 电影风格
    VLOG = "vlog"  # 视频博客风格
    VINTAGE = "vintage"  # 复古风格
    FUTURISTIC = "futuristic"  # 未来风格


class ScriptSection(BaseModel):
    """脚本片段模型"""
    id: str = Field(..., description="片段ID")
    content: str = Field(..., description="脚本内容")
    duration: float = Field(..., description="估计持续时间（秒）")
    visual_description: str = Field(..., description="视觉描述")
    audio_description: Optional[str] = Field(None, description="音频描述")
    tags: List[str] = Field(default_factory=list, description="标签")
    order: int = Field(..., description="在脚本中的顺序")


class Script(BaseModel):
    """完整脚本模型"""
    id: str = Field(..., description="脚本ID")
    title: str = Field(..., description="脚本标题")
    theme: str = Field(..., description="主题")
    type: ScriptType = Field(..., description="脚本类型")
    target_audience: List[str] = Field(..., description="目标受众")
    sections: List[ScriptSection] = Field(..., description="脚本片段列表")
    total_duration: float = Field(..., description="总时长（秒）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    creator_id: str = Field(..., description="创建者ID")
    version: int = Field(1, description="版本号")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    @validator('total_duration')
    def validate_duration(cls, v, values):
        """验证总时长是否与片段时长之和匹配"""
        if 'sections' in values:
            calculated_duration = sum(section.duration for section in values['sections'])
            if abs(calculated_duration - v) > 0.5:  # 允许0.5秒的误差
                raise ValueError(f"总时长 ({v}s) 与片段时长之和 ({calculated_duration}s) 不匹配")
        return v


class VideoAsset(BaseModel):
    """视频资产模型"""
    id: str = Field(..., description="资产ID")
    script_section_id: str = Field(..., description="对应的脚本片段ID")
    file_path: str = Field(..., description="文件路径")
    url: Optional[HttpUrl] = Field(None, description="URL（如果是远程资产）")
    format: str = Field(..., description="文件格式")
    duration: float = Field(..., description="时长（秒）")
    resolution: str = Field(..., description="分辨率")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    generation_model: str = Field(..., description="生成使用的模型")
    generation_parameters: Dict[str, Any] = Field(default_factory=dict, description="生成参数")
    quality_score: Optional[float] = Field(None, description="质量评分")
    preview_image: Optional[str] = Field(None, description="预览图路径")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AudioAsset(BaseModel):
    """音频资产模型"""
    id: str = Field(..., description="资产ID")
    script_section_id: Optional[str] = Field(None, description="对应的脚本片段ID")
    file_path: str = Field(..., description="文件路径")
    url: Optional[HttpUrl] = Field(None, description="URL（如果是远程资产）")
    format: str = Field(..., description="文件格式")
    duration: float = Field(..., description="时长（秒）")
    type: str = Field(..., description="类型（voice/music/sfx）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    generation_tool: str = Field(..., description="生成使用的工具")
    generation_parameters: Dict[str, Any] = Field(default_factory=dict, description="生成参数")
    quality_score: Optional[float] = Field(None, description="质量评分")
    waveform: Optional[List[float]] = Field(None, description="波形数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class FinalVideo(BaseModel):
    """最终视频模型"""
    id: str = Field(..., description="视频ID")
    script_id: str = Field(..., description="脚本ID")
    title: str = Field(..., description="视频标题")
    description: str = Field(..., description="视频描述")
    file_path: str = Field(..., description="文件路径")
    url: Optional[HttpUrl] = Field(None, description="URL（如果已上传）")
    format: str = Field(..., description="文件格式")
    duration: float = Field(..., description="时长（秒）")
    resolution: str = Field(..., description="分辨率")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    video_assets: List[str] = Field(..., description="使用的视频资产ID列表")
    audio_assets: List[str] = Field(..., description="使用的音频资产ID列表")
    thumbnail: Optional[str] = Field(None, description="缩略图路径")
    tags: List[str] = Field(default_factory=list, description="标签")
    quality_score: Optional[float] = Field(None, description="质量评分")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据") 