"""
中央策略代理
负责协调整个视频生成工作流，管理其他代理的任务分配
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from agents.mcp_base_agent import MCPBaseAgent
from models.mcp import (MCPCommand, MCPMessage, MCPMessageType, MCPPriority,
                        MCPResponse, MCPStatus)
from utils.mcp_message_bus import message_bus


class WorkflowStage(str, Enum):
    """工作流阶段"""
    SCRIPT_CREATION = "script_creation"
    VIDEO_GENERATION = "video_generation"
    AUDIO_GENERATION = "audio_generation"
    POST_PRODUCTION = "post_production"
    DISTRIBUTION = "distribution"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStatus(str, Enum):
    """工作流状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    WAITING_USER_INPUT = "waiting_user_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StageInfo:
    """阶段信息"""
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowContext:
    """工作流上下文"""
    workflow_id: str
    session_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_stage: WorkflowStage = WorkflowStage.SCRIPT_CREATION
    stages: Dict[str, StageInfo] = field(default_factory=dict)
    user_request: Dict[str, Any] = field(default_factory=dict)
    script_data: Optional[Dict[str, Any]] = None
    video_data: Optional[Dict[str, Any]] = None
    audio_data: Optional[Dict[str, Any]] = None
    final_video: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        # 初始化所有阶段
        for stage in WorkflowStage:
            if stage.value not in self.stages and stage not in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                self.stages[stage.value] = StageInfo()
    
    def update_stage(self, stage: str, **kwargs):
        """更新阶段状态"""
        if stage in self.stages:
            for key, value in kwargs.items():
                setattr(self.stages[stage], key, value)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "workflow_id": self.workflow_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "current_stage": self.current_stage.value,
            "stages": {
                stage: {
                    "status": info.status,
                    "started_at": info.started_at.isoformat() if info.started_at else None,
                    "completed_at": info.completed_at.isoformat() if info.completed_at else None,
                    "error": info.error,
                }
                for stage, info in self.stages.items()
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class CentralAgent(MCPBaseAgent):
    """
    中央策略代理
    
    职责：
    1. 接收用户请求并创建工作流
    2. 协调各阶段代理的工作
    3. 管理工作流状态和进度
    4. 处理用户干预请求
    5. 错误处理和重试机制
    """
    
    def __init__(self):
        super().__init__(agent_id="central_agent", agent_name="中央策略代理")
        
        # 工作流存储
        self._workflows: Dict[str, WorkflowContext] = {}
        
        # 代理映射（阶段 -> 代理ID）
        self._stage_agents = {
            WorkflowStage.SCRIPT_CREATION: "content_agent",
            WorkflowStage.VIDEO_GENERATION: "visual_agent",
            WorkflowStage.AUDIO_GENERATION: "audio_agent",
            WorkflowStage.POST_PRODUCTION: "postprod_agent",
            WorkflowStage.DISTRIBUTION: "distribution_agent",
        }
        
        # 命令处理器映射
        self._command_handlers = {
            "create_video": self._handle_create_video,
            "get_workflow_status": self._handle_get_workflow_status,
            "cancel_workflow": self._handle_cancel_workflow,
            "user_selection": self._handle_user_selection,
            "retry_stage": self._handle_retry_stage,
            "list_workflows": self._handle_list_workflows,
        }
        
        # 进度回调
        self._progress_callbacks: Dict[str, List[Callable]] = {}
    
    async def handle_command(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理命令消息"""
        if not isinstance(message.body, MCPCommand):
            return message.create_error_response(
                error_code="INVALID_MESSAGE",
                error_message="预期收到命令消息"
            )
        
        command = message.body
        action = command.action
        
        self.logger.info(f"收到命令: {action}")
        
        # 查找处理器
        handler = self._command_handlers.get(action)
        if not handler:
            return message.create_error_response(
                error_code="UNKNOWN_COMMAND",
                error_message=f"未知命令: {action}"
            )
        
        try:
            # 执行处理器
            result = await handler(command.parameters, message.header.session_id)
            
            return message.create_response(
                success=True,
                message=f"命令 {action} 执行成功",
                data=result
            )
        except Exception as e:
            self.logger.error(f"执行命令 {action} 时发生错误: {str(e)}", exc_info=True)
            return message.create_error_response(
                error_code="EXECUTION_ERROR",
                error_message=f"执行命令时发生错误: {str(e)}"
            )
    
    async def _handle_create_video(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """处理创建视频请求"""
        # 验证必要参数
        theme = parameters.get("theme")
        if not theme:
            raise ValueError("缺少必要参数: theme")
        
        # 创建工作流
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
        workflow = WorkflowContext(
            workflow_id=workflow_id,
            session_id=session_id,
            user_request=parameters
        )
        
        self._workflows[workflow_id] = workflow
        
        self.logger.info(f"创建工作流: {workflow_id}, 主题: {theme}")
        
        # 异步执行工作流
        asyncio.create_task(self._execute_workflow(workflow_id))
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "message": "工作流已创建，正在处理中"
        }
    
    async def _execute_workflow(self, workflow_id: str):
        """执行工作流"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            self.logger.error(f"工作流 {workflow_id} 不存在")
            return
        
        workflow.status = WorkflowStatus.PROCESSING
        
        try:
            # 阶段1: 脚本创作
            await self._execute_stage(
                workflow,
                WorkflowStage.SCRIPT_CREATION,
                "create_script",
                {
                    "theme": workflow.user_request.get("theme"),
                    "style": workflow.user_request.get("style", "幽默"),
                    "duration": workflow.user_request.get("duration", 60),
                    "target_audience": workflow.user_request.get("target_audience", "年轻人"),
                }
            )
            
            if workflow.status == WorkflowStatus.FAILED:
                return
            
            # 阶段2: 视频生成
            # 从脚本数据中提取实际脚本内容
            script_content = workflow.script_data.get("script") if workflow.script_data else None
            await self._execute_stage(
                workflow,
                WorkflowStage.VIDEO_GENERATION,
                "generate_video",
                {
                    "script": script_content,
                    "style": workflow.user_request.get("video_style", "realistic"),
                    "aspect_ratio": workflow.user_request.get("aspect_ratio", "9:16"),
                    "quality": workflow.user_request.get("quality", "high"),
                }
            )
            
            if workflow.status == WorkflowStatus.FAILED:
                return
            
            # 阶段3: 音频生成
            script_content = workflow.script_data.get("script") if workflow.script_data else None
            await self._execute_stage(
                workflow,
                WorkflowStage.AUDIO_GENERATION,
                "generate_audio",
                {
                    "script": script_content,
                    "voice_style": workflow.user_request.get("voice_style", "natural"),
                    "music_style": workflow.user_request.get("music_style", "upbeat"),
                    "duration": workflow.user_request.get("duration", 60),
                }
            )
            
            if workflow.status == WorkflowStatus.FAILED:
                return
            
            # 阶段4: 后期制作
            script_content = workflow.script_data.get("script") if workflow.script_data else None
            await self._execute_stage(
                workflow,
                WorkflowStage.POST_PRODUCTION,
                "post_produce",
                {
                    "video": workflow.video_data,
                    "audio": workflow.audio_data,
                    "script": script_content,
                    "effects": workflow.user_request.get("effects", ["color_grade", "transitions"]),
                    "subtitles": workflow.user_request.get("subtitles", True),
                }
            )
            
            if workflow.status == WorkflowStatus.FAILED:
                return
            
            # 阶段5: 分发（可选）
            if workflow.user_request.get("auto_distribute", False):
                await self._execute_stage(
                    workflow,
                    WorkflowStage.DISTRIBUTION,
                    "distribute_video",
                    {
                        "video": workflow.final_video,
                        "platforms": workflow.user_request.get("platforms", ["tiktok"]),
                        "schedule": workflow.user_request.get("schedule"),
                    }
                )
            else:
                workflow.update_stage(
                    WorkflowStage.DISTRIBUTION.value,
                    status="skipped"
                )
            
            # 工作流完成
            workflow.status = WorkflowStatus.COMPLETED
            workflow.current_stage = WorkflowStage.COMPLETED
            
            self.logger.info(f"工作流 {workflow_id} 完成")
            
            # 广播完成事件
            await self.broadcast_event(
                event_type="workflow.completed",
                data=workflow.to_dict(),
                session_id=workflow.session_id
            )
            
        except Exception as e:
            self.logger.error(f"工作流 {workflow_id} 执行失败: {str(e)}", exc_info=True)
            workflow.status = WorkflowStatus.FAILED
            workflow.update_stage(
                workflow.current_stage.value,
                status="failed",
                error=str(e)
            )
            
            # 广播失败事件
            await self.broadcast_event(
                event_type="workflow.failed",
                data={
                    "workflow_id": workflow_id,
                    "error": str(e),
                    "stage": workflow.current_stage.value
                },
                session_id=workflow.session_id
            )
    
    async def _execute_stage(
        self,
        workflow: WorkflowContext,
        stage: WorkflowStage,
        action: str,
        parameters: Dict[str, Any]
    ):
        """执行工作流阶段"""
        workflow.current_stage = stage
        workflow.update_stage(
            stage.value,
            status="processing",
            started_at=datetime.now()
        )
        
        target_agent = self._stage_agents.get(stage)
        if not target_agent:
            raise ValueError(f"未找到阶段 {stage} 对应的代理")
        
        self.logger.info(f"执行阶段 {stage.value}: {action} -> {target_agent}")
        
        # 广播阶段开始事件
        await self.broadcast_event(
            event_type="workflow.stage_started",
            data={
                "workflow_id": workflow.workflow_id,
                "stage": stage.value,
                "action": action
            },
            session_id=workflow.session_id
        )
        
        try:
            # 发送命令到目标代理
            response = await self.send_command(
                target=target_agent,
                action=action,
                parameters=parameters,
                session_id=workflow.session_id,
                priority=MCPPriority.NORMAL,
                timeout_seconds=300,  # 5分钟超时
                wait_for_response=True,
                response_timeout=300.0
            )
            
            if response is None:
                raise TimeoutError(f"等待 {target_agent} 响应超时")
            
            # 检查响应
            if isinstance(response.body, MCPResponse):
                if response.body.success:
                    # 阶段成功
                    result = response.body.data
                    workflow.update_stage(
                        stage.value,
                        status="completed",
                        completed_at=datetime.now(),
                        result=result
                    )
                    
                    # 保存阶段结果
                    self._save_stage_result(workflow, stage, result)
                    
                    self.logger.info(f"阶段 {stage.value} 完成")
                    
                    # 广播阶段完成事件
                    await self.broadcast_event(
                        event_type="workflow.stage_completed",
                        data={
                            "workflow_id": workflow.workflow_id,
                            "stage": stage.value,
                            "result": result
                        },
                        session_id=workflow.session_id
                    )
                else:
                    raise Exception(response.body.message)
            else:
                raise Exception("收到非预期的响应类型")
                
        except Exception as e:
            self.logger.error(f"阶段 {stage.value} 失败: {str(e)}")
            workflow.update_stage(
                stage.value,
                status="failed",
                error=str(e)
            )
            workflow.status = WorkflowStatus.FAILED
            
            # 广播阶段失败事件
            await self.broadcast_event(
                event_type="workflow.stage_failed",
                data={
                    "workflow_id": workflow.workflow_id,
                    "stage": stage.value,
                    "error": str(e)
                },
                session_id=workflow.session_id
            )
            
            raise
    
    def _save_stage_result(
        self,
        workflow: WorkflowContext,
        stage: WorkflowStage,
        result: Dict[str, Any]
    ):
        """保存阶段结果"""
        if stage == WorkflowStage.SCRIPT_CREATION:
            workflow.script_data = result
        elif stage == WorkflowStage.VIDEO_GENERATION:
            workflow.video_data = result
        elif stage == WorkflowStage.AUDIO_GENERATION:
            workflow.audio_data = result
        elif stage == WorkflowStage.POST_PRODUCTION:
            workflow.final_video = result
    
    async def _handle_get_workflow_status(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """获取工作流状态"""
        workflow_id = parameters.get("workflow_id")
        if not workflow_id:
            raise ValueError("缺少参数: workflow_id")
        
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        return workflow.to_dict()
    
    async def _handle_cancel_workflow(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """取消工作流"""
        workflow_id = parameters.get("workflow_id")
        if not workflow_id:
            raise ValueError("缺少参数: workflow_id")
        
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        workflow.status = WorkflowStatus.CANCELLED
        
        self.logger.info(f"工作流 {workflow_id} 已取消")
        
        return {
            "workflow_id": workflow_id,
            "status": "cancelled"
        }
    
    async def _handle_user_selection(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """处理用户选择（用于用户干预场景）"""
        workflow_id = parameters.get("workflow_id")
        selection_type = parameters.get("selection_type")
        selection_value = parameters.get("selection_value")
        
        if not all([workflow_id, selection_type, selection_value]):
            raise ValueError("缺少必要参数")
        
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        # 处理用户选择
        workflow.user_request[selection_type] = selection_value
        
        # 如果工作流处于等待用户输入状态，继续执行
        if workflow.status == WorkflowStatus.WAITING_USER_INPUT:
            workflow.status = WorkflowStatus.PROCESSING
            asyncio.create_task(self._execute_workflow(workflow_id))
        
        return {
            "workflow_id": workflow_id,
            "selection_type": selection_type,
            "selection_value": selection_value
        }
    
    async def _handle_retry_stage(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """重试失败的阶段"""
        workflow_id = parameters.get("workflow_id")
        stage = parameters.get("stage")
        
        if not workflow_id:
            raise ValueError("缺少参数: workflow_id")
        
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        if workflow.status != WorkflowStatus.FAILED:
            raise ValueError("只能重试失败的工作流")
        
        # 重置状态
        workflow.status = WorkflowStatus.PROCESSING
        
        # 从失败的阶段继续执行
        asyncio.create_task(self._execute_workflow(workflow_id))
        
        return {
            "workflow_id": workflow_id,
            "status": "retrying"
        }
    
    async def _handle_list_workflows(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """列出所有工作流"""
        status_filter = parameters.get("status")
        limit = parameters.get("limit", 10)
        
        workflows = []
        for wf_id, workflow in self._workflows.items():
            if status_filter and workflow.status.value != status_filter:
                continue
            workflows.append(workflow.to_dict())
        
        # 按创建时间排序
        workflows.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "workflows": workflows[:limit],
            "total": len(workflows)
        }
    
    async def handle_event(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理事件消息"""
        event_type = message.body.event_type
        data = message.body.data
        
        self.logger.debug(f"收到事件: {event_type}")
        
        # 处理代理状态事件
        if event_type == "agent.offline":
            agent_id = data.get("agent_id")
            self.logger.warning(f"代理 {agent_id} 离线")
            # 可以在这里处理代理离线的情况，如重新分配任务
        
        return None
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowContext]:
        """获取工作流"""
        return self._workflows.get(workflow_id)
    
    def get_all_workflows(self) -> List[WorkflowContext]:
        """获取所有工作流"""
        return list(self._workflows.values())
