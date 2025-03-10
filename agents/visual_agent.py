import asyncio
import uuid
import json
import os
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from models.message import Message, MessageType, AgentType
from models.video import VideoAsset
from agents.base_agent import BaseAgent
from utils.file_manager import file_manager
from utils.logger import system_logger
from config.config import SYSTEM_CONFIG, MODEL_CONFIG, API_KEYS, VideoGenerationModel
from apis.video_generation_api import VideoGenerationAPI
from utils.prompt_manager import get_prompt_manager


class VideoGenerationAPI:
    """视频生成API接口封装"""
    
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = MODEL_CONFIG.get(model_name, {}).get("base_url", "")
        self.model_version = MODEL_CONFIG.get(model_name, {}).get("version", "1.0")
        self.request_timeout = MODEL_CONFIG.get(model_name, {}).get("timeout", 60)
        self.max_retries = MODEL_CONFIG.get(model_name, {}).get("max_retries", 3)
        
    async def generate_video(self, 
                          prompt: str, 
                          visual_description: str, 
                          duration: float,
                          resolution: str,
                          style: str,
                          **kwargs) -> Dict[str, Any]:
        """
        生成视频
        
        Args:
            prompt: 提示词
            visual_description: 视觉描述
            duration: 时长（秒）
            resolution: 分辨率
            style: 视频风格
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 生成结果，包含视频文件路径等信息
        """
        # 当前为模拟实现，实际使用时请替换为真实API调用
        system_logger.log_api_call(
            service=f"video_generation_{self.model_name}",
            endpoint="generate_video",
            params={
                "prompt": prompt,
                "visual_description": visual_description,
                "duration": duration,
                "resolution": resolution,
                "style": style,
                "model_version": self.model_version,
                **kwargs
            }
        )
        
        # 模拟API调用延迟
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # 模拟文件生成
        file_id = str(uuid.uuid4())
        file_path = f"mock_videos/{file_id}.mp4"
        
        # 模拟API响应
        return {
            "success": True,
            "file_path": file_path,
            "duration": duration,
            "resolution": resolution,
            "model": self.model_name,
            "model_version": self.model_version,
            "generation_params": {
                "prompt": prompt,
                "style": style,
                **kwargs
            }
        }

