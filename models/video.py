from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator


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


class ShotType(str, Enum):
    """镜头类型枚举"""
    WIDE = "wide"  # 广角镜头
    MEDIUM = "medium"  # 中景镜头
    CLOSE_UP = "close_up"  # 特写镜头
    EXTREME_CLOSE_UP = "extreme_close_up"  # 极端特写
    AERIAL = "aerial"  # 航拍镜头
    POV = "pov"  # 主观视角
    TRACKING = "tracking"  # 跟踪镜头
    STATIC = "static"  # 静态镜头
    HANDHELD = "handheld"  # 手持镜头
    DOLLY = "dolly"  # 推轨镜头


class TransitionType(str, Enum):
    """转场类型枚举"""
    CUT = "cut"  # 直切
    FADE = "fade"  # 淡入淡出
    DISSOLVE = "dissolve"  # 溶解
    WIPE = "wipe"  # 擦除
    SLIDE = "slide"  # 滑动
    ZOOM = "zoom"  # 缩放
    PUSH = "push"  # 推移
    FLASH = "flash"  # 闪白
    MORPH = "morph"  # 变形


class AudioType(str, Enum):
    """音频类型枚举"""
    VOICE = "voice"  # 人声
    MUSIC = "music"  # 音乐
    SFX = "sfx"  # 音效
    AMBIENT = "ambient"  # 环境音
    FOLEY = "foley"  # 拟音


class EffectType(str, Enum):
    """效果类型枚举"""
    REVERB = "reverb"  # 混响
    ECHO = "echo"  # 回声
    PITCH_SHIFT = "pitch_shift"  # 音调变化
    COMPRESSION = "compression"  # 压缩
    EQUALIZATION = "equalization"  # 均衡器
    DISTORTION = "distortion"  # 失真
    DELAY = "delay"  # 延迟
    FILTER = "filter"  # 滤波器
    FADE = "fade"  # 淡入淡出


class EditType(str, Enum):
    """编辑类型枚举"""
    VIDEO = "video"  # 视频编辑
    AUDIO = "audio"  # 音频编辑
    TEXT = "text"  # 文字编辑
    SPECIAL = "special"  # 特效编辑
    COLOR = "color"  # 色彩编辑
    TRANSITION = "transition"  # 转场编辑


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

    @field_validator('total_duration')
    def validate_duration(cls, v, info):
        """验证总时长是否与片段时长之和匹配"""
        values = info.data
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


