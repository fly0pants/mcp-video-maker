import asyncio
import uuid
import json
import os
import random
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.message import Message, MessageType, AgentType
from models.video import FinalVideo
from agents.base_agent import BaseAgent
from utils.file_manager import file_manager
from utils.logger import system_logger
from config.config import SYSTEM_CONFIG, EDITING_CONFIG, API_KEYS


class EditingAPI:
    """视频编辑API接口封装"""
    
    def __init__(self, tool_name: str, api_key: str):
        self.tool_name = tool_name
        self.api_key = api_key
        self.config = EDITING_CONFIG.get(tool_name, {})
        self.api_url = self.config.get("api_url", "")
        self.features = self.config.get("features", [])
        
    async def edit_video(self, 
                       video_assets: List[Dict[str, Any]], 
                       audio_assets: List[Dict[str, Any]],
                       include_captions: bool = True,
                       resolution: str = "1080x1920",
                       **kwargs) -> Dict[str, Any]:
        """
        编辑视频（模拟实现）
        
        Args:
            video_assets: 视频资产列表
            audio_assets: 音频资产列表
            include_captions: 是否包含字幕
            resolution: 分辨率
            
        Returns:
            编辑结果
        """
        # 实际项目中，这里应该调用真实的视频编辑API
        # 目前使用模拟实现
        
        # 模拟API调用延迟
        await asyncio.sleep(random.uniform(2.0, 5.0))
        
        # 模拟生成结果
        video_id = f"final_{uuid.uuid4().hex[:8]}"
        
        # 模拟文件路径（实际项目中应该是API返回的URL或临时文件路径）
        file_path = f"./temp/videos/{video_id}.mp4"
        
        # 计算总时长（实际项目中应该是真实的视频时长）
        total_duration = sum(asset.get("duration", 0) for asset in video_assets)
        
        return {
            "id": video_id,
            "file_path": file_path,
            "duration": total_duration,
            "resolution": resolution,
            "format": "mp4",
            "include_captions": include_captions,
            "video_assets": [asset.get("id") for asset in video_assets],
            "audio_assets": [asset.get("id") for asset in audio_assets],
            "tool": self.tool_name,
            "created_at": datetime.now().isoformat()
        }