class VisualAgent(BaseAgent):
    """视觉生成代理，负责生成视频片段"""
    
    # 支持的视频生成模型映射
    MODEL_MAP = {
        "keling": "可灵视频生成",
        "pika": "Pika Labs",
        "runway": "Runway Gen-2",
        "wan": "Wan动画生成"
    }
    
    def __init__(self):
        super().__init__(agent_type=AgentType.VISUAL, name="视觉生成代理")
        self.video_apis = {}  # 存储不同模型的API实例
        
    async def initialize(self):
        """初始化代理"""
        await super().initialize()
        
        # 预初始化所有支持的视频模型API
        for model_name, api_key_name in {
            "keling": "KELING_API_KEY",
            "pika": "PIKA_API_KEY",
            "runway": "RUNWAY_API_KEY",
            "wan": "WAN_API_KEY"
        }.items():
            if api_key := API_KEYS.get(api_key_name):
                self.video_apis[model_name] = VideoGenerationAPI(model_name, api_key)
                self.logger.info(f"已初始化{self.MODEL_MAP.get(model_name, model_name)}视频生成API")
            else:
                self.logger.warning(f"未找到{model_name}模型的API密钥，无法初始化该模型")
                
        self.logger.info(f"视觉生成代理初始化完成，支持的模型: {list(self.video_apis.keys())}")
        
    async def handle_command(self, message: Message) -> Optional[Message]:
        """
        处理命令消息
        
        Args:
            message: 接收到的消息
            
        Returns:
            Optional[Message]: 响应消息
        """
        command = message.content.get("command")
        self.logger.info(f"收到命令: {command}")
        
        if command == "generate_videos":
            # 生成视频片段
            try:
                parameters = message.content.get("parameters", {})
                session_id = parameters.get("session_id")
                
                if not session_id:
                    return self.create_error_response(message, "缺少session_id参数")
                
                self.logger.info(f"开始为会话{session_id}生成视频")
                video_assets = await self._generate_videos(parameters, session_id)
                
                # 返回视频资产列表
                return self.create_success_response(message, {
                    "success": True,
                    "data": {
                        "video_assets": video_assets
                    }
                })
                
            except Exception as e:
                self.logger.error(f"视频生成失败: {str(e)}")
                return self.create_error_response(message, f"视频生成失败: {str(e)}")
                
        elif command == "regenerate_video":
            # 重新生成视频片段
            try:
                parameters = message.content.get("parameters", {})
                session_id = parameters.get("session_id")
                
                if not session_id:
                    return self.create_error_response(message, "缺少session_id参数")
                    
                self.logger.info(f"开始为会话{session_id}重新生成视频")
                video_asset = await self._regenerate_video(parameters, session_id)
                
                # 返回重新生成的视频资产
                return self.create_success_response(message, {
                    "success": True,
                    "data": {
                        "video_asset": video_asset
                    }
                })
                
            except Exception as e:
                self.logger.error(f"视频重新生成失败: {str(e)}")
                return self.create_error_response(message, f"视频重新生成失败: {str(e)}")
        else:
            return self.create_error_response(message, f"未知命令: {command}")
    
    async def _generate_videos(self, parameters: Dict[str, Any], session_id: str) -> List[Dict[str, Any]]:
        """
        生成视频
        
        Args:
            parameters: 参数
            session_id: 会话ID
            
        Returns:
            List[Dict[str, Any]]: 生成的视频资产列表
        """
        script_sections = parameters.get("script_sections", [])
        video_model = parameters.get("video_model", "wan")  # 默认使用wan模型
        resolution = parameters.get("resolution", "1080x1920")
        style = parameters.get("style", "realistic")
        
        # 检查选择的模型是否可用
        if video_model not in self.video_apis:
            self.logger.warning(f"所选模型 {video_model} 不可用，将使用默认模型")
            available_models = list(self.video_apis.keys())
            if not available_models:
                raise ValueError("没有可用的视频生成模型")
            video_model = available_models[0]
            
        self.logger.info(f"使用{self.MODEL_MAP.get(video_model, video_model)}模型生成视频，风格: {style}")
        
        # 获取所选模型的API实例
        api = self.video_apis[video_model]
        
        # 并行生成所有视频片段
        tasks = []
        for section in script_sections:
            task = self._generate_single_video(
                api=api,
                section_id=section["id"],
                content=section["content"],
                visual_description=section["visual_description"],
                duration=section["duration"],
                resolution=resolution,
                style=style,
                session_id=session_id
            )
            tasks.append(task)
            
        video_assets = await asyncio.gather(*tasks)
        self.logger.info(f"已为会话{session_id}生成{len(video_assets)}个视频片段")
        
        return video_assets
        
    async def _generate_single_video(self,
                                  api: VideoGenerationAPI,
                                  section_id: str,
                                  content: str,
                                  visual_description: str,
                                  duration: float,
                                  resolution: str,
                                  style: str,
                                  session_id: str) -> Dict[str, Any]:
        """
        生成单个视频片段
        
        Args:
            api: 视频生成API实例
            section_id: 脚本片段ID
            content: 脚本内容
            visual_description: 视觉描述
            duration: 时长（秒）
            resolution: 分辨率
            style: 风格
            session_id: 会话ID
            
        Returns:
            Dict[str, Any]: 生成的视频资产
        """
        self.logger.info(f"为片段{section_id}生成视频，时长: {duration}秒")
        
        # 获取prompt管理器
        prompt_manager = get_prompt_manager()
        
        # 准备模板参数
        template_params = {
            "content": content,
            "visual_description": visual_description
        }
        
        # 渲染prompt模板
        prompt = prompt_manager.render_template(
            file_key="visual_agent_prompts", 
            template_key="generate_video", 
            parameters=template_params
        )
        
        # 获取模型参数配置
        model_params = prompt_manager.get_parameters(
            file_key="visual_agent_prompts",
            template_key="generate_video"
        )
        
        # 从配置中获取参数，如果未配置则使用默认值
        temperature = model_params.get("temperature", MODEL_CONFIG.get(api.model_name, {}).get("temperature", 0.7))
        top_p = model_params.get("top_p", MODEL_CONFIG.get(api.model_name, {}).get("top_p", 0.9))
        style_strength = model_params.get("style_strength", MODEL_CONFIG.get(api.model_name, {}).get("style_strength", 0.8))
        
        # 调用API生成视频
        generation_result = await api.generate_video(
            prompt=prompt,
            visual_description=visual_description,
            duration=duration,
            resolution=resolution,
            style=style,
            temperature=temperature,
            top_p=top_p,
            style_strength=style_strength
        )
        
        # 生成唯一ID
        video_id = f"video_{uuid.uuid4().hex[:8]}"
        
        # 创建视频资产对象
        video_asset = {
            "id": video_id,
            "section_id": section_id,
            "file_path": generation_result.get("file_path", f"./temp/{session_id}/videos/{video_id}.mp4"),
            "preview_image": generation_result.get("preview_image", f"./temp/{session_id}/previews/{video_id}.jpg"),
            "duration": duration,
            "resolution": resolution,
            "prompt": prompt,
            "visual_description": visual_description,
            "model": api.model_name,
            "style": style,
            "created_at": datetime.now().isoformat()
        }
        
        return video_asset
        
    async def _regenerate_video(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        重新生成视频
        
        Args:
            parameters: 参数
            session_id: 会话ID
            
        Returns:
            Dict[str, Any]: 重新生成的视频资产
        """
        section_id = parameters.get("section_id")
        content = parameters.get("content")
        visual_description = parameters.get("visual_description")
        duration = parameters.get("duration", 10.0)
        resolution = parameters.get("resolution", "1080x1920")
        style = parameters.get("style", "realistic")
        video_model = parameters.get("video_model", "wan")
        feedback = parameters.get("feedback", "")
        
        if not all([section_id, content, visual_description]):
            raise ValueError("缺少必要的参数")
            
        # 检查选择的模型是否可用
        if video_model not in self.video_apis:
            self.logger.warning(f"所选模型 {video_model} 不可用，将使用默认模型")
            available_models = list(self.video_apis.keys())
            if not available_models:
                raise ValueError("没有可用的视频生成模型")
            video_model = available_models[0]
            
        self.logger.info(f"根据反馈 '{feedback}' 重新生成视频")
        
        # 获取所选模型的API实例
        api = self.video_apis[video_model]
        
        # 调整视觉描述，结合用户反馈
        if feedback:
            visual_description = f"{visual_description}\n考虑用户反馈: {feedback}"
            
        # 生成视频
        video_asset = await self._generate_single_video(
            api=api,
            section_id=section_id,
            content=content,
            visual_description=visual_description,
            duration=duration,
            resolution=resolution,
            style=style,
            session_id=session_id
        )
        
        return video_asset
        
    async def _evaluate_video_quality(self, video_path: str) -> float:
        """
        评估视频质量
        
        Args:
            video_path: 视频路径
            
        Returns:
            float: 质量评分（0-1）
        """
        # 模拟评估过程
        await asyncio.sleep(0.5)
        
        # 随机生成评分，实际系统中应该有真实的评估逻辑
        quality_score = random.uniform(0.7, 0.95)
        
        return quality_score 

    async def regenerate_video(
            self,
            session_id: str,
            video_id: str,
            section_id: str,
            content: str,
            visual_description: str,
            adjustment: str,
            duration: float,
            resolution: str = "1080x1920",
            video_model: str = "wan",
            style: str = "realistic"
        ) -> Dict[str, Any]:
        """
        重新生成视频，针对用户的调整意见
        
        Args:
            session_id: 会话ID
            video_id: 原视频ID
            section_id: 片段ID
            content: 脚本内容
            visual_description: 视觉描述
            adjustment: 调整要求
            duration: 视频时长
            resolution: 分辨率
            video_model: 视频模型
            style: 风格
            
        Returns:
            Dict[str, Any]: 重新生成的视频资产
        """
        self.logger.info(f"根据调整意见重新生成视频: {video_id}")
        
        # 检查模型是否可用
        if video_model not in self.video_apis:
            self.logger.warning(f"请求的视频模型 {video_model} 不可用，尝试使用其他模型")
            available_models = list(self.video_apis.keys())
            if not available_models:
                raise ValueError("没有可用的视频生成模型")
            video_model = available_models[0]
            
        api = self.video_apis[video_model]
        
        # 获取prompt管理器
        prompt_manager = get_prompt_manager()
        
        # 准备模板参数
        template_params = {
            "content": content,
            "visual_description": visual_description,
            "adjustment": adjustment
        }
        
        # 渲染prompt模板
        prompt = prompt_manager.render_template(
            file_key="visual_agent_prompts", 
            template_key="regenerate_video", 
            parameters=template_params
        )
        
        # 获取模型参数配置
        model_params = prompt_manager.get_parameters(
            file_key="visual_agent_prompts",
            template_key="regenerate_video"
        )
        
        # 从配置中获取参数，如果未配置则使用默认值
        temperature = model_params.get("temperature", MODEL_CONFIG.get(api.model_name, {}).get("temperature", 0.8))
        top_p = model_params.get("top_p", MODEL_CONFIG.get(api.model_name, {}).get("top_p", 0.95))
        style_strength = model_params.get("style_strength", MODEL_CONFIG.get(api.model_name, {}).get("style_strength", 0.9))
        
        # 调用API重新生成视频
        generation_result = await api.generate_video(
            prompt=prompt,
            visual_description=visual_description,
            duration=duration,
            resolution=resolution,
            style=style,
            temperature=temperature,
            top_p=top_p,
            style_strength=style_strength
        )
        
        # 生成新的唯一ID
        new_video_id = f"video_{uuid.uuid4().hex[:8]}"
        
        # 创建新的视频资产对象
        video_asset = {
            "id": new_video_id,
            "section_id": section_id,
            "file_path": generation_result.get("file_path", f"./temp/{session_id}/videos/{new_video_id}.mp4"),
            "preview_image": generation_result.get("preview_image", f"./temp/{session_id}/previews/{new_video_id}.jpg"),
            "duration": duration,
            "resolution": resolution,
            "prompt": prompt,
            "visual_description": visual_description,
            "adjustment": adjustment,
            "model": api.model_name,
            "style": style,
            "original_video_id": video_id,
            "created_at": datetime.now().isoformat()
        }
        
        return video_asset 