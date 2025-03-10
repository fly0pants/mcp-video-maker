import asyncio
import uuid
from typing import Dict, List, Any, Callable, Awaitable, Optional, Set
from models.message import Message, MessageType, MessageStatus, AgentType


class MessageBus:
    """消息总线，用于代理之间的异步通信"""

    def __init__(self):
        self._subscribers: Dict[AgentType, Set[Callable[[Message], Awaitable[None]]]] = {
            agent_type: set() for agent_type in AgentType
        }
        self._message_queue = asyncio.Queue()
        self._message_history: List[Message] = []
        self._is_running = False
        self._processing_task = None

    async def publish(self, message: Message) -> str:
        """发布消息到总线"""
        # 生成消息ID（如果没有）
        if not message.id:
            message.id = f"msg_{uuid.uuid4().hex[:10]}"
            
        # 保存到历史记录
        self._message_history.append(message)
        
        # 放入队列
        await self._message_queue.put(message)
        
        # 确保处理循环正在运行
        if not self._is_running:
            await self.start_processing()
            
        return message.id

    async def start_processing(self):
        """启动消息处理循环"""
        if self._is_running:
            return
            
        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_messages())

    async def stop_processing(self):
        """停止消息处理循环"""
        if not self._is_running:
            return
            
        self._is_running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None

    async def _process_messages(self):
        """消息处理循环"""
        while self._is_running:
            try:
                message = await self._message_queue.get()
                
                # 更新消息状态
                message.status = MessageStatus.PROCESSING
                
                # 获取接收方的订阅者
                subscribers = self._subscribers.get(message.receiver, set())
                
                # 分发消息
                delivery_tasks = []
                for subscriber in subscribers:
                    delivery_tasks.append(asyncio.create_task(subscriber(message)))
                
                # 等待所有订阅者处理完毕
                if delivery_tasks:
                    await asyncio.gather(*delivery_tasks, return_exceptions=True)
                    
                # 标记消息为已完成
                message.status = MessageStatus.COMPLETED
                
                # 标记任务完成
                self._message_queue.task_done()
            except Exception as e:
                print(f"Error processing message: {e}")

    async def subscribe(self, agent_type: AgentType, callback: Callable[[Message], Awaitable[None]]):
        """订阅特定类型代理的消息"""
        self._subscribers[agent_type].add(callback)

    async def unsubscribe(self, agent_type: AgentType, callback: Callable[[Message], Awaitable[None]]):
        """取消订阅特定类型代理的消息"""
        if callback in self._subscribers[agent_type]:
            self._subscribers[agent_type].remove(callback)

    def get_message_history(self, limit: int = None, agent_type: AgentType = None) -> List[Message]:
        """获取消息历史"""
        filtered_messages = self._message_history
        
        # 按代理类型筛选
        if agent_type:
            filtered_messages = [
                msg for msg in filtered_messages 
                if msg.sender == agent_type or msg.receiver == agent_type
            ]
        
        # 限制返回数量
        if limit and limit > 0:
            filtered_messages = filtered_messages[-limit:]
            
        return filtered_messages

    async def wait_for_response(self, 
                                parent_message_id: str, 
                                timeout: float = 60.0,
                                expected_sender: Optional[AgentType] = None) -> Optional[Message]:
        """等待特定消息的响应"""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # 检查现有消息历史中是否已有回复
            for msg in reversed(self._message_history):
                if (msg.parent_id == parent_message_id and 
                    (expected_sender is None or msg.sender == expected_sender) and
                    msg.type == MessageType.RESPONSE):
                    return msg
            
            # 等待一段时间再检查
            await asyncio.sleep(0.5)
        
        # 超时返回None
        return None

    def create_message(self, 
                       sender: AgentType, 
                       receiver: AgentType, 
                       content: Dict[str, Any], 
                       message_type: MessageType = MessageType.COMMAND,
                       parent_id: Optional[str] = None) -> Message:
        """创建一个新消息"""
        return Message(
            id=f"msg_{uuid.uuid4().hex[:10]}",
            type=message_type,
            status=MessageStatus.PENDING,
            sender=sender,
            receiver=receiver,
            content=content,
            parent_id=parent_id
        )


# 全局消息总线实例
message_bus = MessageBus() 