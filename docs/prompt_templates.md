# Prompt 模板配置系统

本文档介绍了系统中配置化 Prompt 模板的使用方法，包括模板的格式、配置、加载和渲染等方面。

## 1. 概述

配置化 Prompt 模板系统允许将硬编码的 Prompt 内容抽离到配置文件中，使系统能够更灵活地管理和使用各种 Prompt。主要功能包括：

- 将 Prompt 模板存储在 JSON 配置文件中
- 支持动态参数替换
- 支持系统角色（System Role）配置
- 支持模型参数配置
- 支持实时修改和重新加载
- 提供命令行工具进行管理

## 2. 模板配置文件格式

Prompt 模板配置文件使用 JSON 格式，存储在 `config/prompts` 目录下。每个文件可以包含多个模板及其相关配置。

### 基本结构

```json
{
  "template_key": {
    "description": "模板描述",
    "template": "模板内容，使用 {{variable}} 表示变量",
    "parameters": {
      "param1": "默认值1",
      "param2": "默认值2"
    }
  },
  "system_role": {
    "template_key": "该模板对应的系统角色提示"
  }
}
```

### 示例：内容创建代理的配置

文件名：`content_agent_prompts.json`

```json
{
  "create_script": {
    "description": "生成TikTok短视频脚本模板",
    "template": "你是一位专业的TikTok短视频脚本编剧。请为以下主题创建一个引人入胜的短视频脚本：\n\n主题：{{theme}}\n风格：{{style}}\n类型：{{script_type}}\n目标受众：{{target_audience}}\n总时长：{{duration}}秒\n语言：{{language}}\n关键词：{{keywords}}\n特殊要求：{{special_requirements}}\n\n请创建一个包含{{num_sections}}个场景的脚本，每个场景应包含：\n1. 场景内容（对白或旁白）\n2. 视觉描述\n3. 音频描述\n4. 场景时长（秒）\n5. 相关标签\n\n请以JSON格式返回，包含标题和场景列表."
  },
  "modify_script": {
    "description": "根据用户反馈修改TikTok短视频脚本模板",
    "template": "这是一个TikTok短视频脚本：\n\n{{script_json}}\n\n用户提供了以下反馈：\n\n{{feedback}}\n\n请根据用户反馈修改脚本，保持JSON格式不变，但更新内容以满足用户需求。"
  },
  "system_role": {
    "create_script": "你是一位专业的TikTok短视频脚本编剧，擅长创作引人入胜、节奏紧凑的短视频内容。",
    "modify_script": "你是一位专业的TikTok短视频脚本编剧，擅长根据反馈修改脚本。"
  }
}
```

## 3. 使用方法

### 在代码中使用

通过 `PromptManager` 类即可在代码中使用配置的模板：

```python
from utils.prompt_manager import get_prompt_manager

# 获取 PromptManager 单例实例
prompt_manager = get_prompt_manager()

# 准备参数
parameters = {
    "theme": "人工智能",
    "style": "幽默",
    "script_type": "知识普及",
    "target_audience": ["年轻人", "学生"],
    "duration": 60.0,
    "language": "zh",
    "keywords": "AI, 机器学习, 未来",
    "special_requirements": "包含一些有趣的AI误解",
    "num_sections": 5
}

# 渲染模板
prompt = prompt_manager.render_template(
    file_key="content_agent_prompts",  # 配置文件名（不含扩展名）
    template_key="create_script",      # 模板名称
    parameters=parameters              # 参数字典
)

# 获取系统角色
system_role = prompt_manager.get_system_role(
    file_key="content_agent_prompts",
    template_key="create_script"
)

# 获取模型参数
model_params = prompt_manager.get_parameters(
    file_key="content_agent_prompts",
    template_key="create_script"
)

# 使用生成的prompt和系统角色
response = await openai_client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_role},
        {"role": "user", "content": prompt}
    ],
    temperature=model_params.get("temperature", 0.7),
    response_format={"type": "json_object"}
)
```

### 自动重载机制

`PromptManager` 支持自动检测并重新加载已修改的配置文件，确保系统始终使用最新的模板配置。

每次调用 `get_template()`, `get_system_role()` 或 `get_parameters()` 时，系统会自动检查相应的配置文件是否已被修改，如果有修改则会自动重新加载。

## 4. 命令行工具

系统提供了一个命令行工具 `tools/prompt_manager_cli.py`，用于管理和操作配置化的 Prompt 模板。

### 基本用法

```bash
# 列出所有模板
python tools/prompt_manager_cli.py list

# 显示特定模板
python tools/prompt_manager_cli.py show content_agent_prompts create_script

# 编辑模板内容
python tools/prompt_manager_cli.py edit content_agent_prompts create_script

# 创建新的模板文件
python tools/prompt_manager_cli.py create-file new_prompts

# 在现有文件中创建新模板
python tools/prompt_manager_cli.py create content_agent_prompts new_template --description "新模板描述" --system-role "系统角色"

# 更新系统角色
python tools/prompt_manager_cli.py system-role content_agent_prompts create_script

# 更新参数配置
python tools/prompt_manager_cli.py parameters content_agent_prompts create_script

# 渲染模板（测试）
python tools/prompt_manager_cli.py render content_agent_prompts create_script --params theme="AI测试" style="教学" duration=30

# 强制重新加载所有模板
python tools/prompt_manager_cli.py reload
```

## 5. 最佳实践

### 模板组织

- 为相关功能的模板创建单独的配置文件，例如 `content_agent_prompts.json`、`visual_agent_prompts.json` 等
- 在同一个配置文件中，为相关的模板提供统一的系统角色
- 使用描述性的名称和详细的描述，便于团队成员理解模板的用途

### 参数设置

- 在模板中使用 `{{parameter}}` 格式定义变量
- 为参数提供明确的默认值，确保在未提供参数时系统仍能正常工作
- 对于列表类型的参数，系统会自动将其转换为逗号分隔的字符串

### 维护与更新

- 定期审核和更新模板，确保其与系统的最新需求保持一致
- 使用版本控制系统管理模板配置文件的变更
- 在进行重大更改前，先在测试环境中验证模板的渲染结果

## 6. 故障排除

### 常见问题

1. **模板未更新**

   - 确认修改已保存
   - 使用 `reload` 命令强制重新加载
   - 检查文件权限和格式

2. **参数替换不生效**

   - 确认参数名称与模板中的 `{{parameter}}` 完全一致
   - 注意参数名称区分大小写
   - 确保参数值能够被正确转换为字符串

3. **JSON 解析错误**
   - 检查 JSON 文件格式，确保符合标准
   - 使用 JSON 验证工具验证配置文件的格式
   - 避免在 JSON 文件中使用注释
