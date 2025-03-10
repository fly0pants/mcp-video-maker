# MCP (Multi-agent Communication Protocol) 协议文档

## 1. 概述

MCP (Multi-agent Communication Protocol) 是一种专为多代理系统设计的通信协议，用于在不同的 AI 代理之间进行标准化、可靠的消息传递。该协议支持异步通信、事件驱动模式和请求-响应模式，适用于复杂的多代理协作场景。

### 1.1 设计目标

- **标准化通信**: 提供统一的消息格式和通信模式
- **可靠性**: 支持消息确认、超时处理和错误恢复
- **灵活性**: 适应不同类型的代理和通信需求
- **可扩展性**: 易于添加新的代理和消息类型
- **可观测性**: 提供消息跟踪和监控能力

### 1.2 核心概念

- **消息 (Message)**: 代理间通信的基本单位，包含头部和内容
- **代理 (Agent)**: 能够发送和接收消息的实体
- **消息总线 (Message Bus)**: 负责消息的路由和分发
- **会话 (Session)**: 相关消息的逻辑分组
- **工作流 (Workflow)**: 多个代理协作完成的任务流程

## 2. 消息结构

MCP 消息由三部分组成：头部(Header)、正文(Body)和元数据(Metadata)。

### 2.1 消息头部 (MCPHeader)

```json
{
  "message_id": "mcp_abc123def456",
  "correlation_id": "mcp_xyz789",
  "timestamp": "2023-06-15T10:30:00Z",
  "source": "content_agent",
  "target": "visual_agent",
  "message_type": "command",
  "priority": "normal",
  "ttl": 300,
  "session_id": "session_12345",
  "trace_id": "trace_67890",
  "content_format": "json",
  "status": "pending"
}
```

字段说明：

- `message_id`: 消息唯一标识符
- `correlation_id`: 相关消息 ID，用于请求-响应关联
- `timestamp`: 消息创建时间戳
- `source`: 消息来源代理
- `target`: 消息目标代理或频道
- `message_type`: 消息类型（command, response, event 等）
- `priority`: 消息优先级（low, normal, high, critical）
- `ttl`: 消息生存时间(秒)
- `session_id`: 会话 ID
- `trace_id`: 追踪 ID，用于跟踪一系列相关消息
- `content_format`: 消息内容格式（json, text, binary, action）
- `status`: 消息状态（pending, processing, completed, failed, canceled, timeout）

### 2.2 消息正文 (MCPBody)

消息正文根据消息类型不同而有不同的结构：

#### 2.2.1 命令消息 (MCPCommand)

```json
{
  "action": "create_script",
  "parameters": {
    "theme": "人工智能",
    "style": "幽默",
    "duration": 60.0
  },
  "execution_context": {
    "timeout_seconds": 120
  },
  "timeout_seconds": 120,
  "idempotency_key": "idempotent_12345"
}
```

#### 2.2.2 响应消息 (MCPResponse)

```json
{
  "success": true,
  "message": "Script created successfully",
  "data": {
    "script": {
      "script_id": "script_abc123",
      "title": "AI的幽默之旅",
      "sections": [...]
    }
  },
  "execution_time_ms": 1500
}
```

#### 2.2.3 事件消息 (MCPEvent)

```json
{
  "event_type": "script.created",
  "event_source": "content_agent",
  "timestamp": "2023-06-15T10:32:00Z",
  "data": {
    "script_id": "script_abc123",
    "title": "AI的幽默之旅"
  },
  "sequence_number": 1
}
```

#### 2.2.4 错误消息 (MCPError)

```json
{
  "error_code": "INVALID_PARAMETERS",
  "error_message": "Missing required parameter: theme",
  "details": {
    "missing_fields": ["theme"]
  },
  "retry_possible": true,
  "suggested_action": "Provide the missing parameters and retry"
}
```

### 2.3 元数据 (Metadata)

元数据是可选的，用于存储与消息处理相关的额外信息：

```json
{
  "retry_count": 0,
  "processing_time_ms": 150,
  "route_history": ["gateway", "load_balancer"],
  "client_info": {
    "ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  }
}
```

## 3. 消息类型

MCP 协议支持以下消息类型：

1. **COMMAND**: 命令消息，请求代理执行特定操作
2. **RESPONSE**: 响应消息，对命令的回复
3. **EVENT**: 事件通知，代理状态变化或重要事件的通知
4. **DATA**: 数据传输，用于传输大量数据
5. **ERROR**: 错误消息，表示处理过程中发生错误
6. **QUERY**: 查询请求，请求获取信息而不改变状态
7. **SUBSCRIBE**: 订阅请求，订阅特定主题或事件
8. **UNSUBSCRIBE**: 取消订阅请求，取消之前的订阅
9. **HEARTBEAT**: 心跳消息，用于检测代理是否在线
10. **STATE_UPDATE**: 状态更新，代理状态的详细更新

## 4. 通信模式

### 4.1 请求-响应模式

