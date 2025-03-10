import asyncio
import logging
import time
from typing import Dict, List, Set, Callable, Awaitable, Optional, Any, Union
from datetime import datetime
import uuid

from models.mcp import (
    MCPMessage, MCPHeader, MCPMessageType, MCPStatus, MCPPriority,
    MCPResponse, MCPError, MCPHeartbeat, MCPEvent,
    create_command_message, create_event_message
)


class MCPMessageBus:
    """MCP协议消息总线，用于多代理系统间通信"""

    def __init__(self):
        self.logger = logging.getLogger("MCPMessageBus")
        
        # 消息队列和处理器
        self._message_queue = asyncio.Queue()
        self._is_running = False
        self._processing_task = None
        
        # 按照agent_id的订阅者注册表 - 直接消息
        self._direct_subscribers: Dict[str, Set[Callable[[MCPMessage], Awaitable[None]]]] = {}
        
        # 按照主题的订阅者注册表 - 主题消息
        self._topic_subscribers: Dict[str, Set[Callable[[MCPMessage], Awaitable[None]]]] = {}
        
        # 按照消息类型的订阅者注册表 - 类型消息
        self._type_subscribers: Dict[MCPMessageType, Set[Callable[[MCPMessage], Awaitable[None]]]] = {
            msg_type: set() for msg_type in MCPMessageType
        }
        
        # 存储所有已处理的消息
        self._message_history: List[MCPMessage] = []
        
        # 消息ID到消息的映射，用于快速查找
        self._message_map: Dict[str, MCPMessage] = {}
        
        # 等待响应的future字典
        self._response_futures: Dict[str, asyncio.Future] = {}
        
        # 会话ID映射到相关消息ID列表
        self._session_messages: Dict[str, List[str]] = {}
        
        # 代理在线状态和心跳监控
        self._agent_heartbeats: Dict[str, Dict[str, Any]] = {}
        self._heartbeat_monitoring_task = None
        
        # 性能指标
        self._metrics = {
            "messages_processed": 0,
            "messages_published": 0,
            "processing_times": [],  # 存储最近100条消息的处理时间
            "error_count": 0,
            "start_time": time.time()
        }

    async def start(self):
        """启动消息总线"""
        if self._is_running:
            return
        
        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_messages())
        self._heartbeat_monitoring_task = asyncio.create_task(self._monitor_agent_heartbeats())
        
        self.logger.info("MCP Message Bus started")
        
        # 发布系统启动事件
        system_event = create_event_message(
            source="system",
            target="broadcast",
            event_type="system.started",
            data={"timestamp": datetime.now().isoformat()}
        )
        await self.publish(system_event)

    async def stop(self):
        """停止消息总线"""
        if not self._is_running:
            return
            
        self._is_running = False
        
        # 发布系统关闭事件
        system_event = create_event_message(
            source="system",
            target="broadcast",
            event_type="system.stopping",
            data={"timestamp": datetime.now().isoformat()}
        )
        await self.publish(system_event)
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            
        if self._heartbeat_monitoring_task:
            self._heartbeat_monitoring_task.cancel()
            try:
                await self._heartbeat_monitoring_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_monitoring_task = None
            
        # 取消所有等待响应的future
        for future in self._response_futures.values():
            if not future.done():
                future.cancel()
                
        self.logger.info("MCP Message Bus stopped")

    async def publish(self, message: MCPMessage) -> str:
        """
        发布MCP消息到总线
        
        Args:
            message: MCP消息对象
            
        Returns:
            消息ID
        """
        # 确保消息有ID
        if not message.header.message_id:
            message.header.message_id = f"mcp_{uuid.uuid4().hex[:10]}"
            
        # 添加到历史记录和映射
        self._message_history.append(message)
        self._message_map[message.header.message_id] = message
        
        # 如果消息有会话ID，添加到会话映射
        if message.header.session_id:
            if message.header.session_id not in self._session_messages:
                self._session_messages[message.header.session_id] = []
            self._session_messages[message.header.session_id].append(message.header.message_id)
        
        # 放入消息队列
        await self._message_queue.put(message)
        
        # 更新指标
        self._metrics["messages_published"] += 1
        
        # 确保处理循环在运行
        if not self._is_running:
            await self.start()
            
        self.logger.debug(f"Published message {message.header.message_id} from {message.header.source} to {message.header.target}")
        return message.header.message_id

    async def subscribe_direct(self, agent_id: str, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """
        订阅直接发送给特定代理的消息
        
        Args:
            agent_id: 代理标识符
            callback: 处理消息的回调函数
        """
        if agent_id not in self._direct_subscribers:
            self._direct_subscribers[agent_id] = set()
        
        self._direct_subscribers[agent_id].add(callback)
        self.logger.debug(f"Agent {agent_id} subscribed to direct messages")

    async def unsubscribe_direct(self, agent_id: str, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """
        取消直接消息订阅
        
        Args:
            agent_id: 代理标识符
            callback: 要取消的回调函数
        """
        if agent_id in self._direct_subscribers and callback in self._direct_subscribers[agent_id]:
            self._direct_subscribers[agent_id].remove(callback)
            if not self._direct_subscribers[agent_id]:
                del self._direct_subscribers[agent_id]
            
            self.logger.debug(f"Agent {agent_id} unsubscribed from direct messages")

    async def subscribe_topic(self, topic: str, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """
        订阅特定主题的消息
        
        Args:
            topic: 主题名称
            callback: 处理消息的回调函数
        """
        if topic not in self._topic_subscribers:
            self._topic_subscribers[topic] = set()
        
        self._topic_subscribers[topic].add(callback)
        self.logger.debug(f"Subscribed to topic {topic}")

    async def unsubscribe_topic(self, topic: str, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """
        取消主题订阅
        
        Args:
            topic: 主题名称
            callback: 要取消的回调函数
        """
        if topic in self._topic_subscribers and callback in self._topic_subscribers[topic]:
            self._topic_subscribers[topic].remove(callback)
            if not self._topic_subscribers[topic]:
                del self._topic_subscribers[topic]
            
            self.logger.debug(f"Unsubscribed from topic {topic}")

    async def subscribe_type(self, message_type: MCPMessageType, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """
        订阅特定类型的消息
        
        Args:
            message_type: 消息类型
            callback: 处理消息的回调函数
        """
        self._type_subscribers[message_type].add(callback)
        self.logger.debug(f"Subscribed to message type {message_type}")

    async def unsubscribe_type(self, message_type: MCPMessageType, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """
        取消类型订阅
        
        Args:
            message_type: 消息类型
            callback: 要取消的回调函数
        """
        if callback in self._type_subscribers[message_type]:
            self._type_subscribers[message_type].remove(callback)
            self.logger.debug(f"Unsubscribed from message type {message_type}")

    async def wait_for_response(
        self, 
        message_id: str, 
        timeout: float = 60.0,
        expected_source: Optional[str] = None
    ) -> Optional[MCPMessage]:
        """
        等待特定消息的响应
        
        Args:
            message_id: 原始消息ID
            timeout: 超时时间（秒）
            expected_source: 期望的响应来源
            
        Returns:
            响应消息，如果超时则返回None
        """
        # 检查消息ID是否存在
        if message_id not in self._message_map:
            self.logger.warning(f"Cannot wait for response to unknown message {message_id}")
            return None
            
        # 创建Future
        future = asyncio.Future()
        self._response_futures[message_id] = future
        
        try:
            # 等待响应，超时处理
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout waiting for response to message {message_id}")
            return None
        finally:
            # 清理Future
            if message_id in self._response_futures:
                del self._response_futures[message_id]

    def get_message_history(
        self, 
        limit: Optional[int] = None, 
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        message_type: Optional[MCPMessageType] = None
    ) -> List[MCPMessage]:
        """
        获取消息历史
        
        Args:
            limit: 返回的最大消息数量
            agent_id: 按代理ID过滤
            session_id: 按会话ID过滤
            message_type: 按消息类型过滤
            
        Returns:
            过滤后的消息列表
        """
        filtered_messages = self._message_history
        
        # 按会话ID筛选
        if session_id:
            if session_id in self._session_messages:
                message_ids = self._session_messages[session_id]
                filtered_messages = [msg for msg in filtered_messages if msg.header.message_id in message_ids]
            else:
                return []
        
        # 按代理ID筛选
        if agent_id:
            filtered_messages = [
                msg for msg in filtered_messages 
                if msg.header.source == agent_id or msg.header.target == agent_id
            ]
        
        # 按消息类型筛选
        if message_type:
            filtered_messages = [
                msg for msg in filtered_messages 
                if msg.header.message_type == message_type
            ]
        
        # 限制返回数量
        if limit and limit > 0:
            filtered_messages = filtered_messages[-limit:]
        
        return filtered_messages

    def get_message_by_id(self, message_id: str) -> Optional[MCPMessage]:
        """按ID获取特定消息"""
        return self._message_map.get(message_id)

    def get_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取代理状态信息
        
        Args:
            agent_id: 特定代理ID，如果为None则返回所有代理状态
            
        Returns:
            代理状态信息
        """
        if agent_id:
            return self._agent_heartbeats.get(agent_id, {"status": "unknown", "last_seen": None})
        else:
            return self._agent_heartbeats

    def get_metrics(self) -> Dict[str, Any]:
        """获取消息总线性能指标"""
        uptime = time.time() - self._metrics["start_time"]
        
        # 计算消息处理速率
        msg_rate = self._metrics["messages_processed"] / uptime if uptime > 0 else 0
        
        # 计算平均处理时间
        avg_processing_time = sum(self._metrics["processing_times"]) / len(self._metrics["processing_times"]) if self._metrics["processing_times"] else 0
        
        return {
            "messages_processed": self._metrics["messages_processed"],
            "messages_published": self._metrics["messages_published"],
            "error_count": self._metrics["error_count"],
            "uptime_seconds": uptime,
            "message_rate_per_second": msg_rate,
            "average_processing_time_ms": avg_processing_time,
            "queue_size": self._message_queue.qsize(),
            "agents_count": len(self._agent_heartbeats),
            "agents_online": sum(1 for status in self._agent_heartbeats.values() if status.get("status") == "active")
        }

    async def _process_messages(self):
        """消息处理循环"""
        while self._is_running:
            try:
                # 从队列获取消息
                message = await self._message_queue.get()
                processing_start = time.time()
                
                # 更新消息状态
                message.header.status = MCPStatus.PROCESSING
                
                # 处理心跳消息
                if message.header.message_type == MCPMessageType.HEARTBEAT and isinstance(message.body, MCPHeartbeat):
                    self._update_agent_heartbeat(message)
                
                # 处理响应消息
                if message.header.message_type in [MCPMessageType.RESPONSE, MCPMessageType.ERROR] and message.header.correlation_id:
                    # 查找等待此响应的future
                    future = self._response_futures.get(message.header.correlation_id)
                    if future and not future.done():
                        future.set_result(message)
                
                # 获取订阅者并分发消息
                subscribers = set()
                
                # 1. 直接消息订阅者
                if message.header.target != "broadcast" and message.header.target in self._direct_subscribers:
                    subscribers.update(self._direct_subscribers[message.header.target])
                
                # 2. 主题订阅者 (对于target为主题的消息)
                if message.header.target.startswith("topic:"):
                    topic = message.header.target[6:]  # 去掉"topic:"前缀
                    if topic in self._topic_subscribers:
                        subscribers.update(self._topic_subscribers[topic])
                
                # 3. 类型订阅者
                if message.header.message_type in self._type_subscribers:
                    subscribers.update(self._type_subscribers[message.header.message_type])
                
                # 4. 广播消息
                if message.header.target == "broadcast":
                    # 向所有直接订阅者广播
                    for subs in self._direct_subscribers.values():
                        subscribers.update(subs)
                
                # 分发消息
                delivery_tasks = []
                for subscriber in subscribers:
                    delivery_tasks.append(asyncio.create_task(subscriber(message)))
                
                # 等待所有订阅者处理完毕
                if delivery_tasks:
                    await asyncio.gather(*delivery_tasks, return_exceptions=True)
                
                # 标记消息为已完成
                message.header.status = MCPStatus.COMPLETED
                
                # 计算处理时间并更新指标
                processing_time = (time.time() - processing_start) * 1000  # 转换为毫秒
                self._metrics["messages_processed"] += 1
                self._metrics["processing_times"].append(processing_time)
                if len(self._metrics["processing_times"]) > 100:
                    self._metrics["processing_times"].pop(0)
                
                # 标记任务完成
                self._message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._metrics["error_count"] += 1
                self.logger.error(f"Error processing MCP message: {str(e)}")

    def _update_agent_heartbeat(self, message: MCPMessage):
        """更新代理心跳状态"""
        if not isinstance(message.body, MCPHeartbeat):
            return
            
        agent_id = message.body.agent_id
        
        self._agent_heartbeats[agent_id] = {
            "status": message.body.status,
            "last_seen": datetime.now(),
            "load": message.body.load,
            "uptime_seconds": message.body.uptime_seconds,
            "version": message.body.version
        }

    async def _monitor_agent_heartbeats(self):
        """监控代理心跳，标记长时间未发送心跳的代理为离线"""
        HEARTBEAT_TIMEOUT = 60  # 60秒没有心跳则认为代理离线
        
        while self._is_running:
            try:
                now = datetime.now()
                offline_agents = []
                
                for agent_id, info in self._agent_heartbeats.items():
                    last_seen = info.get("last_seen")
                    if last_seen and (now - last_seen).total_seconds() > HEARTBEAT_TIMEOUT:
                        if info.get("status") != "offline":
                            offline_agents.append(agent_id)
                            info["status"] = "offline"
                
                # 发布代理离线事件
                for agent_id in offline_agents:
                    event_message = create_event_message(
                        source="system",
                        target="broadcast",
                        event_type="agent.offline",
                        data={"agent_id": agent_id, "timestamp": now.isoformat()}
                    )
                    await self.publish(event_message)
                    self.logger.warning(f"Agent {agent_id} marked as offline due to missing heartbeat")
                
                # 周期性清理过期消息
                self._cleanup_expired_messages()
                
                # 等待下一次检查
                await asyncio.sleep(15)  # 每15秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring agent heartbeats: {str(e)}")
                await asyncio.sleep(5)  # 发生错误时短暂等待后重试

    def _cleanup_expired_messages(self):
        """清理过期的消息"""
        now = datetime.now()
        # 保留最近1000条消息，或者删除超过24小时的消息
        if len(self._message_history) > 1000:
            # 创建新的消息历史列表和映射
            new_history = self._message_history[-1000:]
            new_map = {msg.header.message_id: msg for msg in new_history}
            
            # 更新消息历史和映射
            self._message_history = new_history
            self._message_map = new_map
            
            # 更新会话消息映射
            for session_id in self._session_messages:
                self._session_messages[session_id] = [
                    msg_id for msg_id in self._session_messages[session_id]
                    if msg_id in new_map
                ]


# 全局MCP消息总线实例
mcp_message_bus = MCPMessageBus() 