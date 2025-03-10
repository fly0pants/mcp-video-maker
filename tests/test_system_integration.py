"""
测试整体系统功能
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.central_agent import CentralAgent
from agents.visual_agent import VisualAgent
from agents.audio_agent import AudioAgent
from agents.content_agent import ContentAgent
from agents.postprod_agent import PostProdAgent
from agents.distribution_agent import DistributionAgent
from models.message import Message, MessageType, AgentType
from models.video import VideoCreationRequest
from config.config import USER_CONFIG, update_user_config
from utils.message_bus import MessageBus


class TestSystemIntegration(unittest.TestCase):
    """测试整体系统功能"""

    def setUp(self):
        """测试前的准备工作"""
        # 保存原始配置
        self.original_user_config = USER_CONFIG.copy()
        
        # 创建模拟会话ID
        self.session_id = "test_session_123"
        
        # 创建模拟请求
        self.request = VideoCreationRequest(
            topic="测试视频",
            style="vlog",
            duration=60,
            target_audience="年轻人",
            key_points=["测试点1", "测试点2"],
            references=["参考1", "参考2"],
            video_model="wan",
            voice_tool="elevenlabs",
            music_tool="suno",
            editing_tool="runway",
            resolution="1080x1920",
            language="zh"
        )

    def tearDown(self):
        """测试后的清理工作"""
        # 恢复原始配置
        global USER_CONFIG
        USER_CONFIG = self.original_user_config

    @patch('agents.central_agent.CentralAgent.handle_command')
    @patch('agents.content_agent.ContentAgent.handle_command')
    @patch('agents.visual_agent.VisualAgent.handle_command')
    @patch('agents.audio_agent.AudioAgent.handle_command')
    @patch('agents.postprod_agent.PostProdAgent.handle_command')
    @patch('agents.distribution_agent.DistributionAgent.handle_command')
    def test_end_to_end_workflow(self, mock_dist, mock_post, mock_audio, mock_visual, mock_content, mock_central):
        """测试端到端工作流程"""
        # 设置模拟响应
        mock_central.return_value = self._create_mock_response(AgentType.CENTRAL)
        mock_content.return_value = self._create_mock_response(AgentType.CONTENT)
        mock_visual.return_value = self._create_mock_response(AgentType.VISUAL)
        mock_audio.return_value = self._create_mock_response(AgentType.AUDIO)
        mock_post.return_value = self._create_mock_response(AgentType.POSTPROD)
        mock_dist.return_value = self._create_mock_response(AgentType.DISTRIBUTION)
        
        # 创建异步测试
        async def run_test():
            # 初始化消息总线
            message_bus = MessageBus()
            
            # 初始化所有代理
            central_agent = CentralAgent()
            content_agent = ContentAgent()
            visual_agent = VisualAgent()
            audio_agent = AudioAgent()
            postprod_agent = PostProdAgent()
            dist_agent = DistributionAgent()
            
            # 注册所有代理到消息总线
            await message_bus.register_agent(central_agent)
            await message_bus.register_agent(content_agent)
            await message_bus.register_agent(visual_agent)
            await message_bus.register_agent(audio_agent)
            await message_bus.register_agent(postprod_agent)
            await message_bus.register_agent(dist_agent)
            
            # 启动所有代理
            await central_agent.initialize()
            await content_agent.initialize()
            await visual_agent.initialize()
            await audio_agent.initialize()
            await postprod_agent.initialize()
            await dist_agent.initialize()
            
            # 创建初始消息（模拟用户请求）
            initial_message = Message(
                message_id="user_request_1",
                sender=None,
                receiver=AgentType.CENTRAL,
                message_type=MessageType.REQUEST,
                content={
                    "command": "create_video",
                    "parameters": {
                        "session_id": self.session_id,
                        "request": self.request.dict()
                    }
                }
            )
            
            # 发送初始消息
            await message_bus.send_message(initial_message)
            
            # 等待消息处理完成
            await asyncio.sleep(0.5)
            
            # 验证各代理是否被正确调用
            mock_central.assert_called_once()
            mock_content.assert_called_once()
            mock_visual.assert_called_once()
            mock_audio.assert_called_once()
            mock_post.assert_called_once()
            mock_dist.assert_called_once()
        
        # 运行异步测试
        asyncio.run(run_test())

    def test_model_selection_propagation(self):
        """测试模型选择传播"""
        # 更新用户配置
        new_config = {
            "preferred_video_model": "pika",
            "preferred_voice_tool": "playht",
            "preferred_music_tool": "aiva",
            "preferred_editing_tool": "kapwing"
        }
        update_user_config(new_config)
        
        # 创建异步测试
        async def run_test():
            # 创建请求（不指定模型，应该使用用户偏好）
            request = VideoCreationRequest(
                topic="测试视频",
                style="vlog",
                duration=60,
                target_audience="年轻人",
                key_points=["测试点1", "测试点2"],
                references=["参考1", "参考2"],
                resolution="1080x1920",
                language="zh"
            )
            
            # 初始化中央代理
            central_agent = CentralAgent()
            await central_agent.initialize()
            
            # 模拟处理请求
            with patch('agents.central_agent.CentralAgent._process_video_request') as mock_process:
                # 创建初始消息
                initial_message = Message(
                    message_id="user_request_2",
                    sender=None,
                    receiver=AgentType.CENTRAL,
                    message_type=MessageType.REQUEST,
                    content={
                        "command": "create_video",
                        "parameters": {
                            "session_id": self.session_id,
                            "request": request.dict()
                        }
                    }
                )
                
                # 处理消息
                await central_agent.handle_command(initial_message)
                
                # 验证处理函数被调用
                mock_process.assert_called_once()
                
                # 获取传递给处理函数的参数
                args, kwargs = mock_process.call_args
                processed_request = args[0]
                
                # 验证模型选择是否正确传播
                self.assertEqual(processed_request.video_model, "pika")
                self.assertEqual(processed_request.voice_tool, "playht")
                self.assertEqual(processed_request.music_tool, "aiva")
                self.assertEqual(processed_request.editing_tool, "kapwing")
        
        # 运行异步测试
        asyncio.run(run_test())

    @patch('agents.visual_agent.VideoGenerationAPI')
    def test_error_handling(self, mock_api):
        """测试错误处理"""
        # 设置模拟API抛出异常
        mock_api_instance = MagicMock()
        mock_api_instance.generate_video.side_effect = Exception("模拟API错误")
        mock_api.return_value = mock_api_instance
        
        # 创建异步测试
        async def run_test():
            # 初始化视觉生成代理
            agent = VisualAgent()
            await agent.initialize()
            
            # 创建测试消息
            message = Message(
                message_id="test_error_id",
                sender=AgentType.CENTRAL,
                receiver=AgentType.VISUAL,
                message_type=MessageType.COMMAND,
                content={
                    "command": "generate_videos",
                    "parameters": {
                        "session_id": self.session_id,
                        "script_sections": [
                            {
                                "id": "section1",
                                "content": "测试内容",
                                "visual_description": "测试场景",
                                "duration": 10.0
                            }
                        ],
                        "video_model": "wan",
                        "resolution": "1080x1920",
                        "style": "realistic"
                    }
                }
            )
            
            # 处理消息
            response = await agent.handle_command(message)
            
            # 验证错误响应
            self.assertIsNotNone(response)
            self.assertFalse(response.content.get("success", True))
            self.assertIn("error", response.content)
            self.assertIn("模拟API错误", response.content["error"])
        
        # 运行异步测试
        asyncio.run(run_test())

    def _create_mock_response(self, agent_type: AgentType) -> Message:
        """创建模拟响应消息"""
        return Message(
            message_id=f"response_{agent_type.value}",
            sender=agent_type,
            receiver=AgentType.CENTRAL,
            message_type=MessageType.RESPONSE,
            content={
                "success": True,
                "data": {
                    "agent": agent_type.value,
                    "status": "completed"
                }
            }
        )


if __name__ == "__main__":
    unittest.main() 