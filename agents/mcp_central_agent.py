import asyncio
import json
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.mcp import (
    MCPMessage, MCPMessageType, MCPStatus, MCPPriority, MCPCommand, MCPResponse, MCPEvent,
    create_command_message, create_event_message
)
from agents.mcp_base_agent import MCPBaseAgent
from utils.mcp_message_bus import mcp_message_bus


class MCPCentralAgent(MCPBaseAgent):
    """
    基于MCP协议的中央控制代理，负责协调其他代理的工作流程
    """
    
    def __init__(self):
        """初始化中央控制代理"""
        super().__init__(
            agent_id="central_agent",
            agent_name="Central Coordination Agent"
        )
        
        # 工作流状态管理
        self.workflows: Dict[str, Dict[str, Any]] = {}
        
        # 代理状态缓存
        self.agent_status: Dict[str, Dict[str, Any]] = {}
        
        # 订阅主题列表
        self.subscribed_topics = [
            "workflow.status",
            "agent.status",
            "user.request"
        ]
    
    async def on_start(self):
        """代理启动时的自定义逻辑"""
        # 订阅相关主题
        for topic in self.subscribed_topics:
            await mcp_message_bus.subscribe_topic(f"topic:{topic}", self._message_callback)
            
        # 订阅代理状态事件
        await mcp_message_bus.subscribe_type(MCPMessageType.EVENT, self._event_callback)
        
        self.logger.info(f"Central Agent subscribed to {len(self.subscribed_topics)} topics")
        
        # 广播中央代理已启动事件
        await self.broadcast_event(
            event_type="central.started",
            data={"timestamp": datetime.now().isoformat()}
        )
    
    async def on_stop(self):
        """代理停止时的自定义逻辑"""
        # 取消订阅相关主题
        for topic in self.subscribed_topics:
            await mcp_message_bus.unsubscribe_topic(f"topic:{topic}", self._message_callback)
            
        # 取消订阅代理状态事件
        await mcp_message_bus.unsubscribe_type(MCPMessageType.EVENT, self._event_callback)
        
        # 广播中央代理已停止事件
        await self.broadcast_event(
            event_type="central.stopping",
            data={"timestamp": datetime.now().isoformat()}
        )
    
    async def _event_callback(self, message: MCPMessage):
        """
        处理事件消息的特殊回调
        
        Args:
            message: 事件消息
        """
        if message.header.message_type != MCPMessageType.EVENT:
            return
            
        if isinstance(message.body, MCPEvent):
            event_type = message.body.event_type
            
            # 处理代理状态事件
            if event_type in ["agent.online", "agent.offline"]:
                agent_id = message.body.data.get("agent_id")
                if agent_id:
                    # 更新代理状态缓存
                    self.agent_status[agent_id] = {
                        "status": "online" if event_type == "agent.online" else "offline",
                        "last_updated": datetime.now().isoformat(),
                        "agent_name": message.body.data.get("agent_name", agent_id),
                        "version": message.body.data.get("version")
                    }
                    
                    self.logger.info(f"Agent {agent_id} is now {self.agent_status[agent_id]['status']}")
    
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
        session_id = message.header.session_id or f"session_{uuid.uuid4().hex[:8]}"
        
        try:
            if command.action == "create_video":
                # 创建视频工作流
                workflow_id = await self._start_video_creation_workflow(command.parameters, session_id)
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message="Video creation workflow started",
                    data={"workflow_id": workflow_id, "session_id": session_id}
                )
                
            elif command.action == "get_workflow_status":
                # 获取工作流状态
                workflow_id = command.parameters.get("workflow_id")
                
                if not workflow_id:
                    return message.create_error_response(
                        error_code="INVALID_PARAMETERS",
                        error_message="Missing required parameter: workflow_id"
                    )
                
                # 获取工作流状态
                workflow_status = self._get_workflow_status(workflow_id)
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message=f"Workflow status: {workflow_status.get('status', 'unknown')}",
                    data={"workflow_status": workflow_status}
                )
                
            elif command.action == "get_agent_status":
                # 获取代理状态
                agent_statuses = await self._get_all_agent_status()
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message=f"Retrieved status for {len(agent_statuses)} agents",
                    data={"agent_statuses": agent_statuses}
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
    
    async def _start_video_creation_workflow(self, parameters: Dict[str, Any], session_id: str) -> str:
        """
        启动视频创建工作流
        
        Args:
            parameters: 创建参数
            session_id: 会话ID
            
        Returns:
            工作流ID
        """
        # 生成工作流ID
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        # 创建工作流状态
        self.workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "session_id": session_id,
            "status": "started",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
            "current_stage": "script_creation",
            "stages": {
                "script_creation": {"status": "pending", "started_at": None, "completed_at": None},
                "video_generation": {"status": "pending", "started_at": None, "completed_at": None},
                "audio_generation": {"status": "pending", "started_at": None, "completed_at": None},
                "post_production": {"status": "pending", "started_at": None, "completed_at": None},
                "distribution": {"status": "pending", "started_at": None, "completed_at": None}
            },
            "parameters": parameters,
            "assets": {},
            "errors": []
        }
        
        # 发布工作流启动事件
        await self.send_event(
            target=f"topic:workflow.status",
            event_type="workflow.started",
            data={
                "workflow_id": workflow_id,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            },
            session_id=session_id
        )
        
        # 启动第一阶段 - 脚本创建
        asyncio.create_task(self._execute_script_creation_stage(workflow_id, parameters, session_id))
        
        return workflow_id
    
    async def _execute_script_creation_stage(self, workflow_id: str, parameters: Dict[str, Any], session_id: str):
        """
        执行脚本创建阶段
        
        Args:
            workflow_id: 工作流ID
            parameters: 创建参数
            session_id: 会话ID
        """
        try:
            # 更新工作流状态
            self._update_workflow_stage(workflow_id, "script_creation", "processing")
            
            # 提取脚本创建参数
            script_params = {
                "theme": parameters.get("theme", ""),
                "style": parameters.get("style", "幽默"),
                "script_type": parameters.get("script_type", "知识普及"),
                "target_audience": parameters.get("target_audience", ["年轻人", "学生"]),
                "duration": parameters.get("duration", 60.0),
                "language": parameters.get("language", "zh"),
                "keywords": parameters.get("keywords", []),
                "special_requirements": parameters.get("special_requirements", "")
            }
            
            # 发送命令给内容代理
            self.logger.info(f"Sending create_script command to content_agent for workflow {workflow_id}")
            
            response = await self.send_command(
                target="content_agent",
                action="create_script",
                parameters=script_params,
                session_id=session_id,
                wait_for_response=True,
                response_timeout=120.0  # 脚本创建可能需要较长时间
            )
            
            if not response or response.header.message_type == MCPMessageType.ERROR:
                error_msg = "Failed to create script"
                if response and isinstance(response.body, MCPError):
                    error_msg = f"{error_msg}: {response.body.error_message}"
                
                self._update_workflow_stage(workflow_id, "script_creation", "failed", error=error_msg)
                self._update_workflow_status(workflow_id, "failed", error=error_msg)
                return
            
            # 解析响应
            if isinstance(response.body, MCPResponse) and response.body.success:
                script = response.body.data.get("script")
                
                if script:
                    # 保存脚本到工作流资产
                    self.workflows[workflow_id]["assets"]["script"] = script
                    
                    # 更新工作流状态
                    self._update_workflow_stage(workflow_id, "script_creation", "completed")
                    
                    # 继续下一阶段 - 视频生成
                    asyncio.create_task(self._execute_video_generation_stage(workflow_id, script, parameters, session_id))
                else:
                    self._update_workflow_stage(workflow_id, "script_creation", "failed", error="Script data missing in response")
                    self._update_workflow_status(workflow_id, "failed", error="Script data missing in response")
            else:
                self._update_workflow_stage(workflow_id, "script_creation", "failed", error="Invalid response from content agent")
                self._update_workflow_status(workflow_id, "failed", error="Invalid response from content agent")
                
        except Exception as e:
            error_msg = f"Error in script creation stage: {str(e)}"
            self.logger.error(error_msg)
            self._update_workflow_stage(workflow_id, "script_creation", "failed", error=error_msg)
            self._update_workflow_status(workflow_id, "failed", error=error_msg)
    
    async def _execute_video_generation_stage(self, workflow_id: str, script: Dict[str, Any], parameters: Dict[str, Any], session_id: str):
        """
        执行视频生成阶段
        
        Args:
            workflow_id: 工作流ID
            script: 脚本数据
            parameters: 创建参数
            session_id: 会话ID
        """
        try:
            # 更新工作流状态
            self._update_workflow_stage(workflow_id, "video_generation", "processing")
            
            # 提取视频生成参数
            video_params = {
                "script_sections": script.get("sections", []),
                "video_model": parameters.get("video_model", "wan"),
                "resolution": parameters.get("resolution", "1080x1920"),
                "style": parameters.get("style", "realistic")
            }
            
            # 发送命令给视觉代理
            self.logger.info(f"Sending generate_videos command to visual_agent for workflow {workflow_id}")
            
            response = await self.send_command(
                target="visual_agent",
                action="generate_videos",
                parameters=video_params,
                session_id=session_id,
                wait_for_response=True,
                response_timeout=300.0  # 视频生成可能需要较长时间
            )
            
            if not response or response.header.message_type == MCPMessageType.ERROR:
                error_msg = "Failed to generate videos"
                if response and isinstance(response.body, MCPError):
                    error_msg = f"{error_msg}: {response.body.error_message}"
                
                self._update_workflow_stage(workflow_id, "video_generation", "failed", error=error_msg)
                self._update_workflow_status(workflow_id, "failed", error=error_msg)
                return
            
            # 解析响应
            if isinstance(response.body, MCPResponse) and response.body.success:
                video_assets = response.body.data.get("video_assets", [])
                
                if video_assets:
                    # 保存视频资产到工作流
                    self.workflows[workflow_id]["assets"]["videos"] = video_assets
                    
                    # 更新工作流状态
                    self._update_workflow_stage(workflow_id, "video_generation", "completed")
                    
                    # 继续下一阶段 - 音频生成
                    # 这里可以添加音频生成阶段的代码
                    # asyncio.create_task(self._execute_audio_generation_stage(workflow_id, script, video_assets, parameters, session_id))
                    
                    # 临时：直接标记工作流为完成
                    self._update_workflow_status(workflow_id, "completed")
                else:
                    self._update_workflow_stage(workflow_id, "video_generation", "failed", error="No video assets generated")
                    self._update_workflow_status(workflow_id, "failed", error="No video assets generated")
            else:
                self._update_workflow_stage(workflow_id, "video_generation", "failed", error="Invalid response from visual agent")
                self._update_workflow_status(workflow_id, "failed", error="Invalid response from visual agent")
                
        except Exception as e:
            error_msg = f"Error in video generation stage: {str(e)}"
            self.logger.error(error_msg)
            self._update_workflow_stage(workflow_id, "video_generation", "failed", error=error_msg)
            self._update_workflow_status(workflow_id, "failed", error=error_msg)
    
    def _update_workflow_stage(self, workflow_id: str, stage: str, status: str, error: Optional[str] = None):
        """
        更新工作流阶段状态
        
        Args:
            workflow_id: 工作流ID
            stage: 阶段名称
            status: 状态
            error: 错误信息
        """
        if workflow_id not in self.workflows:
            return
            
        workflow = self.workflows[workflow_id]
        
        if stage not in workflow["stages"]:
            return
            
        # 更新阶段状态
        workflow["stages"][stage]["status"] = status
        workflow["updated_at"] = datetime.now().isoformat()
        
        # 设置开始或完成时间
        if status == "processing" and not workflow["stages"][stage].get("started_at"):
            workflow["stages"][stage]["started_at"] = datetime.now().isoformat()
        elif status in ["completed", "failed"] and not workflow["stages"][stage].get("completed_at"):
            workflow["stages"][stage]["completed_at"] = datetime.now().isoformat()
        
        # 记录错误
        if error:
            workflow["stages"][stage]["error"] = error
            workflow["errors"].append({
                "stage": stage,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            
        # 更新当前阶段
        if status == "completed":
            # 查找下一个待处理阶段
            stages = list(workflow["stages"].keys())
            current_index = stages.index(stage)
            
            if current_index < len(stages) - 1:
                workflow["current_stage"] = stages[current_index + 1]
    
    def _update_workflow_status(self, workflow_id: str, status: str, error: Optional[str] = None):
        """
        更新工作流整体状态
        
        Args:
            workflow_id: 工作流ID
            status: 状态
            error: 错误信息
        """
        if workflow_id not in self.workflows:
            return
            
        workflow = self.workflows[workflow_id]
        
        # 更新状态
        workflow["status"] = status
        workflow["updated_at"] = datetime.now().isoformat()
        
        # 设置完成时间
        if status in ["completed", "failed"] and not workflow.get("completed_at"):
            workflow["completed_at"] = datetime.now().isoformat()
        
        # 记录错误
        if error and error not in [e["error"] for e in workflow["errors"]]:
            workflow["errors"].append({
                "stage": "workflow",
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            
        # 发布工作流状态更新事件
        asyncio.create_task(self.send_event(
            target=f"topic:workflow.status",
            event_type=f"workflow.{status}",
            data={
                "workflow_id": workflow_id,
                "session_id": workflow["session_id"],
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "error": error
            },
            session_id=workflow["session_id"]
        ))
    
    def _get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        获取工作流状态
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            工作流状态信息
        """
        if workflow_id not in self.workflows:
            return {"status": "not_found", "workflow_id": workflow_id}
            
        workflow = self.workflows[workflow_id]
        
        # 返回状态摘要
        return {
            "workflow_id": workflow_id,
            "session_id": workflow["session_id"],
            "status": workflow["status"],
            "current_stage": workflow["current_stage"],
            "created_at": workflow["created_at"],
            "updated_at": workflow["updated_at"],
            "completed_at": workflow["completed_at"],
            "stages": {
                stage: {
                    "status": info["status"],
                    "started_at": info.get("started_at"),
                    "completed_at": info.get("completed_at")
                } for stage, info in workflow["stages"].items()
            },
            "errors": workflow["errors"],
            "has_assets": {
                "script": "script" in workflow["assets"],
                "videos": "videos" in workflow["assets"] and len(workflow["assets"].get("videos", [])) > 0,
                "audios": "audios" in workflow["assets"] and len(workflow["assets"].get("audios", [])) > 0,
                "final_video": "final_video" in workflow["assets"]
            }
        }
    
    async def _get_all_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有代理的状态
        
        Returns:
            代理状态信息
        """
        # 从消息总线获取最新状态
        bus_status = mcp_message_bus.get_agent_status()
        
        # 合并本地缓存和总线状态
        merged_status = {}
        
        # 添加本地缓存中的代理
        for agent_id, status in self.agent_status.items():
            merged_status[agent_id] = status
        
        # 添加或更新总线状态中的代理
        for agent_id, status in bus_status.items():
            if agent_id not in merged_status:
                merged_status[agent_id] = {}
                
            merged_status[agent_id].update({
                "status": status.get("status", "unknown"),
                "last_seen": status.get("last_seen"),
                "load": status.get("load"),
                "uptime_seconds": status.get("uptime_seconds"),
                "version": status.get("version")
            })
        
        return merged_status 