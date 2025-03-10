# TikTok 风格短视频多代理协作生成系统

这是一个基于多代理协作架构的 TikTok 风格短视频生成系统，通过六个专门的代理协同工作，完成从创意到发布的全流程自动化。

## 系统特点

1. **多代理协作架构**：六个专门代理（中央策略、内容创作、视觉生成、语音与音乐、后期制作、分发）协同工作。
2. **灵活的模型选择**：支持多种视频生成模型、语音合成工具和音乐生成工具。
3. **用户干预机制**：在关键创作阶段允许用户预览和选择。
4. **标准化通信协议**：通过消息总线实现代理间的异步通信。
5. **完整的 API 接口**：提供创建、查询、响应等 API 接口。
6. **简单的前端界面**：实现了基本的用户交互界面。

## MCP 协议

本项目使用 MCP (Multi-agent Communication Protocol) 协议作为代理间通信的标准。MCP 协议是一种专为多代理系统设计的通信协议，用于在不同的 AI 代理之间进行标准化、可靠的消息传递。

详细的协议文档请参见 [MCP 协议文档](docs/mcp_protocol.md)。

## 多模型支持

系统支持多种 AI 模型和工具，用户可以根据需求自由选择：

### 视频生成模型

- **可灵视频生成**：支持高质量写实风格视频
- **Pika Labs**：擅长创意和艺术风格视频
- **Runway Gen-2**：提供电影级视频质量
- **Wan 动画生成**：专注于动画风格视频

### 语音合成工具

- **ElevenLabs**：提供自然流畅的多语言语音
- **Play.ht**：支持多种语言和声音风格
- **腾讯云语音合成**：提供中文语音的高质量合成

### 音乐生成工具

- **Suno AI**：生成多种风格的原创音乐
- **AIVA**：专注于情感和氛围音乐创作
- **SoundRaw**：提供无版权的背景音乐

### 编辑工具

- **Runway**：提供专业级视频编辑和特效
- **Descript**：专注于音频增强和字幕生成
- **Kapwing**：提供丰富的文本效果和转场

## API 模型配置灵活性

系统提供了灵活的 API 模型配置机制：

1. **配置文件**：所有模型和工具的配置都集中在`config/config.py`文件中
2. **环境变量**：支持通过环境变量覆盖默认配置
3. **用户偏好**：用户可以设置偏好的模型和工具，系统会优先使用
4. **动态更新**：支持在运行时更新配置，无需重启系统
5. **参数调整**：每个模型和工具都有丰富的参数可以调整，如温度、采样策略等

## 安装与运行

### 环境要求

- Python 3.9+
- 依赖包（见 requirements.txt）

### 安装步骤

1. 克隆仓库：

   ```bash
   git clone https://github.com/fly0pants/mcp-video-maker.git
   cd mcp-video-maker
   ```

2. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

3. 配置 API 密钥（可选）：
   创建`.env`文件并添加以下内容：
   ```
   KELING_API_KEY=your_keling_api_key
   PIKA_API_KEY=your_pika_api_key
   RUNWAY_API_KEY=your_runway_api_key
   WAN_API_KEY=your_wan_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   PLAYHT_API_KEY=your_playht_api_key
   TENCENT_API_KEY=your_tencent_api_key
   SUNO_API_KEY=your_suno_api_key
   AIVA_API_KEY=your_aiva_api_key
   SOUNDRAW_API_KEY=your_soundraw_api_key
   ```

### 运行系统

1. 启动后端服务：

   ```bash
   python main.py
   ```

2. 启动前端服务：

   ```bash
   python ui/server.py
   ```

3. 在浏览器中访问：`http://localhost:8080`

## 测试

系统提供了全面的测试套件，确保各个组件和整体系统的正常运行：

### 运行所有测试

```bash
pytest tests/
```

### 运行特定测试

```bash
# 测试多模型支持
pytest tests/test_multi_model_support.py

# 测试API配置灵活性
pytest tests/test_api_config.py

# 测试整体系统功能
pytest tests/test_system_integration.py
```

## 项目结构

```
video-maker/
├── agents/                 # 代理实现
│   ├── base_agent.py       # 基础代理类
│   ├── central_agent.py    # 中央策略代理
│   ├── content_agent.py    # 内容创作代理
│   ├── visual_agent.py     # 视觉生成代理
│   ├── audio_agent.py      # 语音与音乐代理
│   ├── postprod_agent.py   # 后期制作代理
│   └── distribution_agent.py # 分发代理
├── config/                 # 配置文件
│   └── config.py           # 系统配置
├── models/                 # 数据模型
│   ├── message.py          # 消息模型
│   ├── user.py             # 用户模型
│   └── video.py            # 视频模型
├── utils/                  # 工具类
│   ├── file_manager.py     # 文件管理
│   ├── logger.py           # 日志工具
│   └── message_bus.py      # 消息总线
├── ui/                     # 前端界面
│   ├── server.py           # 前端服务器
│   ├── static/             # 静态资源
│   └── templates/          # 页面模板
├── tests/                  # 测试代码
│   ├── test_multi_model_support.py  # 多模型支持测试
│   ├── test_api_config.py           # API配置测试
│   └── test_system_integration.py   # 系统集成测试
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖列表
└── README.md               # 项目说明
```

## 注意事项

- 当前实现主要是模拟 API 调用，实际使用时需替换为真实 API 调用
- 系统设计支持异步操作，确保高效处理多个请求
- 所有代理都支持错误处理和重试机制，确保系统稳定性

## 贡献

欢迎提交问题和改进建议！请先讨论您想要进行的更改，然后提交拉取请求。

## 许可

本项目采用 MIT 许可证 - 详见 LICENSE 文件