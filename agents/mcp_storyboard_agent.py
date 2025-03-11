import json
import uuid
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx
import os

from models.mcp import (
    MCPMessage, MCPMessageType, MCPStatus, MCPPriority, MCPCommand, MCPResponse,
    create_command_message
)
from agents.mcp_base_agent import MCPBaseAgent
from models.video import (
    Script, ScriptSection, Storyboard, StoryboardFrame, StoryboardImage, 
    StoryboardTransition, StoryboardStyle, StoryboardFrameType, 
    StoryboardImageSource, ShotType, TransitionType
)
from utils.file_manager import file_manager
from config.config import SYSTEM_CONFIG

# 检查是否处于测试模式
def is_test_mode():
    try:
        import sys
        return any("test" in arg for arg in sys.argv)
    except:
        return False


class MCPStoryboardAgent(MCPBaseAgent):
    """基于MCP协议的分镜代理，负责处理分镜相关任务
    
    分镜内容由MCPContentAgent生成，通过mcp_central_agent调用工作流传递给MCPStoryboardAgent。
    MCPStoryboardAgent不自行生成分镜内容，而是负责处理、渲染和管理分镜数据。
    """
    
    def __init__(self):
        """初始化分镜代理"""
        super().__init__(
            agent_id="storyboard_agent",
            agent_name="Storyboard Agent"
        )
        self.httpx_client = None
        self.replicate_api_key = None
        self.douimg_api_key = None
        self.test_mode = is_test_mode()
        
    async def on_start(self):
        """代理启动时的自定义逻辑"""
        try:
            # 初始化HTTP客户端
            self.httpx_client = httpx.AsyncClient()
            
            # 获取图像生成API密钥
            self.replicate_api_key = SYSTEM_CONFIG.get("replicate_api_key") or os.getenv("REPLICATE_API_KEY")
            if not self.replicate_api_key and not self.test_mode:
                self.logger.warning("Replicate API key not found, Replicate image generation will be unavailable")
                
            self.douimg_api_key = SYSTEM_CONFIG.get("douimg_api_key") or os.getenv("DOUIMG_API_KEY")
            if not self.douimg_api_key and not self.test_mode:
                self.logger.warning("豆包 API key not found, 豆包 image generation will be unavailable")
            
            self.logger.info("MCP Storyboard Agent initialized and ready")
            
        except Exception as e:
            self.logger.error(f"Error initializing Storyboard agent: {str(e)}")
    
    async def on_stop(self):
        """代理停止时的自定义逻辑"""
        if self.httpx_client:
            await self.httpx_client.aclose()
    
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
            if command.action == "process_storyboard":
                # 处理从MCPContentAgent收到的分镜内容
                storyboard_data = command.parameters.get("storyboard_data")
                script_data = command.parameters.get("script")
                
                if not storyboard_data or not script_data:
                    return message.create_error_response(
                        error_code="INVALID_PARAMETERS",
                        error_message="Missing required parameters: storyboard_data and script"
                    )
                
                # 处理分镜内容，创建Storyboard对象
                storyboard = await self._process_storyboard(storyboard_data, script_data, session_id)
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message="Storyboard processed successfully",
                    data={"storyboard": storyboard.dict() if storyboard else None}
                )
                
            elif command.action == "generate_storyboard_images":
                # 为分镜生成图像
                storyboard_data = command.parameters.get("storyboard")
                image_source = command.parameters.get("image_source", "replicate")
                image_style = command.parameters.get("image_style", "realistic")
                
                if not storyboard_data:
                    return message.create_error_response(
                        error_code="INVALID_PARAMETERS",
                        error_message="Missing required parameter: storyboard"
                    )
                
                # 将数据转换为Storyboard对象
                storyboard = Storyboard(**storyboard_data)
                
                # 生成分镜图像
                updated_storyboard = await self._generate_storyboard_images(
                    storyboard,
                    image_source,
                    image_style,
                    session_id
                )
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message="Storyboard images generated successfully",
                    data={"storyboard": updated_storyboard.dict() if updated_storyboard else None}
                )
                
            else:
                return message.create_error_response(
                    error_code="UNKNOWN_COMMAND",
                    error_message=f"Unknown action: {command.action}"
                )
                
        except Exception as e:
            self.logger.error(f"Error handling command: {str(e)}")
            return message.create_error_response(
                error_code="COMMAND_ERROR",
                error_message=f"Error processing command: {str(e)}"
            )
    
    async def _process_storyboard(self, storyboard_data: Dict[str, Any], script_data: Dict[str, Any], session_id: str) -> Optional[Storyboard]:
        """
        处理分镜数据，创建Storyboard对象
        
        Args:
            storyboard_data: 分镜数据
            script_data: 脚本数据
            session_id: 会话ID
            
        Returns:
            处理后的分镜对象
        """
        try:
            # 将脚本数据转换为Script对象
            script = Script(**script_data)
            
            # 创建分镜ID
            storyboard_id = f"storyboard_{uuid.uuid4().hex[:8]}"
            
            # 解析分镜帧
            frames = []
            for frame_data in storyboard_data.get("frames", []):
                frames.append(StoryboardFrame(**frame_data))
            
            # 计算总时长
            total_duration = sum(frame.duration for frame in frames)
            
            # 创建Storyboard对象
            storyboard = Storyboard(
                id=storyboard_id,
                script_id=script.id,
                title=f"{script.title} Storyboard",
                style=StoryboardStyle(storyboard_data.get("style", "storyboard")),
                frames=frames,
                transitions=[],  # 初始时没有转场特效
                images=[],  # 初始时没有图像
                total_duration=total_duration,
                creator_id=script.creator_id,
                status="draft",
                metadata={
                    "processed_at": datetime.now().isoformat()
                }
            )
            
            # 保存分镜到文件
            storyboard_json = storyboard.model_dump_json(indent=2)
            file_path = await file_manager.save_json_file(
                data=json.loads(storyboard_json),
                filename=f"storyboard_{storyboard.id}.json",
                session_id=session_id,
                subdir="storyboards"
            )
            
            self.logger.info(f"Storyboard processed and saved to {file_path}")
            return storyboard
            
        except Exception as e:
            self.logger.error(f"Error processing storyboard: {str(e)}")
            raise
    
    async def _generate_storyboard_images(self, storyboard: Storyboard, image_source: str, image_style: str, session_id: str) -> Optional[Storyboard]:
        """
        为分镜生成图像
        
        Args:
            storyboard: 分镜对象
            image_source: 图像来源 (replicate, douimg, mock)
            image_style: 图像风格
            session_id: 会话ID
            
        Returns:
            更新后的分镜对象，包含图像
        """
        self.logger.info(f"Generating storyboard images using {image_source}, style: {image_style}")
        
        # 检查是否为测试模式或使用模拟源
        if self.test_mode or image_source == "mock":
            self.logger.info("Using mock image generation")
            return await self._generate_mock_images(storyboard, image_style, session_id)
        
        # 根据图像来源选择不同的API
        if image_source == "replicate":
            if not self.replicate_api_key:
                self.logger.warning("Replicate API key not found, falling back to mock mode")
                return await self._generate_mock_images(storyboard, image_style, session_id)
            
            # 使用Replicate API生成图像
            return await self._generate_replicate_images(storyboard, image_style, session_id)
            
        elif image_source == "douimg":
            if not self.douimg_api_key:
                self.logger.warning("豆包 API key not found, falling back to mock mode")
                return await self._generate_mock_images(storyboard, image_style, session_id)
            
            # 使用豆包API生成图像
            return await self._generate_douimg_images(storyboard, image_style, session_id)
            
        else:
            self.logger.warning(f"Unknown image source: {image_source}, falling back to mock mode")
            return await self._generate_mock_images(storyboard, image_style, session_id)
    
    async def _generate_replicate_images(self, storyboard: Storyboard, style: str, session_id: str) -> Storyboard:
        """使用Replicate API生成图像"""
        try:
            # 每个帧生成一个图像
            images = []
            
            for i, frame in enumerate(storyboard.frames):
                self.logger.info(f"Generating image for frame {i+1}/{len(storyboard.frames)}")
                
                # 构建提示词
                prompt = f"{frame.visual_description} Style: {style}"
                
                # 调用Replicate API
                payload = {
                    "prompt": prompt,
                    "negative_prompt": "bad quality, low resolution",
                    "width": 1024,
                    "height": 1024,
                    "num_outputs": 1
                }
                
                headers = {
                    "Authorization": f"Token {self.replicate_api_key}",
                    "Content-Type": "application/json"
                }
                
                # 发送请求
                response = await self.httpx_client.post(
                    "https://api.replicate.com/v1/predictions",
                    json=payload,
                    headers=headers
                )
                
                data = await response.json()
                
                if response.status_code != 201:
                    self.logger.error(f"Error calling Replicate API: {data}")
                    continue
                
                # 获取预测ID
                prediction_id = data.get("id")
                if not prediction_id:
                    self.logger.error("No prediction ID returned from Replicate API")
                    continue
                
                # 轮询结果
                for _ in range(30):  # 最多等待30次
                    await asyncio.sleep(2)  # 等待2秒
                    
                    status_response = await self.httpx_client.get(
                        f"https://api.replicate.com/v1/predictions/{prediction_id}",
                        headers=headers
                    )
                    
                    status_data = await status_response.json()
                    
                    if status_data.get("status") == "succeeded":
                        output_urls = status_data.get("output", [])
                        if output_urls and isinstance(output_urls, list) and len(output_urls) > 0:
                            image_url = output_urls[0]
                            
                            # 创建StoryboardImage对象
                            image = StoryboardImage(
                                id=f"img_{uuid.uuid4().hex[:8]}",
                                frame_id=frame.id,
                                url=image_url,
                                width=1024,
                                height=1024,
                                source=StoryboardImageSource.REPLICATE,
                                prompt=prompt,
                                metadata={
                                    "style": style,
                                    "generated_at": datetime.now().isoformat(),
                                    "prediction_id": prediction_id
                                }
                            )
                            
                            images.append(image)
                            break
                    
                    elif status_data.get("status") == "failed":
                        self.logger.error(f"Replicate prediction failed: {status_data.get('error')}")
                        break
            
            # 更新分镜对象，添加图像
            storyboard.images = images
            
            # 保存更新后的分镜到文件
            storyboard_json = storyboard.model_dump_json(indent=2)
            file_path = await file_manager.save_json_file(
                data=json.loads(storyboard_json),
                filename=f"storyboard_{storyboard.id}_with_images.json",
                session_id=session_id,
                subdir="storyboards"
            )
            
            self.logger.info(f"Storyboard images generated and saved to {file_path}")
            return storyboard
            
        except Exception as e:
            self.logger.error(f"Error generating Replicate images: {str(e)}")
            # 出错时回退到模拟模式
            return await self._generate_mock_images(storyboard, style, session_id)
    
    async def _generate_douimg_images(self, storyboard: Storyboard, style: str, session_id: str) -> Storyboard:
        """使用豆包API生成图像"""
        try:
            # 由于没有具体的豆包API实现，这里简单模拟
            self.logger.info("豆包API图像生成尚未实现，使用模拟数据")
            return await self._generate_mock_images(storyboard, style, session_id)
            
        except Exception as e:
            self.logger.error(f"Error generating Douimg images: {str(e)}")
            return await self._generate_mock_images(storyboard, style, session_id)
    
    async def _generate_mock_images(self, storyboard: Storyboard, style: str, session_id: str) -> Storyboard:
        """生成模拟图像数据"""
        self.logger.info("Generating mock images")
        
        # 为每个分镜帧添加一个模拟图像
        images = []
        for i, frame in enumerate(storyboard.frames):
            image = StoryboardImage(
                id=f"img_{uuid.uuid4().hex[:8]}",
                frame_id=frame.id,
                url=f"https://picsum.photos/seed/{i+1}/1024/1024",  # 使用随机图像URL
                width=1024,
                height=1024,
                source=StoryboardImageSource.MOCK,
                prompt=frame.visual_description,
                metadata={
                    "style": style,
                    "generated_at": datetime.now().isoformat(),
                    "mock": True
                }
            )
            images.append(image)
        
        # 更新分镜对象，添加图像
        storyboard.images = images
        
        # 保存更新后的分镜到文件
        storyboard_json = storyboard.model_dump_json(indent=2)
        file_path = await file_manager.save_json_file(
            data=json.loads(storyboard_json),
            filename=f"storyboard_{storyboard.id}_with_images.json",
            session_id=session_id,
            subdir="storyboards"
        )
        
        self.logger.info(f"Mock storyboard images generated and saved to {file_path}")
        return storyboard 