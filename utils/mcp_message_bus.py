"""
MCP消息总线实现
负责消息的路由、分发和管理
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from models.mcp import MCPMessage, MCPMessageType, MCPStatus


class MCPMessageBus:
    """MCP消息总线，负责消息的路由、分发和管理"""

    def __init__(self):
        """初始化消息总线"""
        # 日志记录器
        self.logger = logging.getLogger("mcp.message_bus")
        
        # 消息队列
        self._message_queue = asyncio.Queue()
        
        # 消息历史记录
        self._message_history = deque(maxlen=1000)  # 最多保存1000条消息历史
        
        # 消息处理任务
        self._message_processor_task = None
        
        # 心跳监控任务
        self._heartbeat_monitor_task = None
        
        # 消息清理任务
        self._message_cleanup_task = None
        
        # 运行状态
        self._is_running = False
        
        # 直接订阅（按代理ID订阅）
        self._direct_subscribers = defaultdict(set)  # {agent_id: {callback1, callback2, ...}}
        
        # 主题订阅
        self._topic_subscribers = defaultdict(set)  # {topic: {callback1, callback2, ...}}
        
        # 类型订阅
        self._type_subscribers = defaultdict(set)  # {message_type: {callback1, callback2, ...}}
        
        # 响应等待
        self._response_waiters = {}  # {message_id: asyncio.Future}
        
        # 代理心跳状态
        self._agent_heartbeats = {}  # {agent_id: {"last_heartbeat": timestamp, "status": status, "load": load}}
        
        # 性能指标
        self._metrics = {
            "messages_processed": 0,
            "messages_published": 0,
            "messages_failed": 0,
            "average_processing_time_ms": 0,
            "total_processing_time_ms": 0,
            "queue_size": 0
        }

    async def start(self):
        """启动消息总线"""
        if self._is_running:
            self.logger.warning("消息总线已经在运行中")
            return

        self.logger.info("启动消息总线")
        self._is_running = True
        
        # 启动消息处理任务
        self._message_processor_task = asyncio.create_task(self._process_messages())
        
        # 启动心跳监控任务
        self._heartbeat_monitor_task = asyncio.create_task(self._monitor_agent_heartbeats())
        
        # 启动消息清理任务
        self._message_cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
        
        self.logger.info("消息总线启动完成")

    async def stop(self):
        """停止消息总线"""
        if not self._is_running:
            self.logger.warning("消息总线未在运行")
            return

        self.logger.info("停止消息总线")
        self._is_running = False
        
        # 取消所有等待的响应
        for future in self._response_waiters.values():
            if not future.done():
                future.cancel()
        
        # 取消消息处理任务
        if self._message_processor_task:
            self._message_processor_task.cancel()
            try:
                await self._message_processor_task
            except asyncio.CancelledError:
                pass
        
        # 取消心跳监控任务
        if self._heartbeat_monitor_task:
            self._heartbeat_monitor_task.cancel()
            try:
                await self._heartbeat_monitor_task
            except asyncio.CancelledError:
                pass
        
        # 取消消息清理任务
        if self._message_cleanup_task:
            self._message_cleanup_task.cancel()
            try:
                await self._message_cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("消息总线已停止")

    async def publish(self, message: MCPMessage) -> str:
        """发布消息到总线"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        # 记录消息到历史
        self._message_history.append(message)
        
        # 更新指标
        self._metrics["messages_published"] += 1
        self._metrics["queue_size"] = self._message_queue.qsize()
        
        # 如果是心跳消息，更新代理心跳状态
        if message.header.message_type == MCPMessageType.HEARTBEAT:
            self._update_agent_heartbeat(message)
        
        # 如果是响应或错误消息，检查是否有等待的请求
        if message.header.message_type in [MCPMessageType.RESPONSE, MCPMessageType.ERROR]:
            correlation_id = message.header.correlation_id
            if correlation_id and correlation_id in self._response_waiters:
                future = self._response_waiters[correlation_id]
                if not future.done():
                    future.set_result(message)
                    return message.header.message_id
        
        # 将消息放入队列
        await self._message_queue.put(message)
        
        return message.header.message_id

    async def subscribe_direct(self, agent_id: str, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """订阅发送给特定代理ID的消息"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        self._direct_subscribers[agent_id].add(callback)
        self.logger.debug(f"代理 {agent_id} 添加了直接订阅，当前订阅者数量: {len(self._direct_subscribers[agent_id])}")

    async def unsubscribe_direct(self, agent_id: str, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """取消订阅发送给特定代理ID的消息"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        if agent_id in self._direct_subscribers and callback in self._direct_subscribers[agent_id]:
            self._direct_subscribers[agent_id].remove(callback)
            self.logger.debug(f"代理 {agent_id} 移除了直接订阅，当前订阅者数量: {len(self._direct_subscribers[agent_id])}")
            
            # 如果没有订阅者了，清理该代理的订阅集合
            if not self._direct_subscribers[agent_id]:
                del self._direct_subscribers[agent_id]

    async def subscribe_topic(self, topic: str, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """订阅特定主题的消息"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        self._topic_subscribers[topic].add(callback)
        self.logger.debug(f"主题 {topic} 添加了订阅，当前订阅者数量: {len(self._topic_subscribers[topic])}")

    async def unsubscribe_topic(self, topic: str, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """取消订阅特定主题的消息"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        if topic in self._topic_subscribers and callback in self._topic_subscribers[topic]:
            self._topic_subscribers[topic].remove(callback)
            self.logger.debug(f"主题 {topic} 移除了订阅，当前订阅者数量: {len(self._topic_subscribers[topic])}")
            
            # 如果没有订阅者了，清理该主题的订阅集合
            if not self._topic_subscribers[topic]:
                del self._topic_subscribers[topic]

    async def subscribe_type(self, message_type: MCPMessageType, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """订阅特定类型的消息"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        self._type_subscribers[message_type].add(callback)
        self.logger.debug(f"消息类型 {message_type} 添加了订阅，当前订阅者数量: {len(self._type_subscribers[message_type])}")

    async def unsubscribe_type(self, message_type: MCPMessageType, callback: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """取消订阅特定类型的消息"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        if message_type in self._type_subscribers and callback in self._type_subscribers[message_type]:
            self._type_subscribers[message_type].remove(callback)
            self.logger.debug(f"消息类型 {message_type} 移除了订阅，当前订阅者数量: {len(self._type_subscribers[message_type])}")
            
            # 如果没有订阅者了，清理该类型的订阅集合
            if not self._type_subscribers[message_type]:
                del self._type_subscribers[message_type]

    async def wait_for_response(
        self, 
        message_id: str, 
        timeout: float = 60.0,
        expected_source: Optional[str] = None
    ) -> Optional[MCPMessage]:
        """等待特定消息的响应"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        # 创建Future对象
        future = asyncio.Future()
        self._response_waiters[message_id] = future
        
        try:
            # 等待响应，带超时
            response = await asyncio.wait_for(future, timeout)
            
            # 如果指定了期望的源，检查响应是否来自该源
            if expected_source and response.header.source != expected_source:
                self.logger.warning(f"收到的响应来源 {response.header.source} 与期望的来源 {expected_source} 不匹配")
                return None
            
            return response
        except asyncio.TimeoutError:
            self.logger.warning(f"等待消息 {message_id} 的响应超时")
            return None
        finally:
            # 清理等待器
            if message_id in self._response_waiters:
                del self._response_waiters[message_id]

    def get_message_history(
        self, 
        limit: Optional[int] = None, 
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        message_type: Optional[MCPMessageType] = None
    ) -> List[MCPMessage]:
        """获取消息历史"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        # 过滤消息历史
        filtered_history = list(self._message_history)
        
        # 按代理ID过滤
        if agent_id:
            filtered_history = [
                msg for msg in filtered_history 
                if msg.header.source == agent_id or msg.header.target == agent_id
            ]
        
        # 按会话ID过滤
        if session_id:
            filtered_history = [
                msg for msg in filtered_history 
                if msg.header.session_id == session_id
            ]
        
        # 按消息类型过滤
        if message_type:
            filtered_history = [
                msg for msg in filtered_history 
                if msg.header.message_type == message_type
            ]
        
        # 限制返回数量
        if limit and limit > 0:
            filtered_history = filtered_history[-limit:]
        
        return filtered_history

    def get_message_by_id(self, message_id: str) -> Optional[MCPMessage]:
        """根据消息ID获取消息"""
        for message in self._message_history:
            if message.header.message_id == message_id:
                return message
        return None

    def get_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """获取代理状态"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        if agent_id:
            # 返回特定代理的状态
            if agent_id in self._agent_heartbeats:
                return self._agent_heartbeats[agent_id]
            else:
                return {"status": "unknown", "last_heartbeat": None, "load": None}
        else:
            # 返回所有代理的状态
            return self._agent_heartbeats

    def get_metrics(self) -> Dict[str, Any]:
        """获取消息总线性能指标"""
        if not self._is_running:
            raise RuntimeError("消息总线未启动")
        
        # 更新队列大小
        self._metrics["queue_size"] = self._message_queue.qsize()
        
        # 计算平均处理时间
        if self._metrics["messages_processed"] > 0:
            self._metrics["average_processing_time_ms"] = (
                self._metrics["total_processing_time_ms"] / self._metrics["messages_processed"]
            )
        
        # 返回指标副本
        return dict(self._metrics)

    async def _process_messages(self):
        """处理消息队列中的消息"""
        self.logger.info("消息处理任务启动")
        
        while self._is_running:
            try:
                # 从队列中获取消息
                message = await self._message_queue.get()
                
                # 记录处理开始时间
                start_time = time.time()
                
                # 更新消息状态为处理中
                message.header.status = MCPStatus.PROCESSING
                
                # 获取目标代理ID
                target = message.header.target
                
                # 获取消息类型
                message_type = message.header.message_type
                
                # 查找订阅者
                subscribers = set()
                
                # 1. 直接订阅者
                if target in self._direct_subscribers:
                    subscribers.update(self._direct_subscribers[target])
                
                # 2. 主题订阅者（如果目标是主题）
                if target.startswith("topic.") and target[6:] in self._topic_subscribers:
                    subscribers.update(self._topic_subscribers[target[6:]])
                
                # 3. 类型订阅者
                if message_type in self._type_subscribers:
                    subscribers.update(self._type_subscribers[message_type])
                
                # 如果没有订阅者，记录警告
                if not subscribers:
                    self.logger.warning(f"消息 {message.header.message_id} 没有订阅者: {target}, {message_type}")
                    # 更新消息状态为失败
                    message.header.status = MCPStatus.FAILED
                    self._metrics["messages_failed"] += 1
                else:
                    # 分发消息给所有订阅者
                    delivery_tasks = []
                    for subscriber in subscribers:
                        delivery_tasks.append(self._deliver_message(subscriber, message))
                    
                    # 等待所有分发任务完成
                    if delivery_tasks:
                        await asyncio.gather(*delivery_tasks, return_exceptions=True)
                    
                    # 更新消息状态为已完成
                    message.header.status = MCPStatus.COMPLETED
                
                # 记录处理结束时间并更新指标
                end_time = time.time()
                processing_time_ms = (end_time - start_time) * 1000
                
                self._metrics["messages_processed"] += 1
                self._metrics["total_processing_time_ms"] += processing_time_ms
                self._metrics["queue_size"] = self._message_queue.qsize()
                
                # 标记任务完成
                self._message_queue.task_done()
                
            except asyncio.CancelledError:
                self.logger.info("消息处理任务被取消")
                break
            except Exception as e:
                self.logger.error(f"处理消息时发生错误: {str(e)}", exc_info=True)
                self._metrics["messages_failed"] += 1
        
        self.logger.info("消息处理任务结束")

    async def _deliver_message(self, subscriber: Callable[[MCPMessage], Awaitable[None]], message: MCPMessage):
        """将消息分发给订阅者"""
        try:
            await subscriber(message)
        except Exception as e:
            self.logger.error(f"分发消息 {message.header.message_id} 给订阅者时发生错误: {str(e)}", exc_info=True)

    def _update_agent_heartbeat(self, message: MCPMessage):
        """更新代理心跳状态"""
        if message.header.message_type != MCPMessageType.HEARTBEAT:
            return
        
        agent_id = message.header.source
        status = message.body.status if hasattr(message.body, "status") else "active"
        load = message.body.load if hasattr(message.body, "load") else None
        
        self._agent_heartbeats[agent_id] = {
            "last_heartbeat": datetime.now(),
            "status": status,
            "load": load
        }

    async def _monitor_agent_heartbeats(self):
        """监控代理心跳，检测离线代理"""
        self.logger.info("心跳监控任务启动")
        
        # 心跳超时时间（秒）
        heartbeat_timeout = 30
        
        while self._is_running:
            try:
                # 当前时间
                now = datetime.now()
                
                # 检查所有代理的心跳
                offline_agents = []
                for agent_id, heartbeat_info in list(self._agent_heartbeats.items()):
                    last_heartbeat = heartbeat_info["last_heartbeat"]
                    
                    # 如果心跳超时，标记代理为离线
                    if (now - last_heartbeat).total_seconds() > heartbeat_timeout:
                        if heartbeat_info["status"] != "offline":
                            self.logger.warning(f"代理 {agent_id} 心跳超时，标记为离线")
                            heartbeat_info["status"] = "offline"
                            offline_agents.append(agent_id)
                
                # 如果有代理离线，发布代理离线事件
                for agent_id in offline_agents:
                    # 这里可以发布代理离线事件，但需要避免循环依赖
                    pass
                
                # 等待一段时间再检查
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                self.logger.info("心跳监控任务被取消")
                break
            except Exception as e:
                self.logger.error(f"监控代理心跳时发生错误: {str(e)}", exc_info=True)
                await asyncio.sleep(5)
        
        self.logger.info("心跳监控任务结束")

    def _cleanup_expired_messages(self):
        """清理过期的消息"""
        self.logger.info("消息清理任务启动")
        
        while self._is_running:
            try:
                # 当前时间
                now = datetime.now()
                
                # 清理过期的消息
                for message in list(self._message_history):
                    # 如果消息有TTL
                    if message.header.ttl:
                        # 计算消息过期时间
                        expiry_time = message.header.timestamp + timedelta(seconds=message.header.ttl)
                        
                        # 如果消息已过期，从历史记录中移除
                        if now > expiry_time:
                            self._message_history.remove(message)
                
                # 等待一段时间再清理
                time.sleep(60)  # 每分钟清理一次
                
            except Exception as e:
                self.logger.error(f"清理过期消息时发生错误: {str(e)}", exc_info=True)
                time.sleep(60)
        
        self.logger.info("消息清理任务结束")


# 全局消息总线实例
message_bus = MCPMessageBus()