class Shot(BaseModel):
    """镜头模型"""
    id: str = Field(..., description="镜头ID")
    script_section_id: str = Field(..., description="对应的脚本片段ID")
    type: ShotType = Field(..., description="镜头类型")
    description: str = Field(..., description="镜头描述")
    duration: float = Field(..., description="时长（秒）")
    order: int = Field(..., description="在序列中的顺序")
    asset_id: Optional[str] = Field(None, description="关联的视频资产ID")
    camera_movement: Optional[str] = Field(None, description="相机运动描述")
    composition: Optional[str] = Field(None, description="构图描述")
    lighting: Optional[str] = Field(None, description="灯光描述")
    focal_point: Optional[str] = Field(None, description="焦点描述")
    color_grading: Optional[str] = Field(None, description="色彩校正描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class Transition(BaseModel):
    """转场模型"""
    id: str = Field(..., description="转场ID")
    type: TransitionType = Field(..., description="转场类型")
    duration: float = Field(..., description="时长（秒）")
    from_shot_id: str = Field(..., description="起始镜头ID")
    to_shot_id: str = Field(..., description="目标镜头ID")
    description: Optional[str] = Field(None, description="转场描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="转场参数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AudioEffect(BaseModel):
    """音频效果模型"""
    id: str = Field(..., description="效果ID")
    type: EffectType = Field(..., description="效果类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="效果参数")
    description: Optional[str] = Field(None, description="效果描述")
    start_time: float = Field(..., description="开始时间（秒）")
    end_time: Optional[float] = Field(None, description="结束时间（秒）")
    intensity: float = Field(1.0, description="效果强度")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AudioTrack(BaseModel):
    """音频轨道模型"""
    id: str = Field(..., description="轨道ID")
    type: AudioType = Field(..., description="音频类型")
    asset_id: str = Field(..., description="关联的音频资产ID")
    start_time: float = Field(0.0, description="开始时间（秒）")
    end_time: Optional[float] = Field(None, description="结束时间（秒）")
    volume: float = Field(1.0, description="音量（0.0-1.0）")
    effects: List[AudioEffect] = Field(default_factory=list, description="应用的音频效果")
    channel: int = Field(0, description="音频通道")
    fade_in: Optional[float] = Field(None, description="淡入时间（秒）")
    fade_out: Optional[float] = Field(None, description="淡出时间（秒）")
    loop: bool = Field(False, description="是否循环")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class VideoEdit(BaseModel):
    """视频编辑模型"""
    id: str = Field(..., description="编辑ID")
    script_id: str = Field(..., description="脚本ID")
    title: str = Field(..., description="编辑标题")
    description: Optional[str] = Field(None, description="编辑描述")
    shots: List[Shot] = Field(..., description="镜头列表")
    transitions: List[Transition] = Field(..., description="转场列表")
    audio_tracks: List[AudioTrack] = Field(..., description="音频轨道列表")
    duration: float = Field(..., description="总时长（秒）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    version: int = Field(1, description="版本号")
    creator_id: str = Field(..., description="创建者ID")
    status: str = Field("draft", description="状态（draft/in_progress/completed）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class VideoCreationRequest(BaseModel):
    """视频创建请求模型"""
    id: str = Field(..., description="请求ID")
    title: str = Field(..., description="视频标题")
    theme: str = Field(..., description="主题")
    type: ScriptType = Field(..., description="视频类型")
    style: VideoStyle = Field(..., description="视频风格")
    target_audience: List[str] = Field(..., description="目标受众")
    target_duration: float = Field(..., description="目标时长（秒）")
    description: str = Field(..., description="详细描述")
    references: List[str] = Field(default_factory=list, description="参考链接")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="特殊要求")
    creator_id: str = Field(..., description="创建者ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    priority: int = Field(1, description="优先级（1-5）")
    status: str = Field("pending", description="状态（pending/in_progress/completed/failed）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class DistributionMetadata(BaseModel):
    """分发元数据模型"""
    cover_image: Optional[str] = Field(None, description="封面图片")
    category: Optional[str] = Field(None, description="分类")
    visibility: str = Field("public", description="可见性（public/private/unlisted）")
    allow_comments: bool = Field(True, description="是否允许评论")
    allow_likes: bool = Field(True, description="是否允许点赞")
    age_restriction: Optional[str] = Field(None, description="年龄限制")
    monetization: bool = Field(False, description="是否开启变现")
    language: Optional[str] = Field(None, description="语言")
    location: Optional[str] = Field(None, description="位置信息")
    custom_thumbnail: Optional[bool] = Field(False, description="是否使用自定义缩略图")
    additional_info: Dict[str, Any] = Field(default_factory=dict, description="其他平台特定元数据")


class PublishSchedule(BaseModel):
    """发布计划模型"""
    publish_time: Optional[str] = Field(None, description="发布时间（ISO 8601格式）")
    timezone: str = Field("UTC", description="时区")
    auto_publish: bool = Field(True, description="是否自动发布")
    repeat: Optional[str] = Field(None, description="重复发布计划（如每周）")
    end_date: Optional[str] = Field(None, description="重复发布结束日期")


class Platform(BaseModel):
    """分发平台模型"""
    name: str = Field(..., description="平台名称")
    title: str = Field(..., description="视频标题")
    description: str = Field(..., description="视频描述")
    tags: List[str] = Field(..., description="标签")
    schedule: PublishSchedule = Field(..., description="发布计划")
    metadata: DistributionMetadata = Field(..., description="平台特定元数据")
    status: str = Field("pending", description="状态（pending/scheduled/published/failed）")
    publish_url: Optional[HttpUrl] = Field(None, description="发布URL")
    analytics: Dict[str, Any] = Field(default_factory=dict, description="分析数据")


class Distribution(BaseModel):
    """分发模型"""
    id: str = Field(..., description="分发ID")
    final_video_id: Optional[str] = Field(None, description="关联的最终视频ID")
    platforms: List[Platform] = Field(..., description="目标平台列表")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    creator_id: Optional[str] = Field(None, description="创建者ID")
    status: str = Field("draft", description="整体状态（draft/in_progress/completed/failed）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class StoryboardImageSource(str, Enum):
    """分镜图片来源枚举"""
    REPLICATE = "replicate"  # Replicate平台
    DOUIMG = "douimg"  # 豆包AI平台
    OTHER_API = "other_api"  # 其他API服务
    MANUAL = "manual"  # 手动上传
    PLACEHOLDER = "placeholder"  # 占位图片


class StoryboardStyle(str, Enum):
    """分镜样式枚举"""
    REALISTIC = "realistic"  # 写实风格
    SKETCH = "sketch"  # 素描风格
    CARTOON = "cartoon"  # 卡通风格
    ANIME = "anime"  # 动漫风格
    PAINTERLY = "painterly"  # 绘画风格
    CONCEPT_ART = "concept_art"  # 概念艺术风格
    SIMPLE = "simple"  # 简约风格
    STORYBOARD = "storyboard"  # 标准分镜风格


class StoryboardImage(BaseModel):
    """分镜图片模型"""
    id: str = Field(..., description="分镜图片ID")
    script_section_id: str = Field(..., description="关联的脚本片段ID")
    image_path: str = Field(..., description="图片文件路径")
    preview_url: Optional[str] = Field(None, description="预览URL")
    description: str = Field(..., description="图片描述")
    prompt: str = Field(..., description="生成提示词")
    negative_prompt: Optional[str] = Field(None, description="负向提示词")
    source: StoryboardImageSource = Field(..., description="图片来源")
    source_model: Optional[str] = Field(None, description="生成模型")
    source_parameters: Dict[str, Any] = Field(default_factory=dict, description="生成参数")
    width: int = Field(..., description="图片宽度")
    height: int = Field(..., description="图片高度")
    order: int = Field(..., description="在分镜中的顺序")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class StoryboardFrameType(str, Enum):
    """分镜框架类型枚举"""
    KEYFRAME = "keyframe"  # 关键帧
    ESTABLISHING = "establishing"  # 场景建立
    CLOSEUP = "closeup"  # 特写
    ACTION = "action"  # 动作
    TRANSITION = "transition"  # 转场
    DIALOGUE = "dialogue"  # 对话
    NARRATIVE = "narrative"  # 叙事


class StoryboardTransition(BaseModel):
    """分镜转场模型"""
    id: str = Field(..., description="转场ID")
    description: str = Field(..., description="转场描述")
    from_frame_id: str = Field(..., description="起始帧ID")
    to_frame_id: str = Field(..., description="结束帧ID")
    transition_type: TransitionType = Field(..., description="转场类型")
    duration: float = Field(..., description="转场持续时间（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class StoryboardFrame(BaseModel):
    """分镜框架模型"""
    id: str = Field(..., description="框架ID")
    script_section_id: str = Field(..., description="关联的脚本片段ID")
    frame_type: StoryboardFrameType = Field(..., description="框架类型")
    shot_type: ShotType = Field(..., description="镜头类型")
    description: str = Field(..., description="框架描述")
    visual_description: str = Field(..., description="视觉描述")
    dialogue: Optional[str] = Field(None, description="对白内容")
    duration: float = Field(..., description="估计持续时间（秒）")
    order: int = Field(..., description="在分镜中的顺序")
    image_id: Optional[str] = Field(None, description="关联的分镜图片ID")
    camera_movement: Optional[str] = Field(None, description="相机运动描述")
    composition: Optional[str] = Field(None, description="构图描述")
    comments: Optional[str] = Field(None, description="备注")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class Storyboard(BaseModel):
    """分镜模型"""
    id: str = Field(..., description="分镜ID")
    script_id: str = Field(..., description="关联的脚本ID")
    title: str = Field(..., description="分镜标题")
    style: StoryboardStyle = Field(..., description="分镜风格")
    frames: List[StoryboardFrame] = Field(..., description="分镜框架列表")
    transitions: List[StoryboardTransition] = Field(default_factory=list, description="分镜转场列表")
    images: List[StoryboardImage] = Field(default_factory=list, description="分镜图片列表")
    total_duration: float = Field(..., description="总时长（秒）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    creator_id: str = Field(..., description="创建者ID")
    version: int = Field(1, description="版本号")
    status: str = Field("draft", description="状态（draft/in_progress/completed）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    @field_validator('total_duration')
    def validate_duration(cls, v, info):
        """验证总时长是否与框架时长之和匹配"""
        values = info.data
        if 'frames' in values:
            calculated_duration = sum(frame.duration for frame in values['frames'])
            if abs(calculated_duration - v) > 0.5:  # 允许0.5秒的误差
                raise ValueError(f"总时长 ({v}s) 与框架时长之和 ({calculated_duration}s) 不匹配")
        return v