import asyncio
import uuid
import logging
import time
import random
from typing import Dict, List, Any, Optional, Callable, Awaitable, Set
from abc import ABC, abstractmethod
from datetime import datetime

from models.mcp import (
    MCPMessage, MCPMessageType, MCPStatus, MCPPriority, MCPContentFormat,
    MCPCommand, MCPResponse, MCPError, MCPEvent, MCPHeartbeat,
    create_command_message, create_event_message, create_heartbeat_message
)
from utils.mcp_message_bus import mcp_message_bus
from utils.workflow_state_machine import workflow_manager, Workflow, WorkflowState


class MCPBaseAgent(ABC):
    """
    基于MCP协议的代理基类，提供订阅、发布和处理MCP消息的能力
    """
    
    def __init__(self, agent_id: str, agent_name: str):
        """
        初始化MCP代理
        
        Args:
            agent_id: 代理唯一标识符
            agent_name: 代理友好名称
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"MCPAgent:{agent_id}")
        
        # 消息处理器映射
        self.message_handlers: Dict[MCPMessageType, Callable[[MCPMessage], Awaitable[Optional[MCPMessage]]]] = {}
        
        # 代理状态
        self.is_initialized = False
        self.is_running = False
        self.start_time = None
        self.version = "1.0.0"
        
        # 心跳任务
        self._heartbeat_task = None
        self._heartbeat_interval = 30  # 30秒发送一次心跳
        
        # 等待中的响应
        self._pending_responses: Dict[str, asyncio.Future] = {}
        
        # 消息回调是否已注册
        self._callback_registered = False
        
        # 断路器状态
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # 工作流管理
        self._active_workflows: Dict[str, Workflow] = {}
        
        # 注册消息处理器
        self._register_handlers()
    
    def _register_handlers(self):
        """
        注册不同类型消息的处理器
        """
        self.message_handlers[MCPMessageType.COMMAND] = self.handle_command
        self.message_handlers[MCPMessageType.RESPONSE] = self.handle_response
        self.message_handlers[MCPMessageType.EVENT] = self.handle_event
        self.message_handlers[MCPMessageType.DATA] = self.handle_data
        self.message_handlers[MCPMessageType.QUERY] = self.handle_query
        self.message_handlers[MCPMessageType.ERROR] = self.handle_error
        self.message_handlers[MCPMessageType.STATE_UPDATE] = self.handle_state_update
        self.message_handlers[MCPMessageType.HEARTBEAT] = self.handle_heartbeat
    
    async def initialize(self):
        """
        初始化代理，包括订阅消息和启动心跳
        """
        if self.is_initialized:
            return
        
        # 订阅直接消息
        if not self._callback_registered:
            await mcp_message_bus.subscribe_direct(self.agent_id, self._message_callback)
            self._callback_registered = True
        
        self.is_initialized = True
        self.logger.info(f"Agent {self.agent_name} ({self.agent_id}) initialized")
        
        # 发送代理上线事件
        agent_online_event = create_event_message(
            source=self.agent_id,
            target="broadcast",
            event_type="agent.online",
            data={
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "timestamp": datetime.now().isoformat(),
                "version": self.version
            }
        )
        await mcp_message_bus.publish(agent_online_event)
    
    async def start(self):
        """
        启动代理，包括启动心跳任务
        """
        if not self.is_initialized:
            await self.initialize()
        
        if self.is_running:
            return
        
        self.is_running = True
        self.start_time = time.time()
        
        # 启动心跳任务
        self._heartbeat_task = asyncio.create_task(self._send_heartbeats())
        
        self.logger.info(f"Agent {self.agent_name} ({self.agent_id}) started")
        
        # 运行自定义启动逻辑
        await self.on_start()
    
    async def stop(self):
        """
        停止代理，包括取消心跳任务和清理资源
        """
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 发送代理下线事件
        agent_offline_event = create_event_message(
            source=self.agent_id,
            target="broadcast",
            event_type="agent.offline",
            data={
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "timestamp": datetime.now().isoformat()
            }
        )
        await mcp_message_bus.publish(agent_offline_event)
        
        # 停止心跳任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        
        # 取消订阅
        if self._callback_registered:
            await mcp_message_bus.unsubscribe_direct(self.agent_id, self._message_callback)
            self._callback_registered = False
        
        # 取消所有等待响应的future
        for future in self._pending_responses.values():
            if not future.done():
                future.cancel()
        
        # 运行自定义停止逻辑
        await self.on_stop()
        
        self.logger.info(f"Agent {self.agent_name} ({self.agent_id}) stopped")
    
    async def _message_callback(self, message: MCPMessage):
        """
        处理接收到的MCP消息
        
        Args:
            message: 接收到的MCP消息
        """
        try:
            message_type = message.header.message_type
            self.logger.debug(f"Received {message_type} message: {message.header.message_id} from {message.header.source}")
            
            # 查找对应的处理器
            handler = self.message_handlers.get(message_type)
            if handler:
                # 执行处理器
                response = await handler(message)
                
                # 如果有响应，发送回去
                if response:
                    await mcp_message_bus.publish(response)
            else:
                self.logger.warning(f"No handler for message type: {message_type}")
                
                # 发送错误响应
                error_message = message.create_error_response(
                    error_code="HANDLER_NOT_FOUND",
                    error_message=f"No handler for message type: {message_type}"
                )
                await mcp_message_bus.publish(error_message)
                
        except Exception as e:
            self.logger.error(f"Error handling message {message.header.message_id}: {str(e)}")
            
            # 发送错误响应
            try:
                error_message = message.create_error_response(
                    error_code="PROCESSING_ERROR",
                    error_message=f"Error processing message: {str(e)}",
                    details={"exception": str(e)}
                )
                await mcp_message_bus.publish(error_message)
            except Exception:
                self.logger.exception("Failed to send error response")
    
    async def _send_heartbeats(self):
        """
        周期性发送心跳消息
        """
        while self.is_running:
            try:
                # 计算负载和运行时间
                uptime = int(time.time() - self.start_time) if self.start_time else 0
                
                # 创建并发送心跳消息
                heartbeat_msg = create_heartbeat_message(
                    source=self.agent_id,
                    agent_id=self.agent_id,
                    status="active" if self.is_running else "idle",
                    load=await self._get_current_load(),
                    uptime_seconds=uptime
                )
                await mcp_message_bus.publish(heartbeat_msg)
                
                # 等待下一次心跳时间
                await asyncio.sleep(self._heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error sending heartbeat: {str(e)}")
                await asyncio.sleep(5)  # 出错后短暂等待再重试
    
    async def _get_current_load(self) -> float:
        """
        获取当前代理负载情况，应该返回0-1之间的值
        
        Returns:
            负载值，0表示空闲，1表示满负荷
        """
        # 默认实现返回0.5，子类可以覆盖此方法
        return 0.5
    
    async def send_command(
        self,
        target: str,
        action: str,
        parameters: Dict[str, Any],
        session_id: Optional[str] = None,
        priority: MCPPriority = MCPPriority.NORMAL,
        timeout_seconds: Optional[int] = 60,
        wait_for_response: bool = True,
        response_timeout: float = 30.0,
        retry_config: Optional[Dict[str, Any]] = None
    ) -> Optional[MCPMessage]:
        """
        发送命令消息给目标代理
        
        Args:
            target: 目标代理ID
            action: 命令动作
            parameters: 命令参数
            session_id: 会话ID
            priority: 优先级
            timeout_seconds: 命令执行超时时间
            wait_for_response: 是否等待响应
            response_timeout: 等待响应的超时时间
            retry_config: 重试配置，包含以下可选参数:
                max_retries: 最大重试次数
                base_delay_ms: 初始延迟(毫秒)
                max_delay_ms: 最大延迟(毫秒)
                jitter: 随机抖动比例(0-1)
            
        Returns:
            如果wait_for_response为True，返回响应消息；否则返回None
        """
        # 设置默认重试配置
        default_retry_config = {
            "max_retries": 3,
            "base_delay_ms": 200,
            "max_delay_ms": 10000,
            "jitter": 0.1
        }
        
        # 合并用户配置
        if retry_config:
            retry_settings = {**default_retry_config, **retry_config}
        else:
            retry_settings = default_retry_config
            
        # 生成幂等性键，确保重试时命令只被执行一次
        idempotency_key = f"{self.agent_id}_{target}_{action}_{uuid.uuid4().hex[:8]}"
        
        # 创建包含幂等性键的命令
        command = MCPCommand(
            action=action,
            parameters=parameters,
            timeout_seconds=timeout_seconds,
            idempotency_key=idempotency_key
        )
        
        # 创建命令消息
        command_msg = MCPMessage(
            header=MCPHeader(
                source=self.agent_id,
                target=target,
                message_type=MCPMessageType.COMMAND,
                session_id=session_id,
                priority=priority
            ),
            body=command
        )
        
        # 重试逻辑
        attempts = 0
        last_error = None
        
        while attempts <= retry_settings["max_retries"]:
            try:
                # 发布消息
                message_id = await mcp_message_bus.publish(command_msg)
                
                # 等待响应
                if wait_for_response:
                    response = await mcp_message_bus.wait_for_response(
                        message_id=message_id,
                        timeout=response_timeout,
                        expected_source=target
                    )
                    
                    # 检查响应，如果是错误且可重试，则进行重试
                    if response and response.header.message_type == MCPMessageType.ERROR:
                        error_body = response.body
                        if isinstance(error_body, MCPError) and error_body.retry_possible and error_body.category == "TEMPORARY":
                            # 保存错误信息
                            last_error = error_body
                            
                            # 使用错误消息中建议的重试策略，如果有的话
                            if error_body.max_retries is not None:
                                retry_settings["max_retries"] = error_body.max_retries
                            
                            if error_body.retry_delay_ms is not None:
                                delay_ms = error_body.retry_delay_ms
                            else:
                                # 计算指数退避延迟
                                delay_ms = min(
                                    retry_settings["base_delay_ms"] * (2 ** attempts),
                                    retry_settings["max_delay_ms"]
                                )
                                
                                # 添加随机抖动
                                jitter_amount = delay_ms * retry_settings["jitter"]
                                delay_ms += random.uniform(-jitter_amount, jitter_amount)
                                
                            # 等待延迟时间
                            self.logger.info(f"Retrying command {action} after {delay_ms}ms (attempt {attempts+1}/{retry_settings['max_retries']})")
                            await asyncio.sleep(delay_ms / 1000.0)  # 转换为秒
                            
                            # 增加尝试次数并继续循环
                            attempts += 1
                            continue
                    
                    # 返回响应（成功响应或不可重试的错误）
                    return response
                
                # 如果不等待响应，则直接返回
                return None
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Command {action} timed out after {response_timeout}s")
                
                # 判断是否继续重试
                if attempts < retry_settings["max_retries"]:
                    # 计算指数退避延迟
                    delay_ms = min(
                        retry_settings["base_delay_ms"] * (2 ** attempts),
                        retry_settings["max_delay_ms"]
                    )
                    
                    # 添加随机抖动
                    jitter_amount = delay_ms * retry_settings["jitter"]
                    delay_ms += random.uniform(-jitter_amount, jitter_amount)
                    
                    # 等待延迟时间
                    self.logger.info(f"Retrying command {action} after {delay_ms}ms (attempt {attempts+1}/{retry_settings['max_retries']})")
                    await asyncio.sleep(delay_ms / 1000.0)
                else:
                    # 超过最大重试次数，创建超时错误响应
                    timeout_error = MCPError(
                        error_code="COMMAND_TIMEOUT",
                        error_message=f"Command {action} timed out after {attempts} attempts",
                        retry_possible=False,
                        category="PERMANENT"
                    )
                    
                    # 创建错误响应消息
                    error_response = MCPMessage(
                        header=MCPHeader(
                            source="system",
                            target=self.agent_id,
                            message_type=MCPMessageType.ERROR,
                            correlation_id=command_msg.header.message_id
                        ),
                        body=timeout_error
                    )
                    
                    return error_response
            
            # 增加尝试次数
            attempts += 1
        
        # 如果所有重试都失败，返回最后的错误
        if last_error:
            error_response = MCPMessage(
                header=MCPHeader(
                    source="system",
                    target=self.agent_id,
                    message_type=MCPMessageType.ERROR,
                    correlation_id=command_msg.header.message_id
                ),
                body=MCPError(
                    error_code="MAX_RETRIES_EXCEEDED",
                    error_message=f"Command {action} failed after {retry_settings['max_retries']} attempts",
                    retry_possible=False,
                    category="PERMANENT",
                    details={"last_error": last_error.dict()}
                )
            )
            return error_response
        
        return None
    
    async def send_event(
        self,
        target: str,
        event_type: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """
        发送事件消息
        
        Args:
            target: 目标代理ID或"broadcast"进行广播
            event_type: 事件类型
            data: 事件数据
            session_id: 会话ID
            
        Returns:
            消息ID
        """
        # 创建事件消息
        event_msg = create_event_message(
            source=self.agent_id,
            target=target,
            event_type=event_type,
            data=data,
            session_id=session_id
        )
        
        # 发布消息
        return await mcp_message_bus.publish(event_msg)
    
    async def broadcast_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """
        广播事件消息给所有代理
        
        Args:
            event_type: 事件类型
            data: 事件数据
            session_id: 会话ID
            
        Returns:
            消息ID
        """
        return await self.send_event(
            target="broadcast",
            event_type=event_type,
            data=data,
            session_id=session_id
        )
    
    async def get_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取代理状态
        
        Args:
            agent_id: 特定代理ID，如果为None则返回所有代理状态
            
        Returns:
            代理状态信息
        """
        return mcp_message_bus.get_agent_status(agent_id)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前代理状态
        
        Returns:
            当前代理状态信息
        """
        uptime = int(time.time() - self.start_time) if self.start_time else 0
        
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": "active" if self.is_running else "inactive",
            "initialized": self.is_initialized,
            "uptime_seconds": uptime,
            "version": self.version
        }
    
    # 以下是需要子类实现的抽象方法
    
    @abstractmethod
    async def handle_command(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理命令消息
        
        Args:
            message: 命令消息
            
        Returns:
            可选的响应消息
        """
        pass
    
    async def handle_response(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理响应消息
        
        Args:
            message: 响应消息
            
        Returns:
            可选的响应消息（通常为None）
        """
        # 默认实现只记录日志，子类可以覆盖
        correlation_id = message.header.correlation_id
        if correlation_id:
            self.logger.debug(f"Received response for message {correlation_id}")
        
        return None
    
    async def handle_event(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理事件消息
        
        Args:
            message: 事件消息
            
        Returns:
            可选的响应消息（通常为None）
        """
        # 默认实现只记录日志，子类可以覆盖
        if isinstance(message.body, MCPEvent):
            self.logger.debug(f"Received event {message.body.event_type} from {message.header.source}")
        
        return None
    
    async def handle_data(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理数据消息
        
        Args:
            message: 数据消息
            
        Returns:
            可选的响应消息
        """
        # 默认实现只记录日志，子类可以覆盖
        self.logger.debug(f"Received data message from {message.header.source}")
        
        return None
    
    async def handle_query(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理查询消息
        
        Args:
            message: 查询消息
            
        Returns:
            查询响应消息
        """
        # 默认实现返回未实现错误，子类应该覆盖
        self.logger.warning(f"Received query message from {message.header.source}, but not implemented")
        
        return message.create_error_response(
            error_code="NOT_IMPLEMENTED",
            error_message=f"Query handling not implemented in {self.agent_id}"
        )
    
    async def handle_error(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理错误消息
        
        Args:
            message: 错误消息
            
        Returns:
            可选的响应消息（通常为None）
        """
        # 默认实现只记录日志，子类可以覆盖
        if isinstance(message.body, MCPError):
            self.logger.error(f"Received error from {message.header.source}: {message.body.error_code} - {message.body.error_message}")
        
        return None
    
    async def handle_state_update(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理状态更新消息
        
        Args:
            message: 状态更新消息
            
        Returns:
            可选的响应消息（通常为None）
        """
        # 默认实现只记录日志，子类可以覆盖
        self.logger.debug(f"Received state update from {message.header.source}")
        
        return None
    
    async def handle_heartbeat(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理心跳消息
        
        Args:
            message: 心跳消息
            
        Returns:
            可选的响应消息（通常为None）
        """
        # 默认情况下不处理心跳消息
        return None
    
    async def on_start(self):
        """
        代理启动时的自定义逻辑
        """
        # 默认实现为空，子类可以覆盖
        pass
    
    async def on_stop(self):
        """
        代理停止时的自定义逻辑
        """
        # 默认实现为空，子类可以覆盖
        pass
    
    async def create_workflow(self, name: str, initial_state: str, initial_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        创建并启动工作流
        
        Args:
            name: 工作流名称
            initial_state: 初始状态
            initial_data: 初始数据
            
        Returns:
            工作流ID，如果创建失败则返回None
        """
        # 创建工作流
        workflow = workflow_manager.create_workflow(name, self.agent_id)
        
        # 添加工作流状态
        self._setup_workflow_states(workflow)
        
        # 启动工作流
        success = await workflow.start(initial_state, initial_data)
        
        if success:
            # 添加到活动工作流列表
            self._active_workflows[workflow.workflow_id] = workflow
            self.logger.info(f"Started workflow {name} ({workflow.workflow_id}) in state {initial_state}")
            return workflow.workflow_id
        else:
            self.logger.error(f"Failed to start workflow {name}")
            return None
    
    def _setup_workflow_states(self, workflow: Workflow) -> None:
        """
        设置工作流状态
        
        Args:
            workflow: 工作流实例
        """
        # 子类应该覆盖此方法，添加自定义状态
        pass
    
    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流信息
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            工作流信息，如果不存在则返回None
        """
        workflow = workflow_manager.get_workflow(workflow_id)
        
        if workflow and workflow.agent_id == self.agent_id:
            return {
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
                "current_state": workflow.current_state,
                "status": workflow.data["status"],
                "data": workflow.data
            }
        
        return None
    
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """
        列出代理的所有工作流
        
        Returns:
            工作流信息列表
        """
        return workflow_manager.list_workflows(self.agent_id)
    
    async def transition_workflow(self, workflow_id: str, next_state: str, reason: str = "agent_transition") -> bool:
        """
        转换工作流状态
        
        Args:
            workflow_id: 工作流ID
            next_state: 下一个状态
            reason: 转换原因
            
        Returns:
            是否成功转换
        """
        workflow = workflow_manager.get_workflow(workflow_id)
        
        if workflow and workflow.agent_id == self.agent_id:
            return await workflow.transition(next_state, reason)
        
        self.logger.error(f"Workflow {workflow_id} not found or not owned by this agent")
        return False
    
    async def stop_workflow(self, workflow_id: str, reason: str = "agent_stop") -> bool:
        """
        停止工作流
        
        Args:
            workflow_id: 工作流ID
            reason: 停止原因
            
        Returns:
            是否成功停止
        """
        workflow = workflow_manager.get_workflow(workflow_id)
        
        if workflow and workflow.agent_id == self.agent_id:
            await workflow.stop(reason)
            
            # 从活动工作流列表中移除
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]
                
            return True
        
        self.logger.error(f"Workflow {workflow_id} not found or not owned by this agent")
        return False
    
    async def create_workflow_checkpoint(self, workflow_id: str, checkpoint_id: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        创建工作流检查点
        
        Args:
            workflow_id: 工作流ID
            checkpoint_id: 检查点ID
            data: 检查点数据
            
        Returns:
            是否成功创建
        """
        workflow = workflow_manager.get_workflow(workflow_id)
        
        if workflow and workflow.agent_id == self.agent_id:
            workflow.create_checkpoint(checkpoint_id, data)
            return True
        
        self.logger.error(f"Workflow {workflow_id} not found or not owned by this agent")
        return False
    
    async def restore_workflow_checkpoint(self, workflow_id: str, checkpoint_id: str) -> bool:
        """
        从检查点恢复工作流
        
        Args:
            workflow_id: 工作流ID
            checkpoint_id: 检查点ID
            
        Returns:
            是否成功恢复
        """
        workflow = workflow_manager.get_workflow(workflow_id)
        
        if workflow and workflow.agent_id == self.agent_id:
            return await workflow.restore_from_checkpoint(checkpoint_id)
        
        self.logger.error(f"Workflow {workflow_id} not found or not owned by this agent")
        return False 