"""
真实API调用工作流程测试
测试系统从脚本创建到视频生成的整个工作流程，使用真实API调用而不是模拟数据
"""

import asyncio
import unittest
import os
import logging
import json
import uuid
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.mcp_central_agent import MCPCentralAgent
from agents.mcp_content_agent import MCPContentAgent
from agents.mcp_storyboard_agent import MCPStoryboardAgent
from agents.mcp_visual_agent import MCPVisualAgent
from models.mcp import (
    MCPMessage, MCPMessageType, MCPStatus, MCPPriority, MCPCommand, MCPResponse,
    create_command_message
)
from models.video import ScriptType, VideoStyle, FrameType, ShotType
from utils.mcp_message_bus import mcp_message_bus
from tests.test_utils import create_test_directories, clean_test_directories

# 设置测试日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_real_workflow")

class TestRealWorkflow(unittest.TestCase):
    """测试真实API调用的完整工作流程"""
    
    @classmethod
    async def setUpClass(cls):
        """设置测试环境"""
        logger.info("=== 设置测试环境 ===")
        
        # 创建测试目录
        create_test_directories()
        
        # 检查环境变量
        cls._check_api_keys()
        
        # 初始化代理
        cls.central_agent = MCPCentralAgent()
        cls.content_agent = MCPContentAgent()
        cls.storyboard_agent = MCPStoryboardAgent()
        cls.visual_agent = MCPVisualAgent()
        
        # 启动代理
        await cls.central_agent.start()
        await cls.content_agent.start()
        await cls.storyboard_agent.start()
        await cls.visual_agent.start()
        
        # 等待代理启动完成
        await asyncio.sleep(1)
        
        logger.info("所有代理启动完成")

    @classmethod
    def _check_api_keys(cls):
        """检查必要的API密钥是否已设置"""
        # 检查OpenAI API密钥
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("未设置OPENAI_API_KEY环境变量，这可能会导致某些测试失败")
        else:
            logger.info("已检测到OPENAI_API_KEY环境变量")
        
        # 检查其他可能需要的API密钥
        # 这里可以添加其他API密钥的检查，例如图像生成、视频生成等API密钥
    
    @classmethod
    async def tearDownClass(cls):
        """清理测试环境"""
        logger.info("=== 清理测试环境 ===")
        
        # 关闭代理
        await cls.central_agent.stop()
        await cls.content_agent.stop()
        await cls.storyboard_agent.stop()
        await cls.visual_agent.stop()
        
        logger.info("测试环境清理完成")
    
    async def test_real_script_creation(self):
        """测试真实创建脚本，使用内容代理调用OpenAI API"""
        logger.info("=== 测试真实创建脚本 ===")
        
        # 生成会话ID
        session_id = f"real_test_session_{uuid.uuid4().hex[:8]}"
        
        # 创建脚本生成参数
        script_params = {
            "theme": "人工智能在医疗领域的应用",
            "style": "informative",
            "type": "narrative",  # 使用有效的枚举值
            "duration": 120,  # 目标时长：2分钟
            "target_audience": ["医疗专业人员", "技术爱好者"],
            "language": "zh-CN"
        }
        
        # 创建命令消息
        command = create_command_message(
            source="test_runner",
            target="content_agent",
            action="create_script",
            parameters=script_params,
            session_id=session_id
        )
        
        logger.info(f"正在调用真实OpenAI API创建脚本，主题: {script_params['theme']}")
        
        # 发送命令到内容代理
        response = await self.content_agent.handle_command(command)
        
        # 验证响应
        self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(response.body.success)
        self.assertIn("script", response.body.data)
        
        script = response.body.data["script"]
        self.assertIsNotNone(script)
        
        # 保存脚本到文件
        with open(f"output/test/real_script_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        
        logger.info(f"脚本创建成功: {script.get('title')}")
        logger.info(f"使用的会话ID: {session_id}")
        
        return script, session_id
    
    async def test_real_storyboard_creation(self):
        """测试真实创建分镜内容，使用内容代理调用OpenAI API"""
        logger.info("=== 测试真实创建分镜内容 ===")
        
        # 先创建脚本
        script, session_id = await self.test_real_script_creation()
        
        # 创建分镜生成参数
        storyboard_params = {
            "script": script,
            "style": "storyboard"
        }
        
        # 创建命令消息
        command = create_command_message(
            source="test_runner",
            target="content_agent",
            action="create_storyboard_content",
            parameters=storyboard_params,
            session_id=session_id
        )
        
        logger.info(f"正在调用真实OpenAI API创建分镜内容，脚本标题: {script['title']}")
        
        # 发送命令到内容代理
        response = await self.content_agent.handle_command(command)
        
        # 验证响应
        self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(response.body.success)
        self.assertIn("storyboard_data", response.body.data)
        
        storyboard_data = response.body.data["storyboard_data"]
        self.assertIsNotNone(storyboard_data)
        
        # 保存分镜内容到文件
        with open(f"output/test/real_storyboard_content_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(storyboard_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分镜内容创建成功，包含 {len(storyboard_data.get('frames', []))} 个场景")
        
        return storyboard_data, script, session_id
    
    async def test_real_storyboard_processing(self):
        """测试真实分镜处理，验证分镜代理的处理功能"""
        logger.info("=== 测试真实分镜处理 ===")
        
        # 先创建分镜内容
        storyboard_data, script, session_id = await self.test_real_storyboard_creation()
        
        # 创建分镜处理参数
        process_params = {
            "storyboard_data": storyboard_data,
            "script": script
        }
        
        # 创建命令消息
        command = create_command_message(
            source="test_runner",
            target="storyboard_agent",
            action="process_storyboard",
            parameters=process_params,
            session_id=session_id
        )
        
        logger.info(f"正在处理分镜数据")
        
        # 发送命令到分镜代理
        response = await self.storyboard_agent.handle_command(command)
        
        # 验证响应
        self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(response.body.success)
        self.assertIn("storyboard", response.body.data)
        
        storyboard = response.body.data["storyboard"]
        self.assertIsNotNone(storyboard)
        
        # 保存分镜到文件
        with open(f"output/test/real_storyboard_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(storyboard, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分镜处理成功，创建了 {len(storyboard.get('frames', []))} 个分镜帧")
        
        return storyboard, script, session_id
    
    async def test_real_storyboard_image_generation(self):
        """测试真实分镜图像生成，验证分镜代理的图像生成功能"""
        logger.info("=== 测试真实分镜图像生成 ===")
        
        # 先处理分镜
        storyboard, script, session_id = await self.test_real_storyboard_processing()
        
        # 创建图像生成参数
        image_params = {
            "storyboard": storyboard,
            "image_source": "openai",  # 使用实际的图像生成服务
            "image_style": "realistic"
        }
        
        # 创建命令消息
        command = create_command_message(
            source="test_runner",
            target="storyboard_agent",
            action="generate_storyboard_images",
            parameters=image_params,
            session_id=session_id
        )
        
        logger.info(f"正在使用真实API生成分镜图像")
        
        # 发送命令到分镜代理
        response = await self.storyboard_agent.handle_command(command)
        
        # 验证响应
        self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(response.body.success)
        self.assertIn("storyboard", response.body.data)
        
        updated_storyboard = response.body.data["storyboard"]
        self.assertIsNotNone(updated_storyboard)
        self.assertIn("images", updated_storyboard)
        self.assertGreater(len(updated_storyboard["images"]), 0)
        
        # 保存更新后的分镜到文件
        with open(f"output/test/real_storyboard_with_images_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(updated_storyboard, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分镜图像生成成功，生成了 {len(updated_storyboard['images'])} 个图像")
        
        return updated_storyboard, script, session_id
    
    async def test_real_central_workflow(self):
        """测试中央代理协调的真实完整工作流程"""
        logger.info("=== 测试中央代理协调的真实完整工作流程 ===")
        
        # 生成会话ID和工作流ID
        session_id = f"real_test_session_{uuid.uuid4().hex[:8]}"
        workflow_id = f"real_workflow_{uuid.uuid4().hex[:8]}"
        
        # 创建工作流参数
        workflow_params = {
            "workflow_id": workflow_id,
            "theme": "人工智能在教育领域的应用",
            "style": "informative",
            "type": "narrative",
            "duration": 120,  # 2分钟
            "target_audience": ["教育工作者", "学生", "技术爱好者"],
            "storyboard_style": "storyboard",
            "generate_images": True,
            "image_source": "openai",  # 使用实际的图像生成服务
            "image_style": "realistic",
            "video_model": "none"  # 不生成实际视频，因为这可能很耗时和昂贵
        }
        
        # 创建命令消息
        command = create_command_message(
            source="test_runner",
            target="central_agent",
            action="start_workflow",
            parameters=workflow_params,
            session_id=session_id
        )
        
        logger.info(f"正在启动真实工作流: {workflow_id}, 主题: {workflow_params['theme']}")
        
        # 发送命令到中央代理
        response = await self.central_agent.handle_command(command)
        
        # 验证响应
        self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(response.body.success)
        
        # 等待工作流完成或超时
        timeout = 300  # 等待5分钟
        start_time = datetime.now()
        workflow_completed = False
        
        while not workflow_completed and (datetime.now() - start_time).total_seconds() < timeout:
            # 获取工作流状态
            status_command = create_command_message(
                source="test_runner",
                target="central_agent",
                action="get_workflow_status",
                parameters={"workflow_id": workflow_id},
                session_id=session_id
            )
            
            status_response = await self.central_agent.handle_command(status_command)
            
            if status_response.body.success and "workflow" in status_response.body.data:
                workflow = status_response.body.data["workflow"]
                workflow_status = workflow.get("status")
                
                if workflow_status in ["completed", "failed"]:
                    workflow_completed = True
                    logger.info(f"工作流 {workflow_id} 已{workflow_status}")
                    break
            
            logger.info(f"工作流 {workflow_id} 正在进行中，已等待 {(datetime.now() - start_time).total_seconds():.1f} 秒")
            await asyncio.sleep(10)  # 每10秒检查一次
        
        if not workflow_completed:
            logger.warning(f"等待工作流完成已超时 ({timeout} 秒)")
        
        # 获取最终工作流结果
        final_command = create_command_message(
            source="test_runner",
            target="central_agent",
            action="get_workflow",
            parameters={"workflow_id": workflow_id},
            session_id=session_id
        )
        
        final_response = await self.central_agent.handle_command(final_command)
        
        # 验证响应
        self.assertEqual(final_response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(final_response.body.success)
        self.assertIn("workflow", final_response.body.data)
        
        final_workflow = final_response.body.data["workflow"]
        
        # 保存工作流到文件
        with open(f"output/test/real_workflow_{workflow_id}.json", "w", encoding="utf-8") as f:
            json.dump(final_workflow, f, ensure_ascii=False, indent=2)
            
        logger.info(f"工作流测试完成: {workflow_id}")
        logger.info(f"工作流状态: {final_workflow.get('status')}")
        for stage_name, stage_info in final_workflow.get("stages", {}).items():
            logger.info(f"阶段 {stage_name}: {stage_info.get('status')}")
        
        return workflow_id, session_id


async def run_selected_tests(tests_to_run=None):
    """运行选定的测试"""
    test_case = TestRealWorkflow()
    await test_case.setUpClass()
    
    # 可运行的所有测试
    available_tests = {
        "script": test_case.test_real_script_creation,
        "storyboard_content": test_case.test_real_storyboard_creation,
        "storyboard_process": test_case.test_real_storyboard_processing,
        "storyboard_images": test_case.test_real_storyboard_image_generation,
        "workflow": test_case.test_real_central_workflow
    }
    
    # 如果没有指定测试，默认运行所有测试
    if not tests_to_run:
        tests_to_run = list(available_tests.keys())
    
    try:
        logger.info("\n\n========== 开始真实API测试 ==========")
        logger.info(f"将运行以下测试: {', '.join(tests_to_run)}")
        
        results = {}
        
        # 运行选定的测试
        for test_name in tests_to_run:
            if test_name in available_tests:
                logger.info(f"\n===== 开始测试: {test_name} =====")
                try:
                    result = await available_tests[test_name]()
                    logger.info(f"测试 {test_name} 成功")
                    results[test_name] = True
                except Exception as e:
                    logger.error(f"测试 {test_name} 失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    results[test_name] = False
            else:
                logger.warning(f"未知的测试: {test_name}")
        
        logger.info("\n\n========== 所有测试完成 ==========")
        logger.info("测试结果:")
        for test_name, success in results.items():
            logger.info(f"- {test_name}: {'成功' if success else '失败'}")
        
        logger.info(f"测试结果保存在 'output/test/' 目录中")
        
    finally:
        # 清理
        await test_case.tearDownClass()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="运行真实API调用的工作流程测试")
    parser.add_argument("--tests", type=str, nargs="*", 
                        help="要运行的测试列表，可选值: script, storyboard_content, storyboard_process, storyboard_images, workflow")
    
    return parser.parse_args()


if __name__ == "__main__":
    """运行测试主程序"""
    try:
        args = parse_args()
        asyncio.run(run_selected_tests(args.tests))
        print("测试完成!")
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 