"""
MCP (Multi-agent Communication Protocol) 消息模型
定义了代理间通信的消息结构和工具函数
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MCPMessageType(str, Enum):
    """MCP协议消息类型枚举"""
    COMMAND = "command"            # 命令消息
    RESPONSE = "response"          # 响应消息
    EVENT = "event"                # 事件通知
    DATA = "data"                  # 数据传输
    ERROR = "error"                # 错误消息
    QUERY = "query"                # 查询请求
    SUBSCRIBE = "subscribe"        # 订阅请求
    UNSUBSCRIBE = "unsubscribe"    # 取消订阅请求
    HEARTBEAT = "heartbeat"        # 心跳消息
    STATE_UPDATE = "state_update"  # 状态更新


class MCPPriority(str, Enum):
    """MCP消息优先级枚举"""
    LOW = "low"           # 低优先级
    NORMAL = "normal"     # 正常优先级
    HIGH = "high"         # 高优先级
    CRITICAL = "critical" # 关键优先级


class MCPContentFormat(str, Enum):
    """MCP消息内容格式枚举"""
    JSON = "json"         # JSON格式
    TEXT = "text"         # 纯文本
    BINARY = "binary"     # 二进制数据
    ACTION = "action"     # 操作指令


class MCPStatus(str, Enum):
    """MCP消息状态枚举"""
    PENDING = "pending"       # 等待处理
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 处理失败
    CANCELED = "canceled"     # 已取消
    TIMEOUT = "timeout"       # 处理超时


class MCPHeader(BaseModel):
    """MCP消息头"""
    message_id: str = Field(default_factory=lambda: f"mcp_{uuid.uuid4().hex[:10]}", description="消息唯一标识符")
    correlation_id: Optional[str] = Field(None, description="相关消息ID，用于请求-响应关联")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息创建时间戳")
    source: str = Field(..., description="消息来源代理")
    target: str = Field(..., description="消息目标代理或频道")
    message_type: MCPMessageType = Field(..., description="消息类型")
    priority: MCPPriority = Field(default=MCPPriority.NORMAL, description="消息优先级")
    ttl: Optional[int] = Field(None, description="消息生存时间(秒)")
    session_id: Optional[str] = Field(None, description="会话ID")
    trace_id: Optional[str] = Field(None, description="追踪ID, 用于跟踪一系列相关消息")
    content_format: MCPContentFormat = Field(default=MCPContentFormat.JSON, description="消息内容格式")
    status: MCPStatus = Field(default=MCPStatus.PENDING, description="消息状态")


class MCPCommand(BaseModel):
    """MCP命令消息内容"""
    action: str = Field(..., description="要执行的动作")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="命令参数")
    execution_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="执行上下文")
    timeout_seconds: Optional[int] = Field(None, description="命令执行超时时间(秒)")
    idempotency_key: Optional[str] = Field(None, description="幂等性键，确保命令只执行一次")


class MCPResponse(BaseModel):
    """MCP响应消息内容"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    execution_time_ms: Optional[int] = Field(None, description="执行时间(毫秒)")
    resource_ids: Optional[List[str]] = Field(None, description="相关资源ID列表")


class MCPEvent(BaseModel):
    """MCP事件消息内容"""
    event_type: str = Field(..., description="事件类型")
    event_source: str = Field(..., description="事件来源")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件发生时间")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    sequence_number: Optional[int] = Field(None, description="事件顺序号")
    is_volatile: bool = Field(default=False, description="是否为易失性事件")


class MCPQuery(BaseModel):
    """MCP查询消息内容"""
    query_type: str = Field(..., description="查询类型")
    filters: Dict[str, Any] = Field(default_factory=dict, description="查询过滤条件")
    fields: Optional[List[str]] = Field(None, description="要返回的字段")
    pagination: Optional[Dict[str, Any]] = Field(None, description="分页信息")
    order_by: Optional[List[str]] = Field(None, description="排序字段")


class MCPSubscription(BaseModel):
    """MCP订阅消息内容"""
    topic: str = Field(..., description="订阅主题")
    filters: Optional[Dict[str, Any]] = Field(None, description="订阅过滤条件")
    expiration: Optional[datetime] = Field(None, description="订阅过期时间")
    callback_endpoint: Optional[str] = Field(None, description="回调端点")
    subscription_id: str = Field(default_factory=lambda: f"sub_{uuid.uuid4().hex[:8]}", description="订阅ID")


class MCPError(BaseModel):
    """MCP错误消息内容"""
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    retry_possible: bool = Field(default=False, description="是否可以重试")
    suggested_action: Optional[str] = Field(None, description="建议的操作")


class MCPStateUpdate(BaseModel):
    """MCP状态更新消息内容"""
    entity_id: str = Field(..., description="实体ID")
    entity_type: str = Field(..., description="实体类型")
    previous_state: Optional[Dict[str, Any]] = Field(None, description="之前的状态")
    current_state: Dict[str, Any] = Field(..., description="当前状态")
    changed_fields: Optional[List[str]] = Field(None, description="变更的字段")
    timestamp: datetime = Field(default_factory=datetime.now, description="状态更新时间")


class MCPHeartbeat(BaseModel):
    """MCP心跳消息内容"""
    agent_id: str = Field(..., description="代理ID")
    status: str = Field(default="active", description="代理状态")
    load: Optional[float] = Field(None, description="代理负载情况，0-1之间")
    uptime_seconds: Optional[int] = Field(None, description="代理运行时间")
    version: Optional[str] = Field(None, description="代理版本")


