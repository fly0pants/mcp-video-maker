import asyncio
import uuid
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Awaitable, Set
from abc import ABC, abstractmethod
from datetime import datetime

from models.mcp import (
    MCPMessage, MCPMessageType, MCPStatus, MCPPriority, MCPContentFormat,
    MCPCommand, MCPResponse, MCPError, MCPEvent, MCPHeartbeat,
    create_command_message, create_event_message, create_heartbeat_message
)
from utils.mcp_message_bus import mcp_message_bus


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
        response_timeout: float = 30.0
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
            
        Returns:
            如果wait_for_response为True，返回响应消息；否则返回None
        """
        # 创建命令消息
        command_msg = create_command_message(
            source=self.agent_id,
            target=target,
            action=action,
            parameters=parameters,
            session_id=session_id,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        
        # 发布消息
        message_id = await mcp_message_bus.publish(command_msg)
        
        # 等待响应
        if wait_for_response:
            return await mcp_message_bus.wait_for_response(
                message_id=message_id,
                timeout=response_timeout,
                expected_source=target
            )
        
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