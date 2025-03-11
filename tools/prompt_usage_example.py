#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prompt系统和增强日志的使用示例
"""

import os
import sys
import json
import asyncio
import time
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import system_logger, get_prompt_manager, log_api_call
from utils.logger import AgentLogger


# 创建一个测试用的代理日志器
test_logger = AgentLogger("test_agent")


@log_api_call('openai', 'chat_completions')
async def call_openai_api(prompt: str, model: str = "gpt-4", temperature: float = 0.7) -> Dict[str, Any]:
    """模拟调用OpenAI API的函数"""
    # 在实际应用中，这里会调用真正的API
    test_logger.info(f"调用OpenAI API: {model}", model=model, temperature=temperature)
    
    # 模拟API调用延迟
    await asyncio.sleep(1.2)
    
    # 模拟返回结果
    return {
        "id": "chatcmpl-123456789",
        "model": model,
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": f"这是对'{prompt[:20]}...'的回复"
                },
                "finish_reason": "stop"
            }
        ]
    }


@test_logger.timed("执行完整的提示渲染和API调用流程")
async def test_prompt_workflow():
    """测试整个提示工作流程"""
    # 获取提示管理器
    prompt_manager = get_prompt_manager()
    
    # 准备脚本生成的参数
    script_params = {
        "theme": "人工智能的未来",
        "style": "幽默诙谐",
        "script_type": "知识普及",
        "target_audience": ["年轻人", "学生", "技术爱好者"],
        "duration": 60,
        "language": "zh",
        "keywords": "AI, 机器学习, 深度学习, 未来科技",
        "special_requirements": "包含一些AI发展的有趣预测",
        "num_sections": 5
    }
    
    # 方法1: 直接渲染模板
    test_logger.info("方法1: 使用render_template渲染模板")
    prompt = prompt_manager.render_template(
        file_key="content_agent_prompts",
        template_key="create_script",
        parameters=script_params
    )
    system_role = prompt_manager.get_system_role(
        file_key="content_agent_prompts", 
        template_key="create_script"
    )
    test_logger.debug("已生成提示和系统角色", prompt_length=len(prompt))
    
    # 方法2: 使用build_prompt构建完整提示
    test_logger.info("方法2: 使用build_prompt构建完整提示")
    messages = prompt_manager.build_prompt(
        file_key="content_agent_prompts",
        template_key="create_script",
        parameters=script_params
    )
    test_logger.debug(f"已生成完整提示消息列表，包含 {len(messages)} 条消息")
    
    # 方法3: 组合多个模板
    test_logger.info("方法3: 使用compose_template组合模板")
    # 添加一个视觉引导组件
    visual_params = {
        "subject_description": "AI机器人与人类互动", 
        "style_description": "未来科技风格，明亮色调", 
        "mood_description": "友好、乐观"
    }
    
    combined_template = prompt_manager.compose_template(
        main_file_key="content_agent_prompts",
        main_template_key="create_script",
        components=[
            ("guidelines/visual_generation", "template", visual_params)
        ]
    )
    
    test_logger.debug(
        "已组合模板", 
        template_length=len(combined_template["template"]),
        has_system_role=bool(combined_template["system_role"])
    )
    
    # 使用提示调用API
    trace_id = "test-trace-123"
    test_logger.info("开始调用OpenAI API", trace_id=trace_id)
    
    try:
        response = await call_openai_api(
            prompt=prompt,
            model="gpt-4",
            temperature=0.7
        )
        
        test_logger.info(
            "API调用成功", 
            trace_id=trace_id,
            response_id=response["id"]
        )
        
        # 记录性能指标
        system_logger.log_performance_metric(
            metric_name="prompt_length",
            value=len(prompt),
            unit="chars",
            component="content_generation",
            trace_id=trace_id
        )
        
    except Exception as e:
        test_logger.exception("API调用失败", trace_id=trace_id)
        raise
    
    return response


@test_logger.timed("测试异常处理")
async def test_exception_handling():
    """测试异常处理和日志记录"""
    try:
        # 故意引发异常
        result = 10 / 0
    except Exception as e:
        test_logger.exception("计算过程中出现异常")
        # 继续抛出异常
        raise


async def main():
    """主函数"""
    system_logger.info("开始执行Prompt系统和日志功能测试")
    
    try:
        # 测试提示工作流
        response = await test_prompt_workflow()
        print(f"\n成功测试提示工作流: {response['id']}")
        
        # 测试异常处理
        try:
            await test_exception_handling()
        except Exception as e:
            print(f"\n成功捕获并记录异常: {str(e)}")
    
    except Exception as e:
        system_logger.critical(f"测试过程中出现严重错误: {str(e)}")
    
    finally:
        # 打印所有可用模板
        prompt_manager = get_prompt_manager()
        templates = prompt_manager.list_templates()
        system_logger.info(f"系统中共有 {len(templates)} 个模板文件")
        
        # 获取特定模板所需的参数
        params = prompt_manager.get_required_parameters(
            file_key="content_agent_prompts",
            template_key="create_script"
        )
        print(f"\n内容创建模板需要的参数: {', '.join(params)}")
        
        system_logger.info("测试完成")


if __name__ == "__main__":
    """执行主函数"""
    asyncio.run(main()) 