# 消息内容类型联合
MCPContentType = Union[
    MCPCommand,
    MCPResponse,
    MCPEvent,
    MCPQuery,
    MCPSubscription,
    MCPError,
    MCPStateUpdate,
    MCPHeartbeat,
    Dict[str, Any]  # 用于DATA类型
]


class MCPMessage(BaseModel):
    """MCP协议消息完整结构"""
    header: MCPHeader
    body: MCPContentType
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    def create_response(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None) -> 'MCPMessage':
        """创建对当前消息的响应消息"""
        response_header = MCPHeader(
            message_id=f"mcp_{uuid.uuid4().hex[:10]}",
            correlation_id=self.header.message_id,
            timestamp=datetime.now(),
            source=self.header.target,
            target=self.header.source,
            message_type=MCPMessageType.RESPONSE,
            priority=self.header.priority,
            session_id=self.header.session_id,
            trace_id=self.header.trace_id,
            content_format=MCPContentFormat.JSON,
            status=MCPStatus.COMPLETED if success else MCPStatus.FAILED
        )

        response_body = MCPResponse(
            success=success,
            message=message,
            data=data
        )

        return MCPMessage(
            header=response_header,
            body=response_body,
            metadata={}
        )

    def create_error_response(self, error_code: str, error_message: str, details: Optional[Dict[str, Any]] = None) -> 'MCPMessage':
        """创建对当前消息的错误响应消息"""
        error_header = MCPHeader(
            message_id=f"mcp_{uuid.uuid4().hex[:10]}",
            correlation_id=self.header.message_id,
            timestamp=datetime.now(),
            source=self.header.target,
            target=self.header.source,
            message_type=MCPMessageType.ERROR,
            priority=self.header.priority,
            session_id=self.header.session_id,
            trace_id=self.header.trace_id,
            content_format=MCPContentFormat.JSON,
            status=MCPStatus.FAILED
        )

        error_body = MCPError(
            error_code=error_code,
            error_message=error_message,
            details=details,
            retry_possible=True if error_code.startswith("TEMP_") else False
        )

        return MCPMessage(
            header=error_header,
            body=error_body,
            metadata={}
        )


def create_command_message(
    source: str,
    target: str,
    action: str,
    parameters: Dict[str, Any],
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    priority: MCPPriority = MCPPriority.NORMAL,
    timeout_seconds: Optional[int] = None
) -> MCPMessage:
    """创建命令消息"""
    header = MCPHeader(
        message_id=f"mcp_{uuid.uuid4().hex[:10]}",
        timestamp=datetime.now(),
        source=source,
        target=target,
        message_type=MCPMessageType.COMMAND,
        priority=priority,
        session_id=session_id or f"session_{uuid.uuid4().hex[:8]}",
        trace_id=trace_id or f"trace_{uuid.uuid4().hex[:8]}",
        content_format=MCPContentFormat.JSON,
        status=MCPStatus.PENDING
    )

    body = MCPCommand(
        action=action,
        parameters=parameters,
        timeout_seconds=timeout_seconds
    )

    return MCPMessage(
        header=header,
        body=body,
        metadata={}
    )


def create_event_message(
    source: str,
    target: str,
    event_type: str,
    data: Dict[str, Any],
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None
) -> MCPMessage:
    """创建事件消息"""
    header = MCPHeader(
        message_id=f"mcp_{uuid.uuid4().hex[:10]}",
        timestamp=datetime.now(),
        source=source,
        target=target,
        message_type=MCPMessageType.EVENT,
        priority=MCPPriority.NORMAL,
        session_id=session_id,
        trace_id=trace_id,
        content_format=MCPContentFormat.JSON,
        status=MCPStatus.COMPLETED
    )

    body = MCPEvent(
        event_type=event_type,
        event_source=source,
        timestamp=datetime.now(),
        data=data
    )

    return MCPMessage(
        header=header,
        body=body,
        metadata={}
    )


def create_query_message(
    source: str,
    target: str,
    query_type: str,
    filters: Dict[str, Any],
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    fields: Optional[List[str]] = None,
    pagination: Optional[Dict[str, Any]] = None
) -> MCPMessage:
    """创建查询消息"""
    header = MCPHeader(
        message_id=f"mcp_{uuid.uuid4().hex[:10]}",
        timestamp=datetime.now(),
        source=source,
        target=target,
        message_type=MCPMessageType.QUERY,
        priority=MCPPriority.NORMAL,
        session_id=session_id,
        trace_id=trace_id,
        content_format=MCPContentFormat.JSON,
        status=MCPStatus.PENDING
    )

    body = MCPQuery(
        query_type=query_type,
        filters=filters,
        fields=fields,
        pagination=pagination
    )

    return MCPMessage(
        header=header,
        body=body,
        metadata={}
    )


def create_heartbeat_message(
    source: str,
    target: str = "system",
    agent_id: Optional[str] = None,
    status: str = "active",
    load: Optional[float] = None
) -> MCPMessage:
    """创建心跳消息"""
    header = MCPHeader(
        message_id=f"mcp_{uuid.uuid4().hex[:10]}",
        timestamp=datetime.now(),
        source=source,
        target=target,
        message_type=MCPMessageType.HEARTBEAT,
        priority=MCPPriority.LOW,
        content_format=MCPContentFormat.JSON,
        status=MCPStatus.COMPLETED
    )

    body = MCPHeartbeat(
        agent_id=agent_id or source,
        status=status,
        load=load
    )

    return MCPMessage(
        header=header,
        body=body,
        metadata={}
    )