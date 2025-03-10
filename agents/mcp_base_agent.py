"""
MCP基础代理类
所有基于MCP协议的代理都应继承自此类
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from models.mcp import (MCPCommand, MCPContentType, MCPError, MCPEvent,
                        MCPHeartbeat, MCPMessage, MCPMessageType, MCPPriority,
                        MCPQuery, MCPResponse, MCPStatus, create_command_message,
                        create_event_message, create_heartbeat_message)
from utils.mcp_message_bus import message_bus


class MCPBaseAgent(ABC):
    """MCP基础代理类，所有基于MCP协议的代理都应继承自此类"""
    
    def __init__(self, agent_id: str, agent_name: str):
        """初始化代理"""
        # 代理ID和名称
        self.agent_id = agent_id
        self.agent_name = agent_name
        
        # 日志记录器
        self.logger = logging.getLogger(f"mcp.agent.{agent_id}")
        
        # 运行状态
        self.is_running = False
        
        # 心跳任务
        self._heartbeat_task = None
        
        # 心跳间隔（秒）
        self._heartbeat_interval = 10
        
        # 启动时间
        self._start_time = None
        
        # 消息处理器映射
        self._message_handlers = {}
        
        # 注册消息处理器
        self._register_handlers()
        
        # 代理状态
        self._status = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": "initialized",
            "uptime": 0,
            "messages_processed": 0,
            "errors": 0,
            "last_error": None
        }

    def _register_handlers(self):
        """注册消息处理器"""
        self._message_handlers = {
            MCPMessageType.COMMAND: self.handle_command,
            MCPMessageType.RESPONSE: self.handle_response,
            MCPMessageType.EVENT: self.handle_event,
            MCPMessageType.DATA: self.handle_data,
            MCPMessageType.ERROR: self.handle_error,
            MCPMessageType.QUERY: self.handle_query,
            MCPMessageType.STATE_UPDATE: self.handle_state_update,
            MCPMessageType.HEARTBEAT: self.handle_heartbeat
        }

    async def initialize(self):
        """初始化代理，包括订阅消息"""
        self.logger.info(f"初始化代理 {self.agent_id}")
        
        # 订阅发送给该代理的消息
        await message_bus.subscribe_direct(self.agent_id, self._message_callback)
        
        # 订阅广播消息
        await message_bus.subscribe_direct("broadcast", self._message_callback)
        
        # 订阅心跳消息
        await message_bus.subscribe_type(MCPMessageType.HEARTBEAT, self._message_callback)
        
        # 更新状态
        self._status["status"] = "initialized"
        
        self.logger.info(f"代理 {self.agent_id} 初始化完成")

    async def start(self):
        """启动代理，包括启动心跳任务"""
        if self.is_running:
            self.logger.warning(f"代理 {self.agent_id} 已经在运行中")
            return
        
        self.logger.info(f"启动代理 {self.agent_id}")
        
        # 设置运行状态
        self.is_running = True
        
        # 记录启动时间
        self._start_time = time.time()
        
        # 启动心跳任务
        self._heartbeat_task = asyncio.create_task(self._send_heartbeats())
        
        # 更新状态
        self._status["status"] = "running"
        
        # 调用子类的启动方法
        await self.on_start()
        
        self.logger.info(f"代理 {self.agent_id} 启动完成")

    async def stop(self):
        """停止代理，清理资源"""
        if not self.is_running:
            self.logger.warning(f"代理 {self.agent_id} 未在运行")
            return
        
        self.logger.info(f"停止代理 {self.agent_id}")
        
        # 设置运行状态
        self.is_running = False
        
        # 取消心跳任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 取消订阅
        await message_bus.unsubscribe_direct(self.agent_id, self._message_callback)
        await message_bus.unsubscribe_direct("broadcast", self._message_callback)
        await message_bus.unsubscribe_type(MCPMessageType.HEARTBEAT, self._message_callback)
        
        # 更新状态
        self._status["status"] = "stopped"
        
        # 调用子类的停止方法
        await self.on_stop()
        
        self.logger.info(f"代理 {self.agent_id} 已停止")

    async def _message_callback(self, message: MCPMessage):
        """处理接收到的消息"""
        try:
            # 检查消息类型
            message_type = message.header.message_type
            
            # 如果是心跳消息且不是发给该代理的，忽略
            if message_type == MCPMessageType.HEARTBEAT and message.header.target not in [self.agent_id, "broadcast", "system"]:
                return
            
            # 记录消息接收
            self.logger.debug(f"收到消息: {message.header.message_id}, 类型: {message_type}, 来源: {message.header.source}")
            
            # 获取对应的处理器
            handler = self._message_handlers.get(message_type)
            
            if handler:
                # 处理消息
                response = await handler(message)
                
                # 如果有响应，发送响应
                if response:
                    await message_bus.publish(response)
                
                # 更新状态
                self._status["messages_processed"] += 1
            else:
                self.logger.warning(f"未知消息类型: {message_type}")
                
        except Exception as e:
            self.logger.error(f"处理消息 {message.header.message_id} 时发生错误: {str(e)}", exc_info=True)
            
            # 更新状态
            self._status["errors"] += 1
            self._status["last_error"] = str(e)
            
            # 如果是命令消息，返回错误响应
            if message.header.message_type == MCPMessageType.COMMAND:
                error_response = message.create_error_response(
                    error_code="PROCESSING_ERROR",
                    error_message=f"处理命令时发生错误: {str(e)}",
                    details={"exception": str(e)}
                )
                await message_bus.publish(error_response)

    async def _send_heartbeats(self):
        """定期发送心跳消息"""
        self.logger.info(f"代理 {self.agent_id} 开始发送心跳")
        
        while self.is_running:
            try:
                # 创建心跳消息
                heartbeat_msg = create_heartbeat_message(
                    source=self.agent_id,
                    agent_id=self.agent_id,
                    status="active",
                    load=await self._get_current_load()
                )
                
                # 发送心跳消息
                await message_bus.publish(heartbeat_msg)
                
                # 更新状态
                self._status["uptime"] = int(time.time() - self._start_time)
                
                # 等待下一次心跳
                await asyncio.sleep(self._heartbeat_interval)
                
            except asyncio.CancelledError:
                self.logger.info(f"代理 {self.agent_id} 心跳任务被取消")
                break
            except Exception as e:
                self.logger.error(f"发送心跳时发生错误: {str(e)}", exc_info=True)
                await asyncio.sleep(self._heartbeat_interval)
        
        self.logger.info(f"代理 {self.agent_id} 心跳任务结束")

    async def _get_current_load(self) -> float:
        """获取当前负载情况，返回0-1之间的值"""
        # 默认实现，子类可以重写
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
        """发送命令消息"""
        if not self.is_running:
            raise RuntimeError(f"代理 {self.agent_id} 未在运行")
        
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
        
        # 发送命令
        message_id = await message_bus.publish(command_msg)
        
        self.logger.debug(f"发送命令: {action}, 目标: {target}, 消息ID: {message_id}")
        
        # 如果需要等待响应
        if wait_for_response:
            # 等待响应
            response = await message_bus.wait_for_response(
                message_id=message_id,
                timeout=response_timeout,
                expected_source=target
            )
            
            if response:
                self.logger.debug(f"收到响应: {response.header.message_id}, 来源: {response.header.source}")
                return response
            else:
                self.logger.warning(f"等待命令 {action} 的响应超时")
                return None
        
        return None

    async def send_event(
        self,
        target: str,
        event_type: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """发送事件消息"""
        if not self.is_running:
            raise RuntimeError(f"代理 {self.agent_id} 未在运行")
        
        # 创建事件消息
        event_msg = create_event_message(
            source=self.agent_id,
            target=target,
            event_type=event_type,
            data=data,
            session_id=session_id
        )
        
        # 发送事件
        message_id = await message_bus.publish(event_msg)
        
        self.logger.debug(f"发送事件: {event_type}, 目标: {target}, 消息ID: {message_id}")
        
        return message_id

    async def broadcast_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """广播事件消息"""
        if not self.is_running:
            raise RuntimeError(f"代理 {self.agent_id} 未在运行")
        
        # 创建事件消息
        event_msg = create_event_message(
            source=self.agent_id,
            target="broadcast",
            event_type=event_type,
            data=data,
            session_id=session_id
        )
        
        # 发送事件
        message_id = await message_bus.publish(event_msg)
        
        self.logger.debug(f"广播事件: {event_type}, 消息ID: {message_id}")
        
        return message_id

    async def get_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """获取代理状态"""
        if not self.is_running:
            raise RuntimeError(f"代理 {self.agent_id} 未在运行")
        
        return message_bus.get_agent_status(agent_id)

    def get_status(self) -> Dict[str, Any]:
        """获取当前代理的状态"""
        # 更新状态
        if self._start_time:
            self._status["uptime"] = int(time.time() - self._start_time)
        
        # 返回状态副本
        return dict(self._status)

    @abstractmethod
    async def handle_command(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理命令消息，子类必须实现"""
        # 子类必须实现此方法
        pass

    async def handle_response(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理响应消息"""
        # 默认实现，子类可以重写
        self.logger.debug(f"收到响应消息: {message.header.message_id}")
        
        # 响应消息通常不需要回复
        return None

    async def handle_event(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理事件消息"""
        # 默认实现，子类可以重写
        self.logger.debug(f"收到事件消息: {message.header.message_id}, 事件类型: {message.body.event_type}")
        
        # 事件消息通常不需要回复
        return None

    async def handle_data(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理数据消息"""
        # 默认实现，子类可以重写
        self.logger.debug(f"收到数据消息: {message.header.message_id}")
        
        # 数据消息通常不需要回复
        return None

    async def handle_query(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理查询消息"""
        # 默认实现，子类可以重写
        self.logger.debug(f"收到查询消息: {message.header.message_id}, 查询类型: {message.body.query_type}")
        
        # 查询消息通常需要回复，但默认实现不处理任何查询
        return message.create_error_response(
            error_code="NOT_IMPLEMENTED",
            error_message=f"代理 {self.agent_id} 不支持查询类型: {message.body.query_type}"
        )

    async def handle_error(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理错误消息"""
        # 默认实现，子类可以重写
        self.logger.warning(f"收到错误消息: {message.header.message_id}, 错误代码: {message.body.error_code}, 错误消息: {message.body.error_message}")
        
        # 错误消息通常不需要回复
        return None

    async def handle_state_update(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理状态更新消息"""
        # 默认实现，子类可以重写
        self.logger.debug(f"收到状态更新消息: {message.header.message_id}, 实体: {message.body.entity_id}")
        
        # 状态更新消息通常不需要回复
        return None

    async def handle_heartbeat(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理心跳消息"""
        # 默认实现，子类可以重写
        # 心跳消息通常不需要特殊处理
        return None

    async def on_start(self):
        """代理启动时调用，子类可以重写"""
        # 默认实现为空，子类可以重写
        pass

    async def on_stop(self):
        """代理停止时调用，子类可以重写"""
        # 默认实现为空，子类可以重写
        pass