最基本的通信模式，一个代理发送命令，另一个代理处理并响应：

```
Agent A                    Agent B
  |                          |
  |--- Command Message ----->|
  |                          | (处理命令)
  |<---- Response Message ---|
  |                          |
```

### 4.2 发布-订阅模式

事件驱动的通信模式，代理可以订阅特定主题，当有相关事件发生时接收通知：

```
Agent A        Message Bus        Agent B        Agent C
  |                |                |              |
  |-- Subscribe -->|                |              |
  |                |<-- Subscribe --|              |
  |                |                |              |
  |--- Event ----->|                |              |
  |                |--- Event ----->|              |
  |                |                |              |
  |                |<-- Subscribe --|              |
  |--- Event ----->|                |              |
  |                |--- Event ----->|              |
  |                |--- Event ----->|              |
```

### 4.3 广播模式

向所有代理或特定组的代理发送消息：

```
Agent A        Message Bus        Agent B        Agent C
  |                |                |              |
  |-- Broadcast -->|                |              |
  |                |--- Message --->|              |
  |                |--- Message ---------------->  |
```

## 5. 消息总线

消息总线是 MCP 协议的核心组件，负责消息的路由、分发和管理。

### 5.1 主要功能

- **消息路由**: 将消息从源代理传递到目标代理
- **消息分发**: 支持点对点、发布-订阅和广播模式
- **消息存储**: 保存消息历史，支持重放和查询
- **消息监控**: 跟踪消息流转和处理状态
- **错误处理**: 处理消息传递和处理过程中的错误

### 5.2 订阅机制

消息总线支持三种订阅方式：

1. **直接订阅**: 订阅发送给特定代理 ID 的消息
2. **主题订阅**: 订阅特定主题的消息
3. **类型订阅**: 订阅特定类型的消息

```python
# 直接订阅
await message_bus.subscribe_direct("agent_id", callback_function)

# 主题订阅
await message_bus.subscribe_topic("topic_name", callback_function)

# 类型订阅
await message_bus.subscribe_type(MCPMessageType.EVENT, callback_function)
```

## 6. 代理实现

### 6.1 基础代理类

所有代理都应继承自`MCPBaseAgent`基类，该类提供了基本的消息处理和通信功能：

```python
class MCPBaseAgent(ABC):
    def __init__(self, agent_id: str, agent_name: str):
        # 初始化代理

    async def initialize(self):
        # 初始化代理，包括订阅消息

    async def start(self):
        # 启动代理，包括启动心跳任务

    async def stop(self):
        # 停止代理，清理资源

    async def send_command(self, target, action, parameters, ...):
        # 发送命令消息

    async def send_event(self, target, event_type, data, ...):
        # 发送事件消息

    @abstractmethod
    async def handle_command(self, message: MCPMessage) -> Optional[MCPMessage]:
        # 处理命令消息，子类必须实现
```

### 6.2 代理生命周期

1. **初始化**: 调用`initialize()`方法，设置代理状态和订阅消息
2. **启动**: 调用`start()`方法，启动心跳任务和其他后台任务
3. **运行**: 代理处于活动状态，处理接收到的消息
4. **停止**: 调用`stop()`方法，清理资源和取消订阅

### 6.3 心跳机制

代理通过定期发送心跳消息来表明自己处于活动状态：

```python
async def _send_heartbeats(self):
    while self.is_running:
        try:
            # 创建并发送心跳消息
            heartbeat_msg = create_heartbeat_message(
                source=self.agent_id,
                agent_id=self.agent_id,
                status="active",
                load=await self._get_current_load()
            )
            await message_bus.publish(heartbeat_msg)

            # 等待下一次心跳时间
            await asyncio.sleep(self._heartbeat_interval)
        except Exception as e:
            self.logger.error(f"Error sending heartbeat: {str(e)}")
```

## 7. 工作流管理

工作流是多个代理协作完成的任务流程，通常由中央控制代理协调。

### 7.1 工作流状态

工作流状态包括：

- **started**: 工作流已启动
- **processing**: 工作流正在处理中
- **completed**: 工作流已成功完成
- **failed**: 工作流处理失败
- **canceled**: 工作流被取消

### 7.2 工作流阶段

工作流通常分为多个阶段，每个阶段由不同的代理处理：

```json
{
  "workflow_id": "workflow_abc123",
  "status": "processing",
  "current_stage": "video_generation",
  "stages": {
    "script_creation": {
      "status": "completed",
      "started_at": "...",
      "completed_at": "..."
    },
    "video_generation": {
      "status": "processing",
      "started_at": "...",
      "completed_at": null
    },
    "audio_generation": {
      "status": "pending",
      "started_at": null,
      "completed_at": null
    },
    "post_production": {
      "status": "pending",
      "started_at": null,
      "completed_at": null
    },
    "distribution": {
      "status": "pending",
      "started_at": null,
      "completed_at": null
    }
  }
}
```

## 8. 错误处理

### 8.1 错误类型

