import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable, Awaitable
from abc import ABC, abstractmethod

from models.message import Message, MessageType, MessageStatus, AgentType, AgentResponse
from utils.message_bus import message_bus
from utils.logger import AgentLogger


class BaseAgent(ABC):
    """所有代理的抽象基类，定义共同的接口和基本功能"""
    
    def __init__(self, agent_type: AgentType, name: str):
        """
        初始化代理
        
        Args:
            agent_type: 代理类型
            name: 代理名称
        """
        self.agent_type = agent_type
        self.name = name
        self.id = f"{agent_type.value}_{uuid.uuid4().hex[:6]}"
        self.logger = AgentLogger(f"{agent_type.value}_{name}")
        self.message_handlers: Dict[MessageType, Callable[[Message], Awaitable[Optional[Message]]]] = {}
        self.is_initialized = False
        self._message_callback_registered = False
        
        # 注册消息处理器
        self._register_message_handlers()
        
    async def initialize(self):
        """初始化代理，包括订阅消息总线"""
        if not self._message_callback_registered:
            await message_bus.subscribe(self.agent_type, self._message_callback)
            self._message_callback_registered = True
            
        self.is_initialized = True
        self.logger.info(f"Agent {self.name} ({self.id}) initialized")
        
    async def shutdown(self):
        """关闭代理，清理资源"""
        if self._message_callback_registered:
            await message_bus.unsubscribe(self.agent_type, self._message_callback)
            self._message_callback_registered = False
            
        self.is_initialized = False
        self.logger.info(f"Agent {self.name} ({self.id}) shutdown")
    
    def _register_message_handlers(self):
        """注册不同类型消息的处理器"""
        self.message_handlers[MessageType.COMMAND] = self.handle_command
        self.message_handlers[MessageType.RESPONSE] = self.handle_response
        self.message_handlers[MessageType.DATA] = self.handle_data
        self.message_handlers[MessageType.STATUS] = self.handle_status
        self.message_handlers[MessageType.ERROR] = self.handle_error
        self.message_handlers[MessageType.QUESTION] = self.handle_question
    
    async def _message_callback(self, message: Message):
        """
        消息总线回调函数，根据消息类型分发到不同的处理器
        
        Args:
            message: 接收到的消息
        """
        self.logger.debug(f"Received message: {message.id} of type {message.type} from {message.sender}")
        
        handler = self.message_handlers.get(message.type)
        if handler:
            try:
                response = await handler(message)
                if response:
                    # 发送响应消息回去
                    await message_bus.publish(response)
            except Exception as e:
                self.logger.error(f"Error handling message {message.id}: {str(e)}")
                # 发送错误响应
                error_response = message_bus.create_message(
                    sender=self.agent_type,
                    receiver=message.sender,
                    content={"error": str(e)},
                    message_type=MessageType.ERROR,
                    parent_id=message.id
                )
                await message_bus.publish(error_response)
        else:
            self.logger.warning(f"No handler registered for message type: {message.type}")
    
    async def send_message(self, 
                          to_agent: AgentType, 
                          content: Dict[str, Any], 
                          message_type: MessageType = MessageType.COMMAND,
                          parent_id: Optional[str] = None) -> str:
        """
        发送消息到另一个代理
        
        Args:
            to_agent: 接收消息的代理类型
            content: 消息内容
            message_type: 消息类型
            parent_id: 父消息ID（对于回复）
            
        Returns:
            消息ID
        """
        message = message_bus.create_message(
            sender=self.agent_type,
            receiver=to_agent,
            content=content,
            message_type=message_type,
            parent_id=parent_id
        )
        
        message_id = await message_bus.publish(message)
        self.logger.debug(f"Sent message {message_id} to {to_agent}")
        return message_id
    
    async def wait_for_response(self, 
                               message_id: str, 
                               timeout: float = 60.0,
                               from_agent: Optional[AgentType] = None) -> Optional[Message]:
        """
        等待特定消息的响应
        
        Args:
            message_id: 原始消息ID
            timeout: 超时时间（秒）
            from_agent: 期望回复的代理类型
            
        Returns:
            响应消息，如果超时则返回None
        """
        return await message_bus.wait_for_response(
            parent_message_id=message_id,
            timeout=timeout,
            expected_sender=from_agent
        )
    
    @abstractmethod
    async def handle_command(self, message: Message) -> Optional[Message]:
        """
        处理命令类型的消息
        
        Args:
            message: 命令消息
            
        Returns:
            可选的响应消息
        """
        pass
    
    async def handle_response(self, message: Message) -> Optional[Message]:
        """处理响应类型的消息"""
        # 默认实现只记录日志，子类可以覆盖
        self.logger.debug(f"Received response message {message.id} from {message.sender}")
        return None
    
    async def handle_data(self, message: Message) -> Optional[Message]:
        """处理数据类型的消息"""
        # 默认实现只记录日志，子类可以覆盖
        self.logger.debug(f"Received data message {message.id} from {message.sender}")
        return None
    
    async def handle_status(self, message: Message) -> Optional[Message]:
        """处理状态类型的消息"""
        # 默认实现只记录日志，子类可以覆盖
        self.logger.debug(f"Received status message {message.id} from {message.sender}")
        return None
    
    async def handle_error(self, message: Message) -> Optional[Message]:
        """处理错误类型的消息"""
        # 默认实现只记录日志，子类可以覆盖
        self.logger.error(f"Received error message {message.id} from {message.sender}: {message.content.get('error', 'Unknown error')}")
        return None
    
    async def handle_question(self, message: Message) -> Optional[Message]:
        """处理问题类型的消息"""
        # 默认实现只记录日志并返回默认响应，子类应该覆盖
        self.logger.warning(f"Received question message {message.id} from {message.sender}, but no handler implemented")
        
        # 返回默认响应
        return message_bus.create_message(
            sender=self.agent_type,
            receiver=message.sender,
            content={"answer": "I don't know how to answer this question."},
            message_type=MessageType.RESPONSE,
            parent_id=message.id
        )
    
    def create_success_response(self, message: Message, data: Dict[str, Any] = None) -> Message:
        """创建成功响应消息"""
        content = {
            "success": True,
            "message": "Operation completed successfully"
        }
        
        if data:
            content["data"] = data
            
        return message_bus.create_message(
            sender=self.agent_type,
            receiver=message.sender,
            content=content,
            message_type=MessageType.RESPONSE,
            parent_id=message.id
        )
    
    def create_error_response(self, message: Message, error_message: str) -> Message:
        """创建错误响应消息"""
        return message_bus.create_message(
            sender=self.agent_type,
            receiver=message.sender,
            content={
                "success": False,
                "error": error_message
            },
            message_type=MessageType.ERROR,
            parent_id=message.id
        )
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """获取代理状态信息"""
        return {
            "id": self.id,
            "type": self.agent_type,
            "name": self.name,
            "is_initialized": self.is_initialized,
            "status": "active" if self.is_initialized else "inactive"
        } 