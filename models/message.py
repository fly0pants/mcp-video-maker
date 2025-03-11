from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class MessageType(str, Enum):
    """消息类型枚举"""
    COMMAND = "command"  # 指令消息
    RESPONSE = "response"  # 响应消息
    DATA = "data"  # 数据消息
    ERROR = "error"  # 错误消息
    STATUS = "status"  # 状态更新消息
    QUESTION = "question"  # 询问用户的消息


class MessageStatus(str, Enum):
    """消息状态枚举"""
    PENDING = "pending"  # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    WAITING_USER = "waiting_user"  # 等待用户输入


class AgentType(str, Enum):
    """代理类型枚举"""
    CENTRAL = "central"  # 中央策略代理
    CONTENT = "content"  # 内容创作代理
    VISUAL = "visual"  # 视觉生成代理
    AUDIO = "audio"  # 语音与音乐代理
    POSTPROD = "postprod"  # 后期制作代理
    DISTRIBUTION = "distribution"  # 分发代理
    STORYBOARD = "storyboard"  # 分镜代理
    USER = "user"  # 用户


class Message(BaseModel):
    """代理间通信的消息模型"""
    id: str = Field(..., description="消息的唯一标识符")
    type: MessageType = Field(..., description="消息类型")
    status: MessageStatus = Field(MessageStatus.PENDING, description="消息状态")
    sender: AgentType = Field(..., description="发送者")
    receiver: AgentType = Field(..., description="接收者")
    content: Dict[str, Any] = Field(..., description="消息内容")
    parent_id: Optional[str] = Field(None, description="父消息的ID（用于回复）")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息创建时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "msg_123456",
                "type": "command",
                "status": "pending",
                "sender": "central",
                "receiver": "content",
                "content": {
                    "action": "create_script",
                    "parameters": {
                        "theme": "旅行",
                        "style": "幽默",
                        "duration": 30
                    }
                },
                "parent_id": None,
                "timestamp": "2023-11-20T12:34:56.789Z",
                "metadata": {
                    "priority": "high",
                    "session_id": "sess_abcdef"
                }
            }
        }
    }


class UserChoice(BaseModel):
    """用户选择模型"""
    choice_id: str = Field(..., description="选择的ID")
    option_id: str = Field(..., description="选项的ID")
    feedback: Optional[str] = Field(None, description="用户反馈")
    timestamp: datetime = Field(default_factory=datetime.now, description="选择时间")


class AgentResponse(BaseModel):
    """代理响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")
    status_code: int = Field(200, description="状态码")


class WorkflowState(BaseModel):
    """工作流状态模型"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    current_stage: str = Field(..., description="当前阶段")
    message_history: List[Message] = Field(default_factory=list, description="消息历史")
    created_assets: Dict[str, Any] = Field(default_factory=dict, description="创建的资产")
    user_choices: List[UserChoice] = Field(default_factory=list, description="用户选择")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据") 