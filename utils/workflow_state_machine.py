import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Callable, Awaitable, Set, Tuple
from enum import Enum
from datetime import datetime
import uuid

from models.mcp import (
    MCPMessage, MCPMessageType, MCPStatus, MCPPriority,
    create_command_message, create_event_message
)
from utils.mcp_message_bus import mcp_message_bus


class WorkflowTransitionResult:
    """工作流状态转换结果"""
    
    def __init__(self, success: bool, next_state: Optional[str] = None, error: Optional[str] = None):
        self.success = success
        self.next_state = next_state
        self.error = error
        self.timestamp = datetime.now()


class WorkflowState:
    """工作流状态基类"""
    
    def __init__(self, name: str, workflow: 'Workflow'):
        self.name = name
        self.workflow = workflow
        self.logger = logging.getLogger(f"Workflow:{workflow.workflow_id}:State:{name}")
        self.entry_time: Optional[datetime] = None
        self.exit_time: Optional[datetime] = None
        self.retry_count = 0
        self.max_retries = 3
        self.metadata: Dict[str, Any] = {}
    
    async def on_enter(self, data: Dict[str, Any]) -> None:
        """
        进入状态时的处理
        
        Args:
            data: 状态数据
        """
        self.entry_time = datetime.now()
        self.logger.info(f"Entering state {self.name}")
    
    async def on_exit(self, data: Dict[str, Any]) -> None:
        """
        退出状态时的处理
        
        Args:
            data: 状态数据
        """
        self.exit_time = datetime.now()
        self.logger.info(f"Exiting state {self.name}")
    
    async def process(self, data: Dict[str, Any]) -> WorkflowTransitionResult:
        """
        处理当前状态
        
        Args:
            data: 状态数据
            
        Returns:
            状态转换结果
        """
        # 子类应该覆盖此方法
        return WorkflowTransitionResult(True, None)
    
    async def handle_error(self, error: str, data: Dict[str, Any]) -> WorkflowTransitionResult:
        """
        处理错误
        
        Args:
            error: 错误信息
            data: 状态数据
            
        Returns:
            状态转换结果
        """
        self.retry_count += 1
        
        if self.retry_count <= self.max_retries:
            self.logger.warning(f"Error in state {self.name}: {error}. Retrying ({self.retry_count}/{self.max_retries})")
            # 重试当前状态
            return WorkflowTransitionResult(True, self.name)
        else:
            self.logger.error(f"Error in state {self.name}: {error}. Max retries exceeded.")
            # 转移到错误状态
            return WorkflowTransitionResult(False, "error", error)
    
    async def can_transition_to(self, next_state: str, data: Dict[str, Any]) -> bool:
        """
        检查是否可以转换到下一个状态
        
        Args:
            next_state: 下一个状态名称
            data: 状态数据
            
        Returns:
            是否可以转换
        """
        # 默认允许所有转换，子类可以覆盖此方法添加限制
        return True