class PostProdAgent(BaseAgent):
    """
    后期制作代理 - 系统的"编辑"，将视频、音频和字幕整合为成品
    
    职责:
    - 使用所选视频生成模型的编辑功能调整细节
    - 通过专业编辑API进行剪辑、色彩校正和视觉效果处理
    - 使用所选模型的文本生成能力生成动态字幕
    - 确保最终视频符合TikTok的技术规范
    """
    
    def __init__(self):
        super().__init__(AgentType.POSTPROD, "PostProdAgent")
        self.editing_apis: Dict[str, EditingAPI] = {}
        
    async def initialize(self):
        """初始化后期制作代理"""
        await super().initialize()
        
        # 初始化各个编辑工具的API
        for tool_name in EDITING_CONFIG.keys():
            api_key = API_KEYS.get(f"{tool_name}_edit", "")  # 注意这里使用了特殊的键名
            if api_key:
                self.editing_apis[tool_name] = EditingAPI(tool_name, api_key)
                self.logger.info(f"Initialized {tool_name} editing API")
            else:
                self.logger.warning(f"API key for {tool_name} not found, this editing tool will not be available")
                
        self.logger.info("Post-production Agent initialized and ready to edit videos")
        
    async def handle_command(self, message: Message) -> Optional[Message]:
        """处理命令消息"""
        action = message.content.get("action")
        
        if action == "post_production":
            # 后期制作
            parameters = message.content.get("parameters", {})
            session_id = message.content.get("session_id")
            
            if not parameters:
                return self.create_error_response(message, "Missing post-production parameters")
                
            try:
                final_video = await self._post_production(parameters, session_id)
                
                return self.create_success_response(message, {
                    "final_video": final_video
                })
            except Exception as e:
                self.logger.error(f"Error in post-production: {str(e)}")
                return self.create_error_response(message, f"Error in post-production: {str(e)}")
                
        elif action == "generate_captions":
            # 生成字幕
            video_path = message.content.get("video_path")
            audio_path = message.content.get("audio_path")
            language = message.content.get("language", "zh")
            
            if not video_path or not audio_path:
                return self.create_error_response(message, "Missing video_path or audio_path for caption generation")
                
            try:
                captions = await self._generate_captions(video_path, audio_path, language)
                
                return self.create_success_response(message, {
                    "captions": captions
                })
            except Exception as e:
                self.logger.error(f"Error generating captions: {str(e)}")
                return self.create_error_response(message, f"Error generating captions: {str(e)}")
                
        elif action == "create_thumbnail":
            # 创建缩略图
            video_path = message.content.get("video_path")
            
            if not video_path:
                return self.create_error_response(message, "Missing video_path for thumbnail creation")
                
            try:
                thumbnail_path = await self._create_thumbnail(video_path)
                
                return self.create_success_response(message, {
                    "thumbnail_path": thumbnail_path
                })
            except Exception as e:
                self.logger.error(f"Error creating thumbnail: {str(e)}")
                return self.create_error_response(message, f"Error creating thumbnail: {str(e)}")
                
        else:
            return self.create_error_response(message, f"Unknown action: {action}")
    
    async def _post_production(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        执行后期制作
        
        Args:
            parameters: 制作参数
            session_id: 会话ID
            
        Returns:
            最终视频
        """
        script_id = parameters.get("script_id")
        script_title = parameters.get("script_title", "未命名视频")
        video_assets = parameters.get("video_assets", [])
        audio_assets = parameters.get("audio_assets", [])
        editing_tool = parameters.get("editing_tool", SYSTEM_CONFIG["default_editing_tool"])
        include_captions = parameters.get("include_captions", True)
        resolution = parameters.get("resolution", SYSTEM_CONFIG["default_resolution"])
        
        if not video_assets:
            raise ValueError("No video assets provided")
            
        if not audio_assets:
            raise ValueError("No audio assets provided")
            
        # 检查选择的编辑工具是否可用
        if editing_tool not in self.editing_apis:
            self.logger.warning(f"Selected editing tool {editing_tool} not available, falling back to default")
            editing_tool = SYSTEM_CONFIG["default_editing_tool"]
            
        # 获取API客户端
        api = self.editing_apis.get(editing_tool)
        if not api:
            raise ValueError(f"No API available for editing tool {editing_tool}")
            
        # 创建会话目录
        session_temp_dir, session_output_dir = file_manager.get_session_dir(session_id)
        
        # 1. 生成字幕（如果需要）
        captions = None
        if include_captions:
            # 找到第一个语音资产用于生成字幕
            voice_assets = [asset for asset in audio_assets if asset.get("type") == "voice"]
            if voice_assets:
                first_voice = voice_assets[0]
                captions = await self._generate_captions(
                    video_path=video_assets[0].get("file_path"),
                    audio_path=first_voice.get("file_path"),
                    language="zh"  # 假设使用中文
                )
                
        # 2. 调用编辑API整合视频和音频
        self.logger.info(f"Editing video with {editing_tool}, {len(video_assets)} video assets, {len(audio_assets)} audio assets")
        
        result = await api.edit_video(
            video_assets=video_assets,
            audio_assets=audio_assets,
            include_captions=include_captions,
            resolution=resolution
        )
        
        # 3. 创建缩略图
        thumbnail_path = await self._create_thumbnail(result["file_path"])
        
        # 4. 创建最终视频文件（实际项目中应该是真实的视频文件）
        final_video_filename = f"{script_id}_final.mp4"
        final_video_path = os.path.join(session_output_dir, "videos", final_video_filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(final_video_path), exist_ok=True)
        
        # 模拟最终视频文件（实际项目中应该是真实视频文件）
        with open(final_video_path, "w") as f:
            f.write(f"Simulated final video for {script_title}")
            
        # 5. 创建最终视频对象
        final_video = {
            "id": f"final_{uuid.uuid4().hex[:8]}",
            "script_id": script_id,
            "title": script_title,
            "description": f"{script_title} - 由AI生成的TikTok风格短视频",
            "file_path": final_video_path,
            "format": "mp4",
            "duration": result["duration"],
            "resolution": resolution,
            "created_at": datetime.now().isoformat(),
            "video_assets": [asset.get("id") for asset in video_assets],
            "audio_assets": [asset.get("id") for asset in audio_assets],
            "thumbnail": thumbnail_path,
            "tags": self._extract_tags(video_assets, audio_assets),
            "quality_score": await self._evaluate_video_quality(final_video_path),
            "metadata": {
                "session_id": session_id,
                "editing_tool": editing_tool,
                "include_captions": include_captions,
                "api_response": result
            }
        }
        
        self.logger.info(f"Created final video: {final_video['id']}, duration: {final_video['duration']}s")
        return final_video
    
    async def _generate_captions(self, 
                               video_path: str, 
                               audio_path: str, 
                               language: str = "zh") -> List[Dict[str, Any]]:
        """
        生成字幕
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            language: 语言
            
        Returns:
            字幕列表
        """
        # 实际项目中，这里应该使用语音识别API生成字幕
        # 目前使用模拟数据
        
        # 模拟处理延迟
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # 模拟字幕数据
        captions = []
        
        # 假设视频有30秒，每5秒一个字幕
        for i in range(6):
            start_time = i * 5.0
            end_time = start_time + 4.5  # 留0.5秒空隙
            
            caption = {
                "id": f"caption_{i}",
                "start_time": start_time,
                "end_time": end_time,
                "text": f"这是第{i+1}段字幕文本",
                "position": "bottom"
            }
            
            captions.append(caption)
            
        self.logger.info(f"Generated {len(captions)} caption segments for {video_path}")
        return captions
    
    async def _create_thumbnail(self, video_path: str) -> str:
        """
        从视频中创建缩略图
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            缩略图文件路径
        """
        # 实际项目中，这里应该从视频中提取关键帧作为缩略图
        # 目前使用模拟实现
        
        # 模拟处理延迟
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # 创建缩略图文件名
        thumbnail_id = f"thumb_{uuid.uuid4().hex[:8]}"
        thumbnail_path = os.path.join(os.path.dirname(video_path), f"{thumbnail_id}.jpg")
        
        # 模拟缩略图文件（实际项目中应该是真实图片文件）
        with open(thumbnail_path, "w") as f:
            f.write(f"Simulated thumbnail for {video_path}")
            
        self.logger.info(f"Created thumbnail at {thumbnail_path}")
        return thumbnail_path
    
    async def _evaluate_video_quality(self, video_path: str) -> float:
        """
        评估视频质量
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            质量评分（0-1）
        """
        # 实际项目中，这里应该使用计算机视觉模型评估视频质量
        # 目前使用随机分数模拟
        
        # 模拟评估延迟
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # 生成随机质量分数（偏向高分）
        quality_score = random.uniform(0.75, 0.95)
        
        self.logger.info(f"Evaluated final video quality for {video_path}: {quality_score:.2f}")
        return quality_score
    
    def _extract_tags(self, video_assets: List[Dict[str, Any]], audio_assets: List[Dict[str, Any]]) -> List[str]:
        """
        从视频和音频资产中提取标签
        
        Args:
            video_assets: 视频资产列表
            audio_assets: 音频资产列表
            
        Returns:
            标签列表
        """
        tags = set()
        
        # 从视频资产中提取标签
        for asset in video_assets:
            asset_tags = asset.get("generation_parameters", {}).get("tags", [])
            if isinstance(asset_tags, list):
                tags.update(asset_tags)
                
        # 从音频资产中提取标签
        for asset in audio_assets:
            if asset.get("type") == "music":
                mood = asset.get("generation_parameters", {}).get("mood")
                style = asset.get("generation_parameters", {}).get("style")
                
                if mood:
                    tags.add(mood)
                if style:
                    tags.add(style)
                    
        return list(tags) 