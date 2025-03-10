import asyncio
import json
import uuid
import logging
import os
import random
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from models.mcp import (
    MCPMessage, MCPMessageType, MCPStatus, MCPPriority, MCPCommand, MCPResponse, MCPError,
    create_command_message
)
from agents.mcp_base_agent import MCPBaseAgent
from utils.prompt_manager import get_prompt_manager
from dotenv import load_dotenv


class VideoGenerationAPI:
    """视频生成API接口封装"""

    def __init__(self, model_name: str, api_key: str):
        """
        初始化视频生成API
        
        Args:
            model_name: 模型名称
            api_key: API密钥
        """
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = f"https://api.example.com/{model_name}"
        self.model_version = "1.0"
    
    async def generate_video(
        self,
        prompt: str,
        visual_description: str,
        duration: float,
        resolution: str = "1080x1920",
        style: str = "realistic",
        temperature: float = 0.7,
        top_p: float = 0.9,
        style_strength: float = 0.8,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成视频
        
        Args:
            prompt: 提示文本
            visual_description: 视觉描述
            duration: 视频时长(秒)
            resolution: 分辨率
            style: 视频风格
            temperature: 温度参数
            top_p: top-p参数
            style_strength: 风格强度
            
        Returns:
            生成结果，包含文件路径等信息
        """
        # 模拟API调用，实际应用中应该调用真实API
        # 模拟处理延迟
        processing_time = min(duration * 0.2, 2.0)  # 模拟每秒视频需要0.2秒处理时间，最长2秒
        await asyncio.sleep(processing_time)
        
        # 生成唯一ID
        video_id = f"video_{uuid.uuid4().hex[:10]}"
        
        # 创建临时文件夹路径
        os.makedirs(f"./temp/videos", exist_ok=True)
        os.makedirs(f"./temp/previews", exist_ok=True)
        
        # 文件路径
        file_path = f"./temp/videos/{video_id}.mp4"
        preview_path = f"./temp/previews/{video_id}.jpg"
        
        # 创建空文件模拟视频
        with open(file_path, "w") as f:
            f.write(f"MOCK VIDEO: {prompt}\nStyle: {style}\nDuration: {duration}s")
            
        with open(preview_path, "w") as f:
            f.write(f"MOCK PREVIEW: {prompt}")
        
        return {
            "id": video_id,
            "file_path": file_path,
            "preview_image": preview_path,
            "duration": duration,
            "resolution": resolution,
            "prompt": prompt,
            "visual_description": visual_description,
            "model": self.model_name,
            "created_at": datetime.now().isoformat()
        }


class MCPVisualAgent(MCPBaseAgent):
    """基于MCP协议的视觉代理，负责生成视频内容"""
    
    # 支持的视频生成模型映射
    MODEL_MAP = {
        "keling": "可灵AI视频生成",
        "pika": "Pika Labs",
        "runway": "RunwayML",
        "wan": "万兴爱创"
    }
    
    def __init__(self):
        """初始化视觉代理"""
        super().__init__(
            agent_id="visual_agent",
            agent_name="Visual Generation Agent"
        )
        # 视频生成API实例
        self.video_apis: Dict[str, VideoGenerationAPI] = {}
        
        # 模型参数配置
        self.model_config = {
            "keling": {"temperature": 0.7, "top_p": 0.9, "style_strength": 0.8},
            "pika": {"temperature": 0.8, "top_p": 0.95, "style_strength": 0.85},
            "runway": {"temperature": 0.75, "top_p": 0.9, "style_strength": 0.8},
            "wan": {"temperature": 0.7, "top_p": 0.85, "style_strength": 0.75}
        }
    
    async def on_start(self):
        """代理启动时初始化视频生成API"""
        try:
            # 从环境变量加载API密钥
            load_dotenv()
            
            # 初始化支持的视频生成API
            api_keys = {
                "keling": os.getenv("KELING_API_KEY", ""),
                "pika": os.getenv("PIKA_API_KEY", ""),
                "runway": os.getenv("RUNWAY_API_KEY", ""),
                "wan": os.getenv("WAN_API_KEY", "")
            }
            
            # 只初始化有API密钥的模型
            for model_name, api_key in api_keys.items():
                if api_key:
                    self.video_apis[model_name] = VideoGenerationAPI(model_name, api_key)
                    self.logger.info(f"Initialized {self.MODEL_MAP.get(model_name, model_name)} API")
            
            if not self.video_apis:
                self.logger.warning("No video generation APIs initialized, using mock mode")
                # 至少初始化一个模拟API
                self.video_apis["mock"] = VideoGenerationAPI("mock", "mock_key")
                
            self.logger.info(f"Visual Agent initialized with {len(self.video_apis)} video generation APIs")
            
        except Exception as e:
            self.logger.error(f"Error initializing video generation APIs: {str(e)}")
    
    async def handle_command(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理命令消息
        
        Args:
            message: 命令消息
            
        Returns:
            响应消息
        """
        # 验证是否为命令消息
        if message.header.message_type != MCPMessageType.COMMAND or not isinstance(message.body, MCPCommand):
            return message.create_error_response(
                error_code="INVALID_MESSAGE",
                error_message="Expected a command message"
            )
        
        # 根据命令类型分发处理
        command = message.body
        session_id = message.header.session_id or "default_session"
        
        try:
            if command.action == "generate_videos":
                # 生成视频
                video_assets = await self._generate_videos(command.parameters, session_id)
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message=f"Generated {len(video_assets)} video assets",
                    data={"video_assets": video_assets}
                )
                
            elif command.action == "regenerate_video":
                # 重新生成特定视频
                video_asset = await self._regenerate_video(command.parameters, session_id)
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message="Video regenerated successfully",
                    data={"video_asset": video_asset}
                )
                
            elif command.action == "get_available_models":
                # 获取可用模型列表
                available_models = list(self.video_apis.keys())
                model_display_names = {model: self.MODEL_MAP.get(model, model) for model in available_models}
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message=f"Found {len(available_models)} available video generation models",
                    data={
                        "available_models": available_models,
                        "model_display_names": model_display_names
                    }
                )
                
            else:
                # 未知命令
                return message.create_error_response(
                    error_code="UNKNOWN_COMMAND",
                    error_message=f"Unknown command action: {command.action}"
                )
                
        except Exception as e:
            self.logger.error(f"Error handling command {command.action}: {str(e)}")
            return message.create_error_response(
                error_code="PROCESSING_ERROR",
                error_message=f"Error processing command: {str(e)}"
            )
    
    async def _generate_videos(self, parameters: Dict[str, Any], session_id: str) -> List[Dict[str, Any]]:
        """
        生成多个视频片段
        
        Args:
            parameters: 生成参数
            session_id: 会话ID
            
        Returns:
            生成的视频资产列表
        """
        try:
            # 提取参数
            script_sections = parameters.get("script_sections", [])
            video_model = parameters.get("video_model", "wan")
            resolution = parameters.get("resolution", "1080x1920")
            style = parameters.get("style", "realistic")
            
            self.logger.info(f"Generating videos for {len(script_sections)} script sections using model {video_model}")
            
            # 检查选择的模型是否可用
            if video_model not in self.video_apis:
                self.logger.warning(f"Requested video model {video_model} is not available")
                available_models = list(self.video_apis.keys())
                if not available_models:
                    raise ValueError("No video generation models available")
                    
                video_model = available_models[0]
                self.logger.info(f"Using {video_model} instead")
            
            # 获取API实例
            api = self.video_apis[video_model]
            
            # 为每个场景生成视频
            video_assets = []
            
            for section in script_sections:
                try:
                    section_id = section.get("section_id", f"section_{len(video_assets)}")
                    content = section.get("content", "")
                    visual_description = section.get("visual_description", "")
                    duration = float(section.get("duration", 5.0))
                    
                    # 使用prompt管理器获取并渲染模板
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
                    temperature = model_params.get("temperature", self.model_config.get(api.model_name, {}).get("temperature", 0.7))
                    top_p = model_params.get("top_p", self.model_config.get(api.model_name, {}).get("top_p", 0.9))
                    style_strength = model_params.get("style_strength", self.model_config.get(api.model_name, {}).get("style_strength", 0.8))
                    
                    # 生成视频
                    video_asset = await api.generate_video(
                        prompt=prompt,
                        visual_description=visual_description,
                        duration=duration,
                        resolution=resolution,
                        style=style,
                        temperature=temperature,
                        top_p=top_p,
                        style_strength=style_strength
                    )
                    
                    # 添加部分字段
                    video_asset["section_id"] = section_id
                    video_asset["style"] = style
                    
                    video_assets.append(video_asset)
                    self.logger.info(f"Generated video for section {section_id}, duration: {duration}s")
                    
                except Exception as e:
                    self.logger.error(f"Error generating video for section {section.get('section_id', 'unknown')}: {str(e)}")
                    # 继续处理其他部分，而不是整体失败
            
            return video_assets
            
        except Exception as e:
            self.logger.error(f"Error in generate_videos: {str(e)}")
            raise
    
    async def _regenerate_video(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        重新生成特定视频
        
        Args:
            parameters: 重新生成参数
            session_id: 会话ID
            
        Returns:
            重新生成的视频资产
        """
        try:
            # 提取参数
            video_id = parameters.get("video_id")
            section_id = parameters.get("section_id")
            content = parameters.get("content", "")
            visual_description = parameters.get("visual_description", "")
            adjustment = parameters.get("adjustment", "")
            duration = float(parameters.get("duration", 5.0))
            resolution = parameters.get("resolution", "1080x1920")
            video_model = parameters.get("video_model", "wan")
            style = parameters.get("style", "realistic")
            
            if not video_id or not section_id:
                raise ValueError("Missing required parameters: video_id and section_id")
            
            self.logger.info(f"Regenerating video {video_id} for section {section_id}")
            
            # 检查选择的模型是否可用
            if video_model not in self.video_apis:
                self.logger.warning(f"Requested video model {video_model} is not available")
                available_models = list(self.video_apis.keys())
                if not available_models:
                    raise ValueError("No video generation models available")
                    
                video_model = available_models[0]
                self.logger.info(f"Using {video_model} instead")
            
            # 获取API实例
            api = self.video_apis[video_model]
            
            # 使用prompt管理器获取并渲染模板
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
            temperature = model_params.get("temperature", self.model_config.get(api.model_name, {}).get("temperature", 0.8))
            top_p = model_params.get("top_p", self.model_config.get(api.model_name, {}).get("top_p", 0.95))
            style_strength = model_params.get("style_strength", self.model_config.get(api.model_name, {}).get("style_strength", 0.9))
            
            # 生成视频
            video_asset = await api.generate_video(
                prompt=prompt,
                visual_description=visual_description,
                duration=duration,
                resolution=resolution,
                style=style,
                temperature=temperature,
                top_p=top_p,
                style_strength=style_strength
            )
            
            # 添加部分字段
            video_asset["section_id"] = section_id
            video_asset["style"] = style
            video_asset["original_video_id"] = video_id
            video_asset["adjustment"] = adjustment
            
            self.logger.info(f"Regenerated video for section {section_id}, duration: {duration}s")
            
            return video_asset
            
        except Exception as e:
            self.logger.error(f"Error in regenerate_video: {str(e)}")
            raise
    
    async def _evaluate_video_quality(self, video_path: str) -> float:
        """
        评估视频质量
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            质量评分（0-1之间）
        """
        # 模拟评估，返回0.7-1.0之间的随机分数
        await asyncio.sleep(0.5)  # 模拟评估时间
        quality_score = random.uniform(0.7, 1.0)
        return quality_score 