class Workflow:
    """工作流管理器"""
    
    def __init__(self, workflow_id: str, name: str, agent_id: str):
        """
        初始化工作流
        
        Args:
            workflow_id: 工作流唯一标识符
            name: 工作流名称
            agent_id: 所属代理ID
        """
        self.workflow_id = workflow_id
        self.name = name
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"Workflow:{workflow_id}")
        
        # 状态定义
        self.states: Dict[str, WorkflowState] = {}
        
        # 当前状态
        self.current_state: Optional[str] = None
        
        # 工作流数据
        self.data: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "name": name,
            "agent_id": agent_id,
            "start_time": None,
            "end_time": None,
            "status": "initialized",
            "history": [],
            "checkpoints": {},
            "errors": []
        }
        
        # 工作流锁，防止并发执行
        self.lock = asyncio.Lock()
        
        # 添加默认错误状态
        self.add_state("error", ErrorState(self))
    
    def add_state(self, name: str, state: WorkflowState) -> 'Workflow':
        """
        添加状态
        
        Args:
            name: 状态名称
            state: 状态对象
            
        Returns:
            工作流实例（用于链式调用）
        """
        self.states[name] = state
        return self
    
    async def start(self, initial_state: str, initial_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        启动工作流
        
        Args:
            initial_state: 初始状态
            initial_data: 初始数据
            
        Returns:
            是否成功启动
        """
        async with self.lock:
            if self.current_state is not None:
                self.logger.warning(f"Workflow {self.workflow_id} already started")
                return False
            
            if initial_state not in self.states:
                self.logger.error(f"Invalid initial state: {initial_state}")
                return False
            
            # 设置初始数据
            if initial_data:
                self.data.update(initial_data)
            
            # 设置开始时间和状态
            self.data["start_time"] = datetime.now().isoformat()
            self.data["status"] = "running"
            
            # 设置初始状态
            self.current_state = initial_state
            
            # 记录状态转换历史
            self._record_transition(None, initial_state, "workflow_started")
            
            # 进入初始状态
            await self.states[initial_state].on_enter(self.data)
            
            # 发布工作流启动事件
            await self._publish_workflow_event("workflow.started", {
                "workflow_id": self.workflow_id,
                "name": self.name,
                "initial_state": initial_state
            })
            
            # 开始处理
            asyncio.create_task(self._process_current_state())
            
            return True
    
    async def transition(self, next_state: str, reason: str = "manual_transition") -> bool:
        """
        手动触发状态转换
        
        Args:
            next_state: 下一个状态
            reason: 转换原因
            
        Returns:
            是否成功转换
        """
        async with self.lock:
            if self.current_state is None:
                self.logger.error("Cannot transition: workflow not started")
                return False
            
            if next_state not in self.states:
                self.logger.error(f"Invalid next state: {next_state}")
                return False
            
            # 检查是否允许转换
            current_state_obj = self.states[self.current_state]
            if not await current_state_obj.can_transition_to(next_state, self.data):
                self.logger.warning(f"Transition from {self.current_state} to {next_state} not allowed")
                return False
            
            # 退出当前状态
            await current_state_obj.on_exit(self.data)
            
            # 记录状态转换
            old_state = self.current_state
            self.current_state = next_state
            self._record_transition(old_state, next_state, reason)
            
            # 进入新状态
            await self.states[next_state].on_enter(self.data)
            
            # 发布状态转换事件
            await self._publish_workflow_event("workflow.state_changed", {
                "workflow_id": self.workflow_id,
                "from_state": old_state,
                "to_state": next_state,
                "reason": reason
            })
            
            # 开始处理新状态
            asyncio.create_task(self._process_current_state())
            
            return True
    
    async def _process_current_state(self) -> None:
        """处理当前状态"""
        if self.current_state is None or self.data["status"] != "running":
            return
        
        try:
            # 获取当前状态对象
            state = self.states[self.current_state]
            
            # 处理当前状态
            result = await state.process(self.data)
            
            if result.success:
                if result.next_state:
                    # 状态需要转换
                    if result.next_state != self.current_state:
                        await self.transition(result.next_state, "state_processing_complete")
                else:
                    # 状态处理完成，但不需要转换
                    self.logger.debug(f"State {self.current_state} processed successfully, waiting for external transition")
            else:
                # 处理失败
                error_msg = result.error or "Unknown error"
                self.logger.error(f"Error processing state {self.current_state}: {error_msg}")
                
                # 调用错误处理
                error_result = await state.handle_error(error_msg, self.data)
                
                if error_result.success and error_result.next_state:
                    # 错误处理成功，转换到指定状态
                    await self.transition(error_result.next_state, f"error_recovery: {error_msg}")
                else:
                    # 错误处理失败，记录错误并停止工作流
                    self.data["errors"].append({
                        "state": self.current_state,
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat()
                    })
                    await self.stop(f"error: {error_msg}")
        
        except Exception as e:
            # 捕获未处理的异常
            error_msg = str(e)
            self.logger.exception(f"Unhandled exception in state {self.current_state}: {error_msg}")
            
            # 记录错误
            self.data["errors"].append({
                "state": self.current_state,
                "error": error_msg,
                "timestamp": datetime.now().isoformat(),
                "exception": True
            })
            
            # 停止工作流
            await self.stop(f"exception: {error_msg}")
    
    async def stop(self, reason: str = "manual_stop") -> None:
        """
        停止工作流
        
        Args:
            reason: 停止原因
        """
        async with self.lock:
            if self.current_state is None or self.data["status"] == "completed":
                return
            
            # 如果当前有状态，退出该状态
            if self.current_state and self.current_state in self.states:
                await self.states[self.current_state].on_exit(self.data)
            
            # 更新工作流状态
            self.data["status"] = "completed"
            self.data["end_time"] = datetime.now().isoformat()
            
            # 记录停止原因
            self._record_transition(self.current_state, None, reason)
            self.current_state = None
            
            # 发布工作流停止事件
            await self._publish_workflow_event("workflow.stopped", {
                "workflow_id": self.workflow_id,
                "reason": reason
            })
    
    def create_checkpoint(self, checkpoint_id: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        创建检查点
        
        Args:
            checkpoint_id: 检查点ID
            data: 检查点数据
        """
        checkpoint_data = data or {}
        checkpoint_data.update({
            "state": self.current_state,
            "timestamp": datetime.now().isoformat()
        })
        
        self.data["checkpoints"][checkpoint_id] = checkpoint_data
        self.logger.info(f"Created checkpoint {checkpoint_id} at state {self.current_state}")
    
    async def restore_from_checkpoint(self, checkpoint_id: str) -> bool:
        """
        从检查点恢复
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否成功恢复
        """
        if checkpoint_id not in self.data["checkpoints"]:
            self.logger.error(f"Checkpoint {checkpoint_id} not found")
            return False
        
        checkpoint = self.data["checkpoints"][checkpoint_id]
        target_state = checkpoint["state"]
        
        if target_state not in self.states:
            self.logger.error(f"Invalid checkpoint state: {target_state}")
            return False
        
        # 转换到检查点状态
        success = await self.transition(target_state, f"restore_from_checkpoint:{checkpoint_id}")
        
        if success:
            self.logger.info(f"Restored workflow from checkpoint {checkpoint_id} to state {target_state}")
            
            # 发布检查点恢复事件
            await self._publish_workflow_event("workflow.checkpoint_restored", {
                "workflow_id": self.workflow_id,
                "checkpoint_id": checkpoint_id,
                "state": target_state
            })
        
        return success
    
    def _record_transition(self, from_state: Optional[str], to_state: Optional[str], reason: str) -> None:
        """
        记录状态转换历史
        
        Args:
            from_state: 源状态
            to_state: 目标状态
            reason: 转换原因
        """
        self.data["history"].append({
            "from_state": from_state,
            "to_state": to_state,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        })
    
    async def _publish_workflow_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        发布工作流事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        event_data = {**data, "timestamp": datetime.now().isoformat()}
        
        # 创建并发布事件消息
        event_msg = create_event_message(
            source=self.agent_id,
            target="topic:workflow",
            event_type=event_type,
            data=event_data
        )
        
        await mcp_message_bus.publish(event_msg)


class ErrorState(WorkflowState):
    """错误状态"""
    
    async def on_enter(self, data: Dict[str, Any]) -> None:
        """进入错误状态"""
        await super().on_enter(data)
        
        # 记录错误信息
        if "transition_error" in data:
            self.logger.error(f"Workflow entered error state: {data['transition_error']}")
        
        # 发布错误事件
        event_msg = create_event_message(
            source=self.workflow.agent_id,
            target="topic:workflow.error",
            event_type="workflow.error",
            data={
                "workflow_id": self.workflow.workflow_id,
                "error": data.get("transition_error", "Unknown error"),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        await mcp_message_bus.publish(event_msg)
    
    async def process(self, data: Dict[str, Any]) -> WorkflowTransitionResult:
        """处理错误状态"""
        # 错误状态不做任何处理，等待外部干预
        return WorkflowTransitionResult(True, None)


class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.logger = logging.getLogger("WorkflowManager")
    
    def create_workflow(self, name: str, agent_id: str) -> Workflow:
        """
        创建新工作流
        
        Args:
            name: 工作流名称
            agent_id: 所属代理ID
            
        Returns:
            工作流实例
        """
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
        workflow = Workflow(workflow_id, name, agent_id)
        self.workflows[workflow_id] = workflow
        
        self.logger.info(f"Created workflow {name} ({workflow_id}) for agent {agent_id}")
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        获取工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            工作流实例，如果不存在则返回None
        """
        return self.workflows.get(workflow_id)
    
    def list_workflows(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出工作流
        
        Args:
            agent_id: 可选的代理ID过滤
            
        Returns:
            工作流信息列表
        """
        result = []
        
        for workflow in self.workflows.values():
            if agent_id is None or workflow.agent_id == agent_id:
                result.append({
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "agent_id": workflow.agent_id,
                    "current_state": workflow.current_state,
                    "status": workflow.data["status"],
                    "start_time": workflow.data["start_time"],
                    "end_time": workflow.data["end_time"]
                })
        
        return result


# 创建全局工作流管理器实例
workflow_manager = WorkflowManager() 