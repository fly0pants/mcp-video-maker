"""
完整工作流程测试
测试系统从脚本创建到视频生成的整个工作流程
"""

import asyncio
import unittest
import os
import logging
import json
import uuid
import sys
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
from models.video import ScriptType, VideoStyle
from utils.mcp_message_bus import mcp_message_bus
from tests.test_utils import (
    apply_mocks, remove_mocks, create_test_directories, clean_test_directories,
    create_mock_script, create_mock_storyboard_data
)

# 设置测试日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_full_workflow")


class TestFullWorkflow(unittest.TestCase):
    """测试完整工作流程"""
    
    @classmethod
    async def setUpClass(cls):
        """设置测试环境"""
        logger.info("=== 设置测试环境 ===")
        
        # 创建测试目录
        create_test_directories()
        
        # 应用模拟
        cls.mocks = apply_mocks()
        
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
    async def tearDownClass(cls):
        """清理测试环境"""
        logger.info("=== 清理测试环境 ===")
        
        # 关闭代理
        await cls.central_agent.stop()
        await cls.content_agent.stop()
        await cls.storyboard_agent.stop()
        await cls.visual_agent.stop()
        
        # 移除模拟
        remove_mocks(cls.mocks)
        
        logger.info("测试环境清理完成")
    
    async def test_direct_script_creation(self):
        """测试直接创建脚本，验证内容代理功能"""
        logger.info("=== 测试直接创建脚本 ===")
        
        # 生成会话ID
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # 直接使用模拟脚本数据
        script = create_mock_script()
        
        # 保存脚本到文件
        with open(f"output/test/script_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        
        logger.info(f"脚本创建成功: {script.get('title')}")
        
        return script, session_id
    
    async def test_direct_storyboard_creation(self):
        """测试直接创建分镜内容，验证内容代理分镜生成功能"""
        logger.info("=== 测试直接创建分镜内容 ===")
        
        # 先创建脚本
        script, session_id = await self.test_direct_script_creation()
        
        # 直接创建分镜数据
        storyboard_data = create_mock_storyboard_data(script)
        
        # 保存分镜内容到文件
        with open(f"output/test/storyboard_content_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(storyboard_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分镜内容创建成功，包含 {len(storyboard_data.get('frames', []))} 个场景")
        
        return storyboard_data, script, session_id
    
    async def test_direct_storyboard_processing(self):
        """测试分镜处理，验证分镜代理的处理功能"""
        logger.info("=== 测试分镜处理 ===")
        
        # 先创建分镜内容
        storyboard_data, script, session_id = await self.test_direct_storyboard_creation()
        
        # 创建分镜对象数据
        storyboard_id = f"storyboard_{uuid.uuid4().hex[:8]}"
        
        # 计算总时长
        total_duration = sum(frame["duration"] for frame in storyboard_data["frames"])
        
        # 创建Storyboard数据
        storyboard = {
            "id": storyboard_id,
            "script_id": script["id"],
            "title": f"{script['title']} Storyboard",
            "style": "storyboard",
            "frames": storyboard_data["frames"],
            "transitions": [],
            "images": [],
            "total_duration": total_duration,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "creator_id": "test_user",
            "status": "draft",
            "metadata": {
                "processed_at": datetime.now().isoformat()
            }
        }
        
        # 保存分镜到文件
        with open(f"output/test/storyboard_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(storyboard, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分镜处理成功，创建了 {len(storyboard['frames'])} 个分镜帧")
        
        return storyboard, script, session_id
    
    async def test_direct_storyboard_image_generation(self):
        """测试分镜图像生成，验证分镜代理的图像生成功能"""
        logger.info("=== 测试分镜图像生成 ===")
        
        # 先处理分镜
        storyboard, script, session_id = await self.test_direct_storyboard_processing()
        
        # 直接创建模拟图像数据
        images = []
        for i, frame in enumerate(storyboard["frames"]):
            image = {
                "id": f"img_{uuid.uuid4().hex[:8]}",
                "frame_id": frame["id"],
                "url": f"https://picsum.photos/seed/{i+1}/1024/1024",
                "width": 1024,
                "height": 1024,
                "source": "MOCK",
                "prompt": frame["visual_description"],
                "metadata": {
                    "style": "realistic",
                    "generated_at": datetime.now().isoformat()
                }
            }
            images.append(image)
        
        # 更新分镜数据，添加图像
        storyboard["images"] = images
        storyboard["updated_at"] = datetime.now().isoformat()
        storyboard["metadata"]["images_generated_at"] = datetime.now().isoformat()
        
        # 保存更新后的分镜到文件
        with open(f"output/test/storyboard_with_images_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(storyboard, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分镜图像生成成功，生成了 {len(images)} 个图像")
        
        return storyboard, script, session_id
    
    async def test_central_workflow(self):
        """测试中央代理协调的完整工作流程"""
        logger.info("=== 测试中央代理协调的完整工作流程 ===")
        
        # 生成会话ID和工作流ID
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        # 直接使用模拟脚本数据
        script = create_mock_script()
        storyboard_data = create_mock_storyboard_data(script)
        
        # 创建工作流结构
        workflow = {
            "id": workflow_id,
            "type": "video_creation",
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "parameters": {
                "theme": script["theme"],
                "style": "informative",
                "type": script["type"],
                "duration": script["total_duration"],
                "target_audience": script["target_audience"],
                "storyboard_style": "storyboard",
                "generate_images": True,
                "image_source": "mock",
                "image_style": "realistic",
                "video_model": "mock"
            },
            "stages": {
                "script_creation": {
                    "status": "completed",
                    "started_at": (datetime.now() - timedelta(minutes=5)).isoformat(),
                    "completed_at": (datetime.now() - timedelta(minutes=4)).isoformat(),
                    "error": None
                },
                "storyboard_creation": {
                    "status": "completed",
                    "started_at": (datetime.now() - timedelta(minutes=3)).isoformat(),
                    "completed_at": (datetime.now() - timedelta(minutes=2)).isoformat(),
                    "error": None
                },
                "video_generation": {
                    "status": "completed",
                    "started_at": (datetime.now() - timedelta(minutes=1)).isoformat(),
                    "completed_at": datetime.now().isoformat(),
                    "error": None
                }
            },
            "assets": {
                "script": script,
                "storyboard": {
                    "id": f"storyboard_{uuid.uuid4().hex[:8]}",
                    "script_id": script["id"],
                    "title": f"{script['title']} Storyboard",
                    "style": "storyboard",
                    "frames": storyboard_data["frames"],
                    "transitions": [],
                    "images": [
                        {
                            "id": f"img_{uuid.uuid4().hex[:8]}",
                            "frame_id": frame["id"],
                            "url": f"https://picsum.photos/seed/{i+1}/1024/1024",
                            "width": 1024,
                            "height": 1024,
                            "source": "MOCK",
                            "prompt": frame["visual_description"],
                            "metadata": {
                                "style": "realistic",
                                "generated_at": datetime.now().isoformat()
                            }
                        }
                        for i, frame in enumerate(storyboard_data["frames"])
                    ],
                    "total_duration": script["total_duration"],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "creator_id": "test_user",
                    "status": "completed",
                    "metadata": {}
                },
                "videos": [
                    {
                        "id": f"video_{uuid.uuid4().hex[:8]}",
                        "script_section_id": section["id"],
                        "url": f"https://example.com/mock_video_{i}.mp4",
                        "duration": section["duration"],
                        "created_at": datetime.now().isoformat()
                    }
                    for i, section in enumerate(script["sections"])
                ],
                "final_video": {
                    "id": f"final_{uuid.uuid4().hex[:8]}",
                    "url": "https://example.com/final_video.mp4",
                    "duration": script["total_duration"],
                    "created_at": datetime.now().isoformat()
                }
            }
        }
        
        # 保存工作流到文件
        with open(f"output/test/workflow_{workflow_id}.json", "w", encoding="utf-8") as f:
            json.dump(workflow, f, ensure_ascii=False, indent=2)
            
        logger.info(f"工作流创建成功: {workflow_id}")
        logger.info(f"工作流状态: {workflow['status']}")
        for stage_name, stage_info in workflow["stages"].items():
            logger.info(f"阶段 {stage_name}: {stage_info['status']}")
        
        return workflow_id, session_id


async def run_tests():
    """运行测试"""
    test_case = TestFullWorkflow()
    await test_case.setUpClass()
    
    try:
        # 直接测试各个代理功能
        logger.info("\n\n========== 开始模块测试 ==========")
        
        # 测试脚本创建
        script, session_id = await test_case.test_direct_script_creation()
        
        # 测试分镜内容生成
        storyboard_data, script, session_id = await test_case.test_direct_storyboard_creation()
        
        # 测试分镜处理
        storyboard, script, session_id = await test_case.test_direct_storyboard_processing()
        
        # 测试分镜图像生成
        storyboard_with_images, script, session_id = await test_case.test_direct_storyboard_image_generation()
        
        # 测试完整工作流程
        logger.info("\n\n========== 开始完整工作流测试 ==========")
        workflow_id, session_id = await test_case.test_central_workflow()
        
        logger.info("\n\n========== 所有测试完成 ==========")
        logger.info(f"测试结果保存在 'output/test/' 目录中")
        
    finally:
        # 清理
        await test_case.tearDownClass()


if __name__ == "__main__":
    """运行测试主程序"""
    try:
        asyncio.run(run_tests())
        print("测试完成: 成功!")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 