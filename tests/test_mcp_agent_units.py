import asyncio
import unittest
import os
import json
import sys
import uuid
from typing import Dict, Any, List, Optional

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.mcp_content_agent import MCPContentAgent
from agents.mcp_storyboard_agent import MCPStoryboardAgent
from models.mcp import MCPMessageType
from models.video import Script, ScriptSection


class TestMCPAgentUnits(unittest.TestCase):
    """测试各个MCP代理的基本功能"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 创建输出目录
        os.makedirs("output/test_units", exist_ok=True)
    
    def create_mock_script(self) -> Dict[str, Any]:
        """创建模拟脚本数据"""
        script_id = f"script_{uuid.uuid4().hex[:8]}"
        
        sections = []
        for i in range(3):
            section = {
                "id": f"section_{uuid.uuid4().hex[:8]}",
                "order": i,
                "content": f"这是第 {i+1} 个场景的内容描述。介绍了一些关于人工智能的应用场景。",
                "visual_description": f"画面显示一个人正在使用智能手机，周围有各种智能设备。",
                "audio_description": f"背景音乐轻快，narrator讲述AI如何改变生活。",
                "duration": 15.0,
                "metadata": {}
            }
            sections.append(section)
        
        script = {
            "id": script_id,
            "creator_id": "test_user",
            "title": "人工智能在日常生活中的应用",
            "theme": "科技",
            "type": "educational",
            "style": "informative",
            "keywords": ["AI", "智能家居", "自动化"],
            "total_duration": 45.0,
            "sections": sections,
            "metadata": {
                "created_at": "2023-07-01T10:00:00Z"
            }
        }
        
        return script
    
    async def test_content_agent_script_creation(self):
        """测试内容代理脚本创建功能"""
        # 初始化内容代理
        content_agent = MCPContentAgent()
        
        # 创建会话ID
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # 创建脚本参数
        script_params = {
            "theme": "人工智能在日常生活中的应用",
            "style": "informative",
            "script_type": "short_form",
            "duration": 60.0,
            "keywords": ["AI", "智能家居", "科技"],
            "language": "zh",
            "special_requirements": "适合短视频平台，吸引年轻受众"
        }
        
        # 创建命令消息
        command = content_agent.create_command(
            action="create_script",
            parameters=script_params,
            session_id=session_id
        )
        
        # 模拟启动代理
        try:
            await content_agent.on_start()
            
            # 处理命令
            response = await content_agent.handle_command(command)
            
            # 验证响应
            self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
            self.assertTrue(response.body.success)
            self.assertIn("script", response.body.data)
            
            script = response.body.data["script"]
            self.assertIsNotNone(script)
            
            # 保存脚本到文件
            with open(f"output/test_units/content_script_{session_id}.json", "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=2)
            
            print(f"脚本创建成功: {script.get('title', '未知标题')}")
            
        finally:
            # 关闭代理
            await content_agent.on_stop()
    
    async def test_content_agent_storyboard_generation(self):
        """测试内容代理分镜内容生成功能"""
        # 初始化内容代理
        content_agent = MCPContentAgent()
        
        # 创建会话ID
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # 创建模拟脚本
        script = self.create_mock_script()
        
        # 创建分镜参数
        storyboard_params = {
            "script": script,
            "style": "storyboard"
        }
        
        # 创建命令消息
        command = content_agent.create_command(
            action="generate_storyboard_content",
            parameters=storyboard_params,
            session_id=session_id
        )
        
        # 模拟启动代理
        try:
            await content_agent.on_start()
            
            # 处理命令
            response = await content_agent.handle_command(command)
            
            # 验证响应
            self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
            self.assertTrue(response.body.success)
            self.assertIn("storyboard_data", response.body.data)
            
            storyboard_data = response.body.data["storyboard_data"]
            self.assertIsNotNone(storyboard_data)
            
            # 保存分镜内容到文件
            with open(f"output/test_units/content_storyboard_{session_id}.json", "w", encoding="utf-8") as f:
                json.dump(storyboard_data, f, ensure_ascii=False, indent=2)
            
            print(f"分镜内容生成成功，包含 {len(storyboard_data.get('frames', []))} 个场景")
            
        finally:
            # 关闭代理
            await content_agent.on_stop()
    
    async def test_storyboard_agent_processing(self):
        """测试分镜代理处理功能"""
        # 初始化分镜代理
        storyboard_agent = MCPStoryboardAgent()
        
        # 创建会话ID
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # 创建模拟脚本和分镜内容
        script = self.create_mock_script()
        
        # 创建模拟分镜数据
        storyboard_data = {
            "raw_content": "这是一份模拟的分镜内容",
            "style": "storyboard",
            "frames": [],
            "metadata": {
                "generated_at": "2023-07-01T10:30:00Z",
                "mock": True
            }
        }
        
        # 为每个脚本场景创建一个分镜帧
        for i, section in enumerate(script["sections"]):
            frame = {
                "id": f"frame_{uuid.uuid4().hex[:8]}",
                "order": i,
                "script_section_id": section["id"],
                "frame_type": "SCENE",
                "shot_type": "MEDIUM",
                "content": section["content"],
                "visual_description": section["visual_description"],
                "audio_description": section["audio_description"],
                "duration": section["duration"],
                "metadata": {}
            }
            storyboard_data["frames"].append(frame)
        
        # 创建处理参数
        process_params = {
            "storyboard_data": storyboard_data,
            "script": script
        }
        
        # 创建命令消息
        command = storyboard_agent.create_command(
            action="process_storyboard",
            parameters=process_params,
            session_id=session_id
        )
        
        # 模拟启动代理
        try:
            await storyboard_agent.on_start()
            
            # 处理命令
            response = await storyboard_agent.handle_command(command)
            
            # 验证响应
            self.assertEqual(response.header.message_type, MCPMessageType.RESPONSE)
            self.assertTrue(response.body.success)
            self.assertIn("storyboard", response.body.data)
            
            storyboard = response.body.data["storyboard"]
            self.assertIsNotNone(storyboard)
            
            # 保存分镜到文件
            with open(f"output/test_units/storyboard_{session_id}.json", "w", encoding="utf-8") as f:
                json.dump(storyboard, f, ensure_ascii=False, indent=2)
            
            print(f"分镜处理成功，创建了 {len(storyboard.get('frames', []))} 个分镜帧")
            
        finally:
            # 关闭代理
            await storyboard_agent.on_stop()


async def run_tests():
    """运行测试"""
    test_case = TestMCPAgentUnits()
    test_case.setUpClass()
    
    print("===== 测试内容代理脚本创建功能 =====")
    await test_case.test_content_agent_script_creation()
    
    print("\n===== 测试内容代理分镜内容生成功能 =====")
    await test_case.test_content_agent_storyboard_generation()
    
    print("\n===== 测试分镜代理处理功能 =====")
    await test_case.test_storyboard_agent_processing()
    
    print("\n===== 所有测试完成 =====")
    print("测试结果保存在 'output/test_units/' 目录中")


if __name__ == "__main__":
    asyncio.run(run_tests()) 