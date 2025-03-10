import asyncio
import uuid
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from models.message import Message, MessageType, AgentType, WorkflowState
from models.user import VideoCreationRequest
from models.video import Script, FinalVideo
from agents.base_agent import BaseAgent
from utils.logger import system_logger
from config.config import SYSTEM_CONFIG, WORKFLOW_CONFIG


class CentralAgent(BaseAgent):
    """
    中央策略代理 - 系统的"导演"，负责全局协调与决策
    
    职责:
    - 接收用户输入，制定视频创作的总体策略
    - 根据用户选择，配置视频生成模型和音频工具
    - 为其他代理分配任务并设定优先级
    - 监控工作流程，解决代理间冲突，确保满足质量标准
    - 提供最终质量评估和优化建议
    """
    
    def __init__(self):
        super().__init__(AgentType.CENTRAL, "CentralAgent")
        self.active_sessions: Dict[str, WorkflowState] = {}
        self.pending_user_inputs: Dict[str, asyncio.Event] = {}
        self.user_responses: Dict[str, Any] = {}
        
    async def initialize(self):
        """初始化中央代理"""
        await super().initialize()
        self.logger.info("Central Agent initialized and ready to coordinate workflow")
        
    async def create_session(self, user_id: str, request: VideoCreationRequest) -> str:
        """
        创建新的视频创作会话
        
        Args:
            user_id: 用户ID
            request: 视频创建请求
            
        Returns:
            会话ID
        """
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        
        # 创建工作流状态
        workflow_state = WorkflowState(
            session_id=session_id,
            user_id=user_id,
            current_stage="initialization",
            started_at=datetime.now(),
            metadata={
                "request": request.dict(),
                "selected_models": {
                    "video": request.video_model,
                    "voice": request.voice_tool,
                    "music": request.music_tool,
                    "editing": request.editing_tool
                }
            }
        )
        
        # 保存会话
        self.active_sessions[session_id] = workflow_state
        
        self.logger.info(f"Created new session {session_id} for user {user_id}")
        
        # 启动工作流
        asyncio.create_task(self._run_workflow(session_id))
        
        return session_id
    
    async def _run_workflow(self, session_id: str):
        """
        运行视频创作工作流
        
        Args:
            session_id: 会话ID
        """
        try:
            workflow = self.active_sessions[session_id]
            self.logger.info(f"Starting workflow for session {session_id}")
            
            # 更新状态
            workflow.current_stage = "script_creation"
            
            # 1. 脚本创建阶段
            script = await self._create_script(session_id)
            if not script:
                self.logger.error(f"Failed to create script for session {session_id}")
                workflow.current_stage = "failed"
                return
                
            # 保存脚本到工作流状态
            workflow.created_assets["script"] = script.dict()
            
            # 2. 视频生成阶段
            workflow.current_stage = "video_generation"
            video_assets = await self._generate_videos(session_id, script)
            if not video_assets:
                self.logger.error(f"Failed to generate videos for session {session_id}")
                workflow.current_stage = "failed"
                return
                
            # 保存视频资产到工作流状态
            workflow.created_assets["video_assets"] = video_assets
            
            # 3. 音频生成阶段
            workflow.current_stage = "audio_generation"
            audio_assets = await self._generate_audio(session_id, script)
            if not audio_assets:
                self.logger.error(f"Failed to generate audio for session {session_id}")
                workflow.current_stage = "failed"
                return
                
            # 保存音频资产到工作流状态
            workflow.created_assets["audio_assets"] = audio_assets
            
            # 4. 后期制作阶段
            workflow.current_stage = "post_production"
            final_video = await self._post_production(session_id, script, video_assets, audio_assets)
            if not final_video:
                self.logger.error(f"Failed to complete post-production for session {session_id}")
                workflow.current_stage = "failed"
                return
                
            # 保存最终视频到工作流状态
            workflow.created_assets["final_video"] = final_video.dict()
            
            # 5. 分发阶段
            workflow.current_stage = "distribution"
            distribution_result = await self._distribute_video(session_id, final_video)
            
            # 完成工作流
            workflow.current_stage = "completed"
            workflow.completed_at = datetime.now()
            
            self.logger.info(f"Workflow completed for session {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error in workflow for session {session_id}: {str(e)}")
            if session_id in self.active_sessions:
                self.active_sessions[session_id].current_stage = "failed"
    
    async def _create_script(self, session_id: str) -> Optional[Script]:
        """
        创建视频脚本
        
        Args:
            session_id: 会话ID
            
        Returns:
            创建的脚本，如果失败则返回None
        """
        workflow = self.active_sessions[session_id]
        request = VideoCreationRequest(**workflow.metadata["request"])
        
        # 发送命令给内容创作代理
        command_content = {
            "action": "create_script",
            "parameters": {
                "theme": request.theme,
                "style": request.style.value,
                "script_type": request.script_type.value,
                "target_audience": request.target_audience,
                "duration": request.duration,
                "language": request.language,
                "keywords": request.keywords,
                "special_requirements": request.special_requirements
            },
            "session_id": session_id
        }
        
        message_id = await self.send_message(
            to_agent=AgentType.CONTENT,
            content=command_content
        )
        
        # 等待响应
        response = await self.wait_for_response(
            message_id=message_id,
            timeout=SYSTEM_CONFIG["agent_timeout"],
            from_agent=AgentType.CONTENT
        )
        
        if not response or not response.content.get("success"):
            error_msg = "Failed to create script" if not response else response.content.get("error", "Unknown error")
            self.logger.error(f"Script creation failed: {error_msg}")
            return None
            
        # 从响应中提取脚本
        script_data = response.content.get("data", {}).get("script")
        if not script_data:
            self.logger.error("No script data in response")
            return None
            
        # 询问用户是否接受脚本
        user_approved = await self._ask_user_approval(
            session_id=session_id,
            stage="script",
            content=script_data,
            message="请审核并确认脚本内容"
        )
        
        if not user_approved:
            self.logger.info(f"User rejected script for session {session_id}")
            # 可以在这里实现脚本修改逻辑
            return None
            
        # 将脚本数据转换为Script对象
        try:
            script = Script(**script_data)
            self.logger.info(f"Script created and approved for session {session_id}")
            return script
        except Exception as e:
            self.logger.error(f"Error parsing script data: {str(e)}")
            return None
    
    async def _generate_videos(self, session_id: str, script: Script) -> Optional[List[Dict[str, Any]]]:
        """
        生成视频片段
        
        Args:
            session_id: 会话ID
            script: 脚本
            
        Returns:
            视频资产列表，如果失败则返回None
        """
        workflow = self.active_sessions[session_id]
        request = VideoCreationRequest(**workflow.metadata["request"])
        
        # 发送命令给视觉生成代理
        command_content = {
            "action": "generate_videos",
            "parameters": {
                "script_id": script.id,
                "script_sections": [section.dict() for section in script.sections],
                "video_model": request.video_model.value,
                "resolution": request.resolution,
                "style": request.style.value
            },
            "session_id": session_id
        }
        
        message_id = await self.send_message(
            to_agent=AgentType.VISUAL,
            content=command_content
        )
        
        # 等待响应
        response = await self.wait_for_response(
            message_id=message_id,
            timeout=SYSTEM_CONFIG["agent_timeout"] * 2,  # 视频生成可能需要更长时间
            from_agent=AgentType.VISUAL
        )
        
        if not response or not response.content.get("success"):
            error_msg = "Failed to generate videos" if not response else response.content.get("error", "Unknown error")
            self.logger.error(f"Video generation failed: {error_msg}")
            return None
            
        # 从响应中提取视频资产
        video_assets = response.content.get("data", {}).get("video_assets")
        if not video_assets:
            self.logger.error("No video assets in response")
            return None
            
        # 询问用户是否接受视频
        user_approved = await self._ask_user_approval(
            session_id=session_id,
            stage="video",
            content=video_assets,
            message="请审核并确认生成的视频片段"
        )
        
        if not user_approved:
            self.logger.info(f"User rejected videos for session {session_id}")
            # 可以在这里实现视频重新生成逻辑
            return None
            
        self.logger.info(f"Videos generated and approved for session {session_id}")
        return video_assets
    
    async def _generate_audio(self, session_id: str, script: Script) -> Optional[List[Dict[str, Any]]]:
        """
        生成音频（语音和音乐）
        
        Args:
            session_id: 会话ID
            script: 脚本
            
        Returns:
            音频资产列表，如果失败则返回None
        """
        workflow = self.active_sessions[session_id]
        request = VideoCreationRequest(**workflow.metadata["request"])
        
        # 发送命令给音频生成代理
        command_content = {
            "action": "generate_audio",
            "parameters": {
                "script_id": script.id,
                "script_sections": [section.dict() for section in script.sections],
                "voice_tool": request.voice_tool.value,
                "music_tool": request.music_tool.value,
                "language": request.language,
                "voice_character": request.voice_character,
                "music_style": request.music_style
            },
            "session_id": session_id
        }
        
        message_id = await self.send_message(
            to_agent=AgentType.AUDIO,
            content=command_content
        )
        
        # 等待响应
        response = await self.wait_for_response(
            message_id=message_id,
            timeout=SYSTEM_CONFIG["agent_timeout"],
            from_agent=AgentType.AUDIO
        )
        
        if not response or not response.content.get("success"):
            error_msg = "Failed to generate audio" if not response else response.content.get("error", "Unknown error")
            self.logger.error(f"Audio generation failed: {error_msg}")
            return None
            
        # 从响应中提取音频资产
        audio_assets = response.content.get("data", {}).get("audio_assets")
        if not audio_assets:
            self.logger.error("No audio assets in response")
            return None
            
        # 询问用户是否接受音频
        user_approved = await self._ask_user_approval(
            session_id=session_id,
            stage="audio",
            content=audio_assets,
            message="请审核并确认生成的音频"
        )
        
        if not user_approved:
            self.logger.info(f"User rejected audio for session {session_id}")
            # 可以在这里实现音频重新生成逻辑
            return None
            
        self.logger.info(f"Audio generated and approved for session {session_id}")
        return audio_assets
    
    async def _post_production(self, 
                              session_id: str, 
                              script: Script, 
                              video_assets: List[Dict[str, Any]], 
                              audio_assets: List[Dict[str, Any]]) -> Optional[FinalVideo]:
        """
        后期制作，整合视频和音频
        
        Args:
            session_id: 会话ID
            script: 脚本
            video_assets: 视频资产
            audio_assets: 音频资产
            
        Returns:
            最终视频，如果失败则返回None
        """
        workflow = self.active_sessions[session_id]
        request = VideoCreationRequest(**workflow.metadata["request"])
        
        # 发送命令给后期制作代理
        command_content = {
            "action": "post_production",
            "parameters": {
                "script_id": script.id,
                "script_title": script.title,
                "video_assets": video_assets,
                "audio_assets": audio_assets,
                "editing_tool": request.editing_tool.value,
                "include_captions": request.include_captions,
                "resolution": request.resolution
            },
            "session_id": session_id
        }
        
        message_id = await self.send_message(
            to_agent=AgentType.POSTPROD,
            content=command_content
        )
        
        # 等待响应
        response = await self.wait_for_response(
            message_id=message_id,
            timeout=SYSTEM_CONFIG["agent_timeout"],
            from_agent=AgentType.POSTPROD
        )
        
        if not response or not response.content.get("success"):
            error_msg = "Failed to complete post-production" if not response else response.content.get("error", "Unknown error")
            self.logger.error(f"Post-production failed: {error_msg}")
            return None
            
        # 从响应中提取最终视频
        final_video_data = response.content.get("data", {}).get("final_video")
        if not final_video_data:
            self.logger.error("No final video data in response")
            return None
            
        # 询问用户是否接受最终视频
        user_approved = await self._ask_user_approval(
            session_id=session_id,
            stage="final_video",
            content=final_video_data,
            message="请审核并确认最终视频"
        )
        
        if not user_approved:
            self.logger.info(f"User rejected final video for session {session_id}")
            # 可以在这里实现视频重新编辑逻辑
            return None
            
        # 将最终视频数据转换为FinalVideo对象
        try:
            final_video = FinalVideo(**final_video_data)
            self.logger.info(f"Final video created and approved for session {session_id}")
            return final_video
        except Exception as e:
            self.logger.error(f"Error parsing final video data: {str(e)}")
            return None
    
    async def _distribute_video(self, session_id: str, final_video: FinalVideo) -> bool:
        """
        分发视频
        
        Args:
            session_id: 会话ID
            final_video: 最终视频
            
        Returns:
            是否成功
        """
        # 发送命令给分发代理
        command_content = {
            "action": "distribute_video",
            "parameters": {
                "video_id": final_video.id,
                "video_path": final_video.file_path,
                "title": final_video.title,
                "description": final_video.description,
                "tags": final_video.tags
            },
            "session_id": session_id
        }
        
        message_id = await self.send_message(
            to_agent=AgentType.DISTRIBUTION,
            content=command_content
        )
        
        # 等待响应
        response = await self.wait_for_response(
            message_id=message_id,
            timeout=SYSTEM_CONFIG["agent_timeout"],
            from_agent=AgentType.DISTRIBUTION
        )
        
        if not response or not response.content.get("success"):
            error_msg = "Failed to distribute video" if not response else response.content.get("error", "Unknown error")
            self.logger.error(f"Video distribution failed: {error_msg}")
            return False
            
        self.logger.info(f"Video distributed successfully for session {session_id}")
        return True
    
    async def _ask_user_approval(self, 
                                session_id: str, 
                                stage: str, 
                                content: Any, 
                                message: str) -> bool:
        """
        请求用户审批
        
        Args:
            session_id: 会话ID
            stage: 当前阶段
            content: 需要审批的内容
            message: 提示消息
            
        Returns:
            用户是否批准
        """
        # 创建等待事件
        if session_id not in self.pending_user_inputs:
            self.pending_user_inputs[session_id] = asyncio.Event()
        else:
            # 重置事件
            self.pending_user_inputs[session_id].clear()
        
        # 发送问题消息给用户
        question_content = {
            "stage": stage,
            "message": message,
            "content": content,
            "session_id": session_id,
            "options": [
                {"id": "approve", "label": "批准"},
                {"id": "reject", "label": "拒绝"}
            ]
        }
        
        await self.send_message(
            to_agent=AgentType.USER,
            content=question_content,
            message_type=MessageType.QUESTION
        )
        
        # 等待用户响应
        try:
            # 更新工作流状态
            self.active_sessions[session_id].current_stage = f"waiting_user_approval_{stage}"
            
            # 等待用户输入
            await asyncio.wait_for(
                self.pending_user_inputs[session_id].wait(),
                timeout=SYSTEM_CONFIG["agent_timeout"]
            )
            
            # 获取用户响应
            user_response = self.user_responses.get(session_id)
            if not user_response:
                self.logger.warning(f"No user response for session {session_id}")
                return False
                
            # 检查用户选择
            approved = user_response.get("choice") == "approve"
            
            # 记录用户反馈
            if "feedback" in user_response:
                self.logger.info(f"User feedback for {stage}: {user_response['feedback']}")
                
            return approved
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout waiting for user approval in session {session_id}")
            return False
    
    async def handle_command(self, message: Message) -> Optional[Message]:
        """处理命令消息"""
        action = message.content.get("action")
        
        if action == "create_session":
            # 创建新会话
            user_id = message.content.get("user_id")
            request_data = message.content.get("request")
            
            if not user_id or not request_data:
                return self.create_error_response(message, "Missing user_id or request data")
                
            try:
                request = VideoCreationRequest(**request_data)
                session_id = await self.create_session(user_id, request)
                
                return self.create_success_response(message, {
                    "session_id": session_id,
                    "message": "Session created successfully"
                })
            except Exception as e:
                return self.create_error_response(message, f"Error creating session: {str(e)}")
                
        elif action == "get_session_status":
            # 获取会话状态
            session_id = message.content.get("session_id")
            
            if not session_id or session_id not in self.active_sessions:
                return self.create_error_response(message, "Invalid or missing session_id")
                
            workflow = self.active_sessions[session_id]
            
            return self.create_success_response(message, {
                "session_id": session_id,
                "status": workflow.current_stage,
                "started_at": workflow.started_at.isoformat(),
                "updated_at": workflow.updated_at.isoformat(),
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
            })
            
        elif action == "cancel_session":
            # 取消会话
            session_id = message.content.get("session_id")
            
            if not session_id or session_id not in self.active_sessions:
                return self.create_error_response(message, "Invalid or missing session_id")
                
            # 更新状态
            self.active_sessions[session_id].current_stage = "cancelled"
            
            # 如果有等待用户输入的事件，触发它以解除阻塞
            if session_id in self.pending_user_inputs:
                self.pending_user_inputs[session_id].set()
                
            return self.create_success_response(message, {
                "message": f"Session {session_id} cancelled successfully"
            })
            
        elif action == "user_response":
            # 处理用户响应
            session_id = message.content.get("session_id")
            choice = message.content.get("choice")
            feedback = message.content.get("feedback")
            
            if not session_id or not choice or session_id not in self.active_sessions:
                return self.create_error_response(message, "Invalid user response data")
                
            # 保存用户响应
            self.user_responses[session_id] = {
                "choice": choice,
                "feedback": feedback
            }
            
            # 触发等待事件
            if session_id in self.pending_user_inputs:
                self.pending_user_inputs[session_id].set()
                
            return self.create_success_response(message, {
                "message": "User response received"
            })
            
        else:
            return self.create_error_response(message, f"Unknown action: {action}")
    
    async def handle_response(self, message: Message) -> Optional[Message]:
        """处理响应消息"""
        self.logger.debug(f"Received response from {message.sender}: {message.content.get('message', '')}")
        return None
        
    async def handle_error(self, message: Message) -> Optional[Message]:
        """处理错误消息"""
        error = message.content.get("error", "Unknown error")
        self.logger.error(f"Received error from {message.sender}: {error}")
        
        # 如果是关键代理的错误，可能需要更新会话状态
        if message.parent_id:
            # 查找相关会话
            for session_id, workflow in self.active_sessions.items():
                for msg in workflow.message_history:
                    if msg.id == message.parent_id:
                        self.logger.error(f"Error in session {session_id}: {error}")
                        workflow.current_stage = "error"
                        break
                        
        return None 