- **验证错误**: 消息格式或内容不符合要求
- **处理错误**: 代理处理消息时发生错误
- **超时错误**: 消息处理超时
- **路由错误**: 消息无法路由到目标代理
- **系统错误**: 系统级别的错误，如资源不足

### 8.2 错误响应

当发生错误时，代理应返回错误消息：

```python
return message.create_error_response(
    error_code="PROCESSING_ERROR",
    error_message="Failed to process command",
    details={"exception": str(e)}
)
```

### 8.3 重试机制

对于可重试的错误，系统支持自动重试：

```python
# 在发送命令时指定重试次数
response = await agent.send_command(
    target="content_agent",
    action="create_script",
    parameters=script_params,
    max_retries=3,
    retry_delay=2.0
)
```

## 9. 安全性

### 9.1 消息验证

确保消息来源可信：

```python
# 验证消息签名
if not verify_message_signature(message):
    return message.create_error_response(
        error_code="INVALID_SIGNATURE",
        error_message="Message signature verification failed"
    )
```

### 9.2 访问控制

限制代理的操作权限：

```python
# 检查代理是否有权限执行操作
if not self._check_permission(message.header.source, command.action):
    return message.create_error_response(
        error_code="PERMISSION_DENIED",
        error_message="Agent does not have permission to perform this action"
    )
```

## 10. 最佳实践

### 10.1 消息设计

- 使用明确的消息类型和动作名称
- 保持消息结构简洁，避免过大的消息体
- 使用适当的优先级和 TTL
- 包含足够的上下文信息，便于调试和跟踪

### 10.2 代理实现

- 实现幂等的命令处理器
- 正确处理和报告错误
- 使用异步处理避免阻塞
- 实现健壮的状态管理
- 记录详细的日志，便于问题排查

### 10.3 系统配置

- 根据负载调整消息队列大小
- 配置适当的超时时间
- 设置合理的重试策略
- 实现监控和告警机制

## 11. 示例

### 11.1 创建和发送命令

```python
# 创建命令消息
command_msg = create_command_message(
    source="central_agent",
    target="content_agent",
    action="create_script",
    parameters={
        "theme": "人工智能",
        "style": "幽默",
        "duration": 60.0
    },
    session_id="session_12345"
)

# 发布消息
message_id = await message_bus.publish(command_msg)

# 等待响应
response = await message_bus.wait_for_response(
    message_id=message_id,
    timeout=30.0,
    expected_source="content_agent"
)
```

### 11.2 处理命令

```python
async def handle_command(self, message: MCPMessage) -> Optional[MCPMessage]:
    # 验证是否为命令消息
    if not isinstance(message.body, MCPCommand):
        return message.create_error_response(
            error_code="INVALID_MESSAGE",
            error_message="Expected a command message"
        )

    # 获取命令详情
    command = message.body

    try:
        if command.action == "create_script":
            # 处理创建脚本命令
            script = await self._create_script(command.parameters)

            # 返回成功响应
            return message.create_response(
                success=True,
                message="Script created successfully",
                data={"script": script.dict()}
            )
        else:
            # 未知命令
            return message.create_error_response(
                error_code="UNKNOWN_COMMAND",
                error_message=f"Unknown command action: {command.action}"
            )
    except Exception as e:
        # 处理错误
        return message.create_error_response(
            error_code="PROCESSING_ERROR",
            error_message=f"Error processing command: {str(e)}"
        )
```

## 12. 工具和调试

### 12.1 消息监控

使用消息总线的监控功能查看消息流转：

```python
# 获取消息历史
messages = message_bus.get_message_history(
    limit=10,
    agent_id="content_agent",
    message_type=MCPMessageType.COMMAND
)

# 打印消息详情
for msg in messages:
    print(f"Message {msg.header.message_id}: {msg.header.message_type} from {msg.header.source} to {msg.header.target}")
```

### 12.2 性能指标

监控系统性能：

```python
# 获取消息总线指标
metrics = message_bus.get_metrics()
print(f"Messages processed: {metrics['messages_processed']}")
print(f"Average processing time: {metrics['average_processing_time_ms']} ms")
print(f"Queue size: {metrics['queue_size']}")
```

### 12.3 命令行工具

使用命令行工具管理和调试 MCP 系统：

```bash
# 查看代理状态
python mcp_cli.py agents status

# 发送测试命令
python mcp_cli.py send command --target content_agent --action create_script --param theme="AI" --param style="幽默"

# 查看消息历史
python mcp_cli.py messages list --limit 10 --agent content_agent
```

## 13. 总结

MCP 协议提供了一个灵活、可靠的框架，用于构建多代理协作系统。通过标准化的消息格式和通信模式，不同的代理可以无缝协作，共同完成复杂的任务。

关键优势：

- **标准化**: 统一的消息格式和通信模式
- **灵活性**: 支持多种通信模式和消息类型
- **可靠性**: 内置错误处理和重试机制
- **可观测性**: 完善的监控和日志功能
- **可扩展性**: 易于添加新��代理和功能