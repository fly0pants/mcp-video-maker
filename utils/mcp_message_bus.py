import asyncio
import logging
import time
from typing import Dict, List, Set, Callable, Awaitable, Optional, Any, Union
from datetime import datetime
import uuid
import random

from models.mcp import (
    MCPMessage, MCPHeader, MCPMessageType, MCPStatus, MCPPriority,
    MCPResponse, MCPError, MCPHeartbeat, MCPEvent,
    create_command_message, create_event_message
)
from utils.mcp_message_persistence import MCPMessagePersistence, default_persistence
from utils.rate_limiter import global_rate_limiter


class MCPMessageBus:
    """MCP协议消息总线，用于多代理系统间通信"""

    def __init__(self, persistence: Optional[MCPMessagePersistence] = None):
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
        self._max_history_size = 1000  # 最大历史记录数量
        
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
            "start_time": time.time(),
            "persistence_success": 0,
            "persistence_failure": 0
        }
        
        # 消息持久化
        self._persistence = persistence or default_persistence
        
        # 消息清理任务
        self._cleanup_task = None
        self._cleanup_interval = 3600  # 每小时清理一次
        
        # 断路器状态
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # 消息去重集合
        self._processed_idempotency_keys: Set[str] = set()
        self._idempotency_key_ttl = 3600  # 幂等键的生存时间（秒）
        
        # 限流器
        self._rate_limiters: Dict[str, Dict[str, Any]] = {}

    async def start(self):
        """启动消息总线"""
        if self._is_running:
            return
        
        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_messages())
        self._heartbeat_monitoring_task = asyncio.create_task(self._monitor_agent_heartbeats())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
        
        # 恢复未处理的持久化消息
        await self._recover_persisted_messages()
        
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
            
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            
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
            
        # 应用速率限制
        if message.header.message_type == MCPMessageType.COMMAND:
            # 为每个目标代理创建一个限流桶
            rate_key = f"target_{message.header.target}"
            
            # 根据优先级分配不同的令牌消耗量
            token_cost = 1.0
            if message.header.priority == MCPPriority.LOW:
                token_cost = 2.0  # 低优先级消息消耗更多令牌
            elif message.header.priority == MCPPriority.HIGH:
                token_cost = 0.5  # 高优先级消息消耗更少令牌
            elif message.header.priority == MCPPriority.CRITICAL:
                token_cost = 0.1  # 关键消息几乎不受限制
            
            # 检查目标代理的负载情况，动态调整速率
            if message.header.target in self._agent_heartbeats:
                agent_load = self._agent_heartbeats[message.header.target].get("load", 0.5)
                
                # 根据负载调整速率：负载越高，速率越低
                base_rate = 50.0  # 基础速率：每秒50个请求
                adjusted_rate = base_rate * (1.0 - 0.8 * agent_load)  # 负载为1时降至基础速率的20%
                
                # 更新限流器速率
                global_rate_limiter.update_rate(rate_key, adjusted_rate)
            
            # 等待获取令牌，超时时间根据优先级设置
            timeout = None
            if message.header.priority == MCPPriority.LOW:
                timeout = 10.0  # 低优先级消息最多等待10秒
            elif message.header.priority == MCPPriority.NORMAL:
                timeout = 30.0  # 普通优先级消息最多等待30秒
            
            # 尝试获取令牌
            if not await global_rate_limiter.wait_for_tokens(rate_key, token_cost, timeout):
                # 如果获取令牌超时，创建限流错误响应
                self.logger.warning(f"Rate limit applied for message to {message.header.target}")
                
                # 创建错误响应
                error_response = MCPMessage(
                    header=MCPHeader(
                        source="system",
                        target=message.header.source,
                        message_type=MCPMessageType.ERROR,
                        correlation_id=message.header.message_id
                    ),
                    body=MCPError(
                        error_code="RATE_LIMITED",
                        error_message=f"Request rate limited due to high load on {message.header.target}",
                        retry_possible=True,
                        category="TEMPORARY",
                        retry_delay_ms=5000,  # 建议5秒后重试
                        error_severity="WARNING"
                    )
                )
                
                # 将错误响应放入队列
                await self._message_queue.put(error_response)
                return message.header.message_id
        
        # 检查幂等性键，避免重复处理
        if hasattr(message.body, 'idempotency_key') and message.body.idempotency_key:
            idempotency_key = message.body.idempotency_key
            if idempotency_key in self._processed_idempotency_keys:
                self.logger.info(f"Duplicate message with idempotency key {idempotency_key} ignored")
                return message.header.message_id
            
            # 添加到已处理集合
            self._processed_idempotency_keys.add(idempotency_key)
            
        # 检查断路器状态
        if message.header.message_type == MCPMessageType.COMMAND:
            circuit_key = f"{message.header.source}_{message.header.target}"
            if circuit_key in self._circuit_breakers:
                circuit = self._circuit_breakers[circuit_key]
                if circuit["status"] == "OPEN":
                    # 断路器开启，拒绝请求
                    self.logger.warning(f"Circuit breaker open for {circuit_key}, rejecting command")
                    
                    # 创建错误响应
                    error_response = MCPMessage(
                        header=MCPHeader(
                            source="system",
                            target=message.header.source,
                            message_type=MCPMessageType.ERROR,
                            correlation_id=message.header.message_id
                        ),
                        body=MCPError(
                            error_code="CIRCUIT_OPEN",
                            error_message=f"Circuit breaker open for {message.header.target}",
                            retry_possible=True,
                            category="TEMPORARY",
                            retry_delay_ms=circuit["reset_timeout_ms"]
                        )
                    )
                    
                    # 将错误响应放入队列
                    await self._message_queue.put(error_response)
                    return message.header.message_id
                elif circuit["status"] == "HALF_OPEN":
                    # 半开状态，随机允许部分请求通过
                    if random.random() > 0.2:  # 允许20%的请求通过
                        self.logger.info(f"Circuit half-open for {circuit_key}, testing with this request")
                    else:
                        self.logger.info(f"Circuit half-open for {circuit_key}, rejecting this request")
                        
                        # 创建错误响应
                        error_response = MCPMessage(
                            header=MCPHeader(
                                source="system",
                                target=message.header.source,
                                message_type=MCPMessageType.ERROR,
                                correlation_id=message.header.message_id
                            ),
                            body=MCPError(
                                error_code="CIRCUIT_HALF_OPEN",
                                error_message=f"Circuit breaker half-open for {message.header.target}",
                                retry_possible=True,
                                category="TEMPORARY",
                                retry_delay_ms=1000
                            )
                        )
                        
                        # 将错误响应放入队列
                        await self._message_queue.put(error_response)
                        return message.header.message_id
        
        # 检查是否需要持久化
        should_persist = False
        
        # 根据消息优先级和类型决定是否持久化
        if message.header.priority in [MCPPriority.HIGH, MCPPriority.CRITICAL]:
            should_persist = True
        elif message.header.message_type in [MCPMessageType.COMMAND, MCPMessageType.STATE_UPDATE]:
            should_persist = True
        
        # 执行持久化
        if should_persist:
            persist_success = await self._persistence.save_message(message)
            if persist_success:
                self._metrics["persistence_success"] += 1
            else:
                self._metrics["persistence_failure"] += 1
                self.logger.warning(f"Failed to persist message {message.header.message_id}")
            
        # 添加到历史记录和映射
        self._message_history.append(message)
        self._message_map[message.header.message_id] = message
        
        # 如果历史记录过长，移除最旧的消息
        if len(self._message_history) > self._max_history_size:
            old_message = self._message_history.pop(0)
            if old_message.header.message_id in self._message_map:
                del self._message_map[old_message.header.message_id]
        
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

    async def _recover_persisted_messages(self):
        """恢复未处理的持久化消息"""
        try:
            # 获取所有未处理的消息
            message_ids = await self._persistence.list_messages()
            
            if message_ids:
                self.logger.info(f"Recovering {len(message_ids)} persisted messages")
                
                for message_id in message_ids:
                    message = await self._persistence.load_message(message_id)
                    if message:
                        # 将消息放入队列
                        self._message_map[message_id] = message
                        self._message_history.append(message)
                        await self._message_queue.put(message)
                        
                        self.logger.debug(f"Recovered message {message_id}")
                    else:
                        self.logger.warning(f"Failed to recover message {message_id}")
        except Exception as e:
            self.logger.error(f"Error recovering persisted messages: {str(e)}")

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
                    
                    # 如果是错误响应，更新断路器状态
                    if message.header.message_type == MCPMessageType.ERROR:
                        circuit_key = f"{message.header.target}_{message.header.source}"
                        if circuit_key in self._circuit_breakers:
                            circuit = self._circuit_breakers[circuit_key]
                            
                            # 增加失败计数
                            circuit["failure_count"] += 1
                            
                            # 检查是否需要打开断路器
                            if circuit["status"] == "CLOSED" and circuit["failure_count"] >= circuit["threshold"]:
                                circuit["status"] = "OPEN"
                                circuit["last_error"] = message.body.error_code if hasattr(message.body, 'error_code') else "UNKNOWN"
                                circuit["open_time"] = time.time()
                                self.logger.warning(f"Circuit breaker opened for {circuit_key} due to {circuit['failure_count']} failures")
                        else:
                            # 创建新的断路器
                            self._circuit_breakers[circuit_key] = {
                                "status": "CLOSED",
                                "failure_count": 1,
                                "success_count": 0,
                                "threshold": 5,  # 5次失败后打开断路器
                                "reset_timeout_ms": 30000,  # 30秒后尝试半开
                                "last_error": message.body.error_code if hasattr(message.body, 'error_code') else "UNKNOWN",
                                "open_time": None
                            }
                
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
                
                # 如果消息已持久化，标记为已处理
                if message.header.priority in [MCPPriority.HIGH, MCPPriority.CRITICAL] or \
                   message.header.message_type in [MCPMessageType.COMMAND, MCPMessageType.STATE_UPDATE]:
                    await self._persistence.mark_as_processed(message.header.message_id)
                
                # 如果是成功响应，更新断路器状态
                if message.header.message_type == MCPMessageType.RESPONSE:
                    response_body = message.body
                    if isinstance(response_body, MCPResponse) and response_body.success:
                        circuit_key = f"{message.header.target}_{message.header.source}"
                        if circuit_key in self._circuit_breakers:
                            circuit = self._circuit_breakers[circuit_key]
                            
                            # 增加成功计数
                            circuit["success_count"] += 1
                            
                            # 如果断路器处于半开状态，检查是否可以关闭
                            if circuit["status"] == "HALF_OPEN" and circuit["success_count"] >= 3:
                                circuit["status"] = "CLOSED"
                                circuit["failure_count"] = 0
                                circuit["success_count"] = 0
                                self.logger.info(f"Circuit breaker closed for {circuit_key} after successful tests")
                
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
        """更新代理心跳信息"""
        if isinstance(message.body, MCPHeartbeat):
            agent_id = message.body.agent_id
            
            self._agent_heartbeats[agent_id] = {
                "last_heartbeat": time.time(),
                "status": message.body.status,
                "load": message.body.load,
                "uptime_seconds": message.body.uptime_seconds,
                "version": message.body.version
            }

    async def _monitor_agent_heartbeats(self):
        """监控代理心跳，检测离线代理"""
        heartbeat_timeout = 90  # 90秒无心跳视为离线
        check_interval = 30  # 每30秒检查一次
        
        while self._is_running:
            try:
                current_time = time.time()
                offline_agents = []
                
                # 检查所有代理的心跳
                for agent_id, info in self._agent_heartbeats.items():
                    last_heartbeat = info["last_heartbeat"]
                    
                    # 如果超过超时时间没有心跳，标记为离线
                    if current_time - last_heartbeat > heartbeat_timeout:
                        offline_agents.append(agent_id)
                        
                        # 更新状态为离线
                        self._agent_heartbeats[agent_id]["status"] = "offline"
                        
                        self.logger.warning(f"Agent {agent_id} appears to be offline (no heartbeat for {int(current_time - last_heartbeat)}s)")
                
                # 发布代理离线事件
                for agent_id in offline_agents:
                    offline_event = create_event_message(
                        source="system",
                        target="broadcast",
                        event_type="agent.offline",
                        data={
                            "agent_id": agent_id,
                            "timestamp": datetime.now().isoformat(),
                            "reason": "heartbeat_timeout"
                        }
                    )
                    await self.publish(offline_event)
                
                # 等待下一次检查
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring agent heartbeats: {str(e)}")
                await asyncio.sleep(5)  # 出错后短暂等待再重试

    async def _cleanup_expired_messages(self):
        """清理过期消息和幂等键"""
        while self._is_running:
            try:
                # 清理过期的幂等键
                current_time = time.time()
                expired_keys = set()
                
                # 这里应该有一个时间戳映射，但为简化实现，我们暂时不做
                # 在实际实现中，应该为每个幂等键记录添加时间
                # 这里简单地每小时清空一次
                self._processed_idempotency_keys.clear()
                
                # 检查断路器状态
                for circuit_key, circuit in list(self._circuit_breakers.items()):
                    if circuit["status"] == "OPEN" and circuit["open_time"]:
                        # 检查是否应该进入半开状态
                        if current_time - circuit["open_time"] > (circuit["reset_timeout_ms"] / 1000):
                            circuit["status"] = "HALF_OPEN"
                            circuit["success_count"] = 0
                            self.logger.info(f"Circuit breaker for {circuit_key} changed from OPEN to HALF_OPEN")
                
                # 等待下一次清理
                await asyncio.sleep(self._cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error cleaning up expired messages: {str(e)}")
                await asyncio.sleep(60)  # 出错后等待一分钟再重试

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
            "agents_online": sum(1 for status in self._agent_heartbeats.values() if status.get("status") == "active"),
            "persistence_success": self._metrics["persistence_success"],
            "persistence_failure": self._metrics["persistence_failure"]
        }

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


# 全局MCP消息总线实例
mcp_message_bus = MCPMessageBus() 