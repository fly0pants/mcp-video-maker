# MCP 系统优化文档

本文档详细说明了对 TikTok 风格短视频多代理协作生成系统的 MCP（Multi-agent Communication Protocol）通信框架的优化。

## 1. 错误处理与恢复机制增强

### 1.1 错误分类和处理策略

实现了层次化的错误分类系统，明确区分暂时性和永久性错误：

- **扩展 MCPError 模型**：
  - 添加 `category` 字段，区分 `TEMPORARY` 和 `PERMANENT` 错误
  - 添加 `max_retries`、`retry_delay_ms` 等字段，提供错误恢复建议
  - 添加 `recovery_strategy` 字段，指导接收方如何处理错误
  - 添加 `error_severity` 字段，标识错误严重程度

### 1.2 智能重试机制

实现了指数退避重试策略，根据错误类型智能调整重试行为：

- **增强 send_command 方法**：
  - 添加 `retry_config` 参数，支持配置重试策略
  - 实现指数退避算法，避免立即重试导致的雪崩效应
  - 添加随机抖动，防止多个客户端同时重试
  - 根据错误响应中的建议动态调整重试策略

## 2. 消息传递可靠性保障

### 2.1 消息持久化

实现了关键消息的持久化存储，以应对代理崩溃的情况：

- **创建 MCPMessagePersistence 接口**：

  - 定义消息持久化的标准接口
  - 实现基于文件系统的持久化实现 `FileSystemMessagePersistence`
  - 支持消息的保存、加载、删除和查询

- **集成到 MCPMessageBus**：
  - 根据消息优先级和类型决定是否持久化
  - 系统启动时恢复未处理的持久化消息
  - 消息处理完成后标记为已处理

### 2.2 消息去重机制

实现了幂等消息处理，确保重复消息不会导致操作重复执行：

- **利用 idempotency_key**：
  - 在 MCPCommand 中使用 idempotency_key 标识唯一操作
  - 在消息总线中维护已处理的幂等键集合
  - 定期清理过期的幂等键

## 3. 断路器与限流模式

### 3.1 断路器模式

实现了断路器模式，防止系统级联故障：

- **断路器状态管理**：

  - 实现 CLOSED（正常）、OPEN（阻断）、HALF-OPEN（试探）三种状态
  - 根据失败次数自动开启断路器
  - 在半开状态下允许部分请求通过，测试目标服务是否恢复

- **集成到消息发布流程**：
  - 在消息发布前检查断路器状态
  - 断路器开启时快速失败，返回适当的错误响应
  - 根据成功/失败响应更新断路器状态

### 3.2 智能限流

实现了基于负载的自适应限流机制：

- **令牌桶限流算法**：

  - 实现 `TokenBucket` 和 `RateLimiter` 类
  - 支持基于时间的令牌生成和消耗
  - 支持等待令牌和超时机制

- **动态调整限流参数**：
  - 根据目标代理的负载情况动态调整速率
  - 根据消息优先级分配不同的令牌消耗量
  - 高优先级消息获得更多资源，确保关键操作不受阻

## 4. 工作流管理增强

### 4.1 状态机驱动工作流

使用状态机模式管理复杂工作流：

- **工作流状态机**：

  - 实现 `Workflow`、`WorkflowState` 和 `WorkflowTransitionResult` 类
  - 支持状态定义、状态转换和事件发布
  - 提供状态进入/退出钩子和处理逻辑

- **集成到代理基类**：
  - 在 `MCPBaseAgent` 中添加工作流管理方法
  - 支持创建、查询、转换和停止工作流
  - 允许子类定义自定义工作流状态

### 4.2 容错工作流

实现了容错工作流设计，允许部分失败后恢复：

- **检查点机制**：

  - 支持在关键点创建工作流检查点
  - 允许从检查点恢复工作流状态
  - 记录检查点数据和时间戳

- **错误处理与恢复**：
  - 工作流状态支持错误处理和重试逻辑
  - 支持配置最大重试次数和重试策略
  - 提供错误状态和错误事件通知

## 5. 系统监控与可观测性

- **增强心跳机制**：

  - 添加代理负载和版本信息
  - 实现离线检测和通知

- **性能指标收集**：
  - 记录消息处理时间和成功/失败计数
  - 添加持久化成功/失败指标

## 6. 性能优化

- **消息批处理**：

  - 支持批量处理非实时消息
  - 减少网络交互和处理开销

- **历史消息管理**：
  - 限制内存中保存的历史消息数量
  - 定期清理过期数据

## 安装与依赖

新增依赖：

- aiofiles==23.2.1：用于异步文件操作
- tenacity==8.2.3：用于实现高级重试逻辑

## 使用示例

### 错误处理与重试

```python
# 使用重试配置发送命令
response = await agent.send_command(
    target="content_agent",
    action="generate_script",
    parameters={"theme": "travel"},
    retry_config={
        "max_retries": 5,
        "base_delay_ms": 100,
        "max_delay_ms": 5000,
        "jitter": 0.2
    }
)
```

### 工作流管理

```python
# 创建视频生成工作流
workflow_id = await agent.create_workflow(
    name="video_generation",
    initial_state="script_creation",
    initial_data={"theme": "travel", "duration": 30}
)

# 转换工作流状态
await agent.transition_workflow(workflow_id, "visual_generation")

# 创建检查点
await agent.create_workflow_checkpoint(workflow_id, "after_script")

# 从检查点恢复
await agent.restore_workflow_checkpoint(workflow_id, "after_script")
```
