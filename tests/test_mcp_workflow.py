import asyncio
import unittest
import os
import logging
import json
import uuid
from datetime import datetime
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.mcp_central_agent import MCPCentralAgent
from agents.mcp_content_agent import MCPContentAgent
from agents.mcp_storyboard_agent import MCPStoryboardAgent
from agents.mcp_visual_agent import MCPVisualAgent
from models.mcp import MCPCommand, MCPMessageType
from utils.mcp_message_bus import mcp_message_bus
from models.mcp import create_command_message


class TestMCPWorkflow(unittest.TestCase):
    """测试MCP代理系统的工作流程"""
    
    @classmethod
    async def setUpClass(cls):
        """初始化测试环境和代理"""
        # 设置日志
        logging.basicConfig(level=logging.INFO,
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 初始化消息总线 - 不需要显式初始化
        # await mcp_message_bus.initialize()
        
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
        await asyncio.sleep(2)
        
        # 创建输出目录
        os.makedirs("output/test_workflow", exist_ok=True)
    
    @classmethod
    async def tearDownClass(cls):
        """清理测试环境和代理"""
        # 关闭代理
        await cls.central_agent.stop()
        await cls.content_agent.stop()
        await cls.storyboard_agent.stop()
        await cls.visual_agent.stop()
        
        # 关闭消息总线 - 不需要显式关闭
        # await mcp_message_bus.shutdown()
    
    async def test_script_creation(self):
        """测试脚本创建功能"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # 创建脚本参数
        script_params = {
            "theme": "人工智能在日常生活中的应用",
            "style": "informative",
            "script_type": "short_form",
            "duration": 60.0,
            "references": [],
            "extra_requirements": "适合短视频平台，吸引年轻受众"
        }
        
        # 发送创建脚本命令
        response = await self.content_agent.handle_command(
            create_command_message(
                sender="test",
                target="content_agent",
                action="create_script",
                parameters=script_params,
                session_id=session_id
            )
        )
        
        # 验证响应
        self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(response.body.success)
        self.assertIn("script", response.body.data)
        
        script = response.body.data["script"]
        self.assertIsNotNone(script)
        self.assertIn("sections", script)
        self.assertGreater(len(script["sections"]), 0)
        
        print(f"脚本创建成功: {script['title']}")
        
        # 保存脚本到文件
        with open(f"output/test_workflow/script_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        
        return script, session_id
    
    async def test_storyboard_generation(self):
        """测试分镜生成功能"""
        # 先创建脚本
        script, session_id = await self.test_script_creation()
        
        # 创建分镜参数
        storyboard_params = {
            "script": script,
            "style": "storyboard"
        }
        
        # 发送生成分镜内容命令
        content_response = await self.content_agent.handle_command(
            create_command_message(
                sender="test",
                target="content_agent",
                action="generate_storyboard_content",
                parameters=storyboard_params,
                session_id=session_id
            )
        )
        
        # 验证响应
        self.assertEqual(content_response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(content_response.body.success)
        self.assertIn("storyboard_data", content_response.body.data)
        
        storyboard_data = content_response.body.data["storyboard_data"]
        self.assertIsNotNone(storyboard_data)
        self.assertIn("frames", storyboard_data)
        
        print(f"分镜内容生成成功，包含 {len(storyboard_data['frames'])} 个场景")
        
        # 保存分镜内容到文件
        with open(f"output/test_workflow/storyboard_content_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(storyboard_data, f, ensure_ascii=False, indent=2)
        
        # 将分镜内容发送给分镜代理处理
        process_params = {
            "storyboard_data": storyboard_data,
            "script": script
        }
        
        storyboard_response = await self.storyboard_agent.handle_command(
            create_command_message(
                sender="test",
                target="storyboard_agent",
                action="process_storyboard",
                parameters=process_params,
                session_id=session_id
            )
        )
        
        # 验证响应
        self.assertEqual(storyboard_response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(storyboard_response.body.success)
        self.assertIn("storyboard", storyboard_response.body.data)
        
        storyboard = storyboard_response.body.data["storyboard"]
        self.assertIsNotNone(storyboard)
        self.assertIn("frames", storyboard)
        self.assertGreater(len(storyboard["frames"]), 0)
        
        print(f"分镜处理成功，创建了 {len(storyboard['frames'])} 个分镜帧")
        
        # 保存处理后的分镜到文件
        with open(f"output/test_workflow/storyboard_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(storyboard, f, ensure_ascii=False, indent=2)
        
        return storyboard, script, session_id
    
    async def test_storyboard_image_generation(self):
        """测试分镜图像生成功能"""
        # 先生成分镜
        storyboard, script, session_id = await self.test_storyboard_generation()
        
        # 创建图像生成参数
        image_params = {
            "storyboard": storyboard,
            "image_source": "mock",  # 使用模拟模式
            "image_style": "realistic"
        }
        
        # 发送生成分镜图像命令
        image_response = await self.storyboard_agent.handle_command(
            create_command_message(
                sender="test",
                target="storyboard_agent",
                action="generate_storyboard_images",
                parameters=image_params,
                session_id=session_id
            )
        )
        
        # 验证响应
        self.assertEqual(image_response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(image_response.body.success)
        self.assertIn("storyboard", image_response.body.data)
        
        updated_storyboard = image_response.body.data["storyboard"]
        self.assertIsNotNone(updated_storyboard)
        self.assertIn("images", updated_storyboard)
        self.assertGreater(len(updated_storyboard["images"]), 0)
        
        print(f"分镜图像生成成功，生成了 {len(updated_storyboard['images'])} 个图像")
        
        # 保存带图像的分镜到文件
        with open(f"output/test_workflow/storyboard_with_images_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(updated_storyboard, f, ensure_ascii=False, indent=2)
        
        return updated_storyboard, script, session_id
    
    async def test_complete_workflow(self):
        """测试完整的工作流程，从CentralAgent开始"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # 创建视频创建参数
        video_params = {
            "theme": "人工智能在日常生活中的应用",
            "style": "informative",
            "type": "short_form",
            "duration": 60.0,
            "storyboard_style": "storyboard",
            "generate_images": True,
            "image_source": "mock",
            "image_style": "realistic"
        }
        
        # 发送创建视频工作流命令
        response = await self.central_agent.handle_command(
            create_command_message(
                sender="test",
                target="central_agent",
                action="start_video_creation",
                parameters=video_params,
                session_id=session_id
            )
        )
        
        # 验证响应
        self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(response.body.success)
        self.assertIn("workflow_id", response.body.data)
        
        workflow_id = response.body.data["workflow_id"]
        self.assertIsNotNone(workflow_id)
        
        print(f"工作流启动成功: {workflow_id}")
        
        # 等待工作流执行一段时间
        await asyncio.sleep(10)
        
        # 获取工作流状态
        status_response = await self.central_agent.handle_command(
            create_command_message(
                sender="test",
                target="central_agent",
                action="get_workflow_status",
                parameters={"workflow_id": workflow_id},
                session_id=session_id
            )
        )
        
        # 验证响应
        self.assertEqual(status_response.header.message_type, MCPMessageType.RESPONSE)
        self.assertTrue(status_response.body.success)
        self.assertIn("workflow", status_response.body.data)
        
        workflow = status_response.body.data["workflow"]
        self.assertIsNotNone(workflow)
        
        print(f"工作流状态: {workflow['status']}")
        print(f"脚本创建阶段: {workflow['stages']['script_creation']['status']}")
        print(f"分镜创建阶段: {workflow['stages']['storyboard_creation']['status']}")
        
        # 保存工作流状态到文件
        with open(f"output/test_workflow/workflow_{workflow_id}.json", "w", encoding="utf-8") as f:
            json.dump(workflow, f, ensure_ascii=False, indent=2)
        
        return workflow_id, session_id


async def run_tests():
    """运行测试"""
    # 使用unittest的测试方法
    test_case = TestMCPWorkflow()
    await test_case.setUpClass()
    
    try:
        # 运行测试
        print("===== 测试脚本创建功能 =====")
        script, session_id = await test_case.test_script_creation()
        
        print("\n===== 测试分镜生成功能 =====")
        storyboard, script, session_id = await test_case.test_storyboard_generation()
        
        print("\n===== 测试分镜图像生成功能 =====")
        storyboard_with_images, script, session_id = await test_case.test_storyboard_image_generation()
        
        print("\n===== 测试完整工作流程 =====")
        workflow_id, session_id = await test_case.test_complete_workflow()
        
        print("\n===== 所有测试完成 =====")
        print(f"测试结果保存在 'output/test_workflow/' 目录中")
        
    finally:
        # 清理
        await test_case.tearDownClass()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_tests()) 