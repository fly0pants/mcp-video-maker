"""
测试工具函数
包含测试过程中使用的辅助函数和模拟器
"""

import json
import asyncio
import os
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Callable
from unittest.mock import patch, MagicMock

from tests.test_config import MOCK_OPENAI_RESPONSES, MOCK_VIDEO_API_RESPONSES, MOCK_IMAGE_API_RESPONSES

# 设置日志记录
logger = logging.getLogger("test_utils")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class MockAsyncResponse:
    """模拟异步HTTP响应"""
    
    def __init__(self, status_code: int, data: Dict[str, Any]):
        self.status_code = status_code
        self._data = data
        
    async def json(self) -> Dict[str, Any]:
        return self._data
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockOpenAI:
    """模拟OpenAI客户端"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = self._mock_create
        
    async def _mock_create(self, model=None, messages=None, temperature=None, max_tokens=None, **kwargs):
        # 分析请求内容决定返回什么模拟响应
        user_message = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
        
        # 创建一个模拟脚本或分镜
        if "脚本" in user_message or "script" in user_message.lower():
            # 创建模拟脚本
            script_data = create_mock_script()
            content = json.dumps(script_data, ensure_ascii=False, indent=2)
            logger.info(f"MockOpenAI生成脚本: {script_data['title']}")
        elif "分镜" in user_message or "storyboard" in user_message.lower():
            # 首先创建模拟脚本
            script_data = create_mock_script()
            # 然后基于脚本创建模拟分镜数据
            storyboard_data = create_mock_storyboard_data(script_data)
            content = json.dumps(storyboard_data, ensure_ascii=False, indent=2)
            logger.info(f"MockOpenAI生成分镜数据，包含 {len(storyboard_data['frames'])} 个场景")
        else:
            content = "这是一个默认的模拟响应。"
            
        # 创建模拟响应对象
        choice = MagicMock()
        choice.message.content = content
        
        response = MagicMock()
        response.choices = [choice]
        
        logger.info(f"MockOpenAI返回响应，长度: {len(content)} 字符")
        
        return response
    

class MockHTTPClient:
    """模拟HTTP客户端"""
    
    async def get(self, url: str, headers: Dict = None, params: Dict = None, **kwargs) -> MockAsyncResponse:
        """模拟GET请求"""
        logger.info(f"模拟GET请求: {url}")
        
        # 根据URL返回不同的模拟响应
        if "video" in url and "status" in url:
            return MockAsyncResponse(200, MOCK_VIDEO_API_RESPONSES["check_status"])
        elif "image" in url:
            return MockAsyncResponse(200, MOCK_IMAGE_API_RESPONSES["generate_image"])
        else:
            return MockAsyncResponse(200, {"status": "success", "message": "默认GET响应"})
    
    async def post(self, url: str, headers: Dict = None, json: Dict = None, data: Dict = None, **kwargs) -> MockAsyncResponse:
        """模拟POST请求"""
        logger.info(f"模拟POST请求: {url}")
        
        # 根据URL返回不同的模拟响应
        if "video" in url and "generate" in url:
            return MockAsyncResponse(200, MOCK_VIDEO_API_RESPONSES["generate_video"])
        elif "image" in url:
            return MockAsyncResponse(200, MOCK_IMAGE_API_RESPONSES["generate_image"])
        else:
            return MockAsyncResponse(200, {"status": "success", "message": "默认POST响应"})
    
    async def aclose(self):
        """模拟关闭连接"""
        pass


def apply_mocks():
    """应用所有模拟，返回patch列表"""
    patches = []
    
    # 模拟OpenAI
    openai_patch = patch('openai.AsyncOpenAI', MockOpenAI)
    patches.append(openai_patch)
    
    # 模拟HTTP客户端
    httpx_patch = patch('httpx.AsyncClient', MockHTTPClient)
    patches.append(httpx_patch)
    
    # 启用所有模拟
    for p in patches:
        p.start()
    
    return patches


def remove_mocks(patches: List):
    """移除所有模拟"""
    for p in patches:
        p.stop()


async def wait_for_processing(check_status_func: Callable, task_id: str, max_retries: int = 10, delay: float = 1.0) -> bool:
    """
    等待任务处理完成
    
    Args:
        check_status_func: 检查状态的函数
        task_id: 任务ID
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        
    Returns:
        任务是否完成
    """
    for i in range(max_retries):
        status = await check_status_func(task_id)
        if status.get("status") == "completed":
            return True
        elif status.get("status") == "failed":
            logger.error(f"任务失败: {status.get('error', '未知错误')}")
            return False
        
        logger.info(f"任务处理中 [{i+1}/{max_retries}]...")
        await asyncio.sleep(delay)
    
    logger.warning(f"等待任务处理超时")
    return False


def create_test_directories():
    """创建测试所需的目录"""
    dirs = [
        "output/test",
        "output/test/scripts",
        "output/test/storyboards",
        "output/test/images",
        "output/test/videos",
        "temp/test",
        "assets/test"
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"创建目录: {directory}")


def clean_test_directories():
    """清理测试目录中的文件（保留目录结构）"""
    dirs = [
        "output/test/scripts",
        "output/test/storyboards",
        "output/test/images",
        "output/test/videos",
        "temp/test"
    ]
    
    for directory in dirs:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            logger.info(f"清理目录: {directory}")


def create_mock_script() -> Dict[str, Any]:
    """创建模拟脚本数据"""
    script_id = f"script_{uuid.uuid4().hex[:8]}"
    
    # 创建脚本章节
    sections = []
    for i in range(5):
        section_id = f"section_{uuid.uuid4().hex[:8]}"
        section = {
            "id": section_id,
            "order": i,
            "content": f"这是第{i+1}个场景的内容。介绍AI在日常生活中的应用场景。",
            "visual_description": f"场景{i+1}：展示一个人使用智能设备，周围环境现代化。",
            "audio_description": "背景音乐轻快，narrator讲述AI如何改变生活。",
            "duration": 12.0,  # 每个部分12秒
            "tags": ["AI", "科技", "日常生活"]
        }
        sections.append(section)
    
    # 确保总时长与各部分时长之和一致
    total_duration = sum(section["duration"] for section in sections)
    
    script = {
        "id": script_id,
        "title": "人工智能改变生活的5种方式",
        "theme": "科技",
        "type": "narrative",  # 使用有效的枚举值
        "target_audience": ["年轻人", "科技爱好者"],
        "sections": sections,
        "total_duration": total_duration,
        "creator_id": "test_user",
        "version": 1,
        "keywords": ["AI", "智能家居", "自动化"],
        "metadata": {"created_for_test": True}
    }
    
    return script


def create_mock_storyboard_data(script: Dict[str, Any]) -> Dict[str, Any]:
    """根据脚本创建模拟分镜数据"""
    frames = []
    
    # 可用的镜头类型（根据枚举定义）
    shot_types = ["wide", "medium", "close_up", "aerial", "pov", "tracking", "static", "handheld", "dolly"]
    frame_types = ["keyframe", "establishing", "closeup", "action", "transition", "dialogue", "narrative"]
    
    for i, section in enumerate(script["sections"]):
        frame = {
            "id": f"frame_{uuid.uuid4().hex[:8]}",
            "order": i,
            "script_section_id": section["id"],
            "frame_type": frame_types[i % len(frame_types)],  # 使用有效的枚举值
            "shot_type": shot_types[i % len(shot_types)],     # 使用有效的枚举值
            "description": f"分镜{i+1}",
            "visual_description": section["visual_description"],
            "dialogue": None,
            "duration": section["duration"],
            "camera_movement": "静态",
            "composition": "中心构图",
            "comments": "测试用分镜"
        }
        frames.append(frame)
    
    storyboard_data = {
        "raw_content": "# 分镜测试\n\n这是测试用的分镜内容。",
        "style": "storyboard",
        "frames": frames,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "model": "test_mock",
            "is_test": True
        }
    }
    
    return storyboard_data 