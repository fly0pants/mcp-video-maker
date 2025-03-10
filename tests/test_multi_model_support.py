"""
测试多模型支持功能
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.visual_agent import VisualAgent
from agents.audio_agent import AudioAgent
from models.message import Message, MessageType, AgentType
from config.config import MODEL_CONFIG, AUDIO_CONFIG, API_KEYS, get_available_models


class TestMultiModelSupport(unittest.TestCase):
    """测试系统对多模型支持的功能"""

    def setUp(self):
        """测试前的准备工作"""
        # 确保API密钥存在（使用模拟值）
        self.original_api_keys = API_KEYS.copy()
        API_KEYS.update({
            "KELING_API_KEY": "test_keling_key",
            "PIKA_API_KEY": "test_pika_key",
            "RUNWAY_API_KEY": "test_runway_key",
            "WAN_API_KEY": "test_wan_key",
            "ELEVENLABS_API_KEY": "test_elevenlabs_key",
            "PLAYHT_API_KEY": "test_playht_key",
            "TENCENT_API_KEY": "test_tencent_key",
            "SUNO_API_KEY": "test_suno_key",
            "AIVA_API_KEY": "test_aiva_key",
            "SOUNDRAW_API_KEY": "test_soundraw_key"
        })

    def tearDown(self):
        """测试后的清理工作"""
        # 恢复原始API密钥
        global API_KEYS
        API_KEYS = self.original_api_keys

    def test_get_available_models(self):
        """测试获取可用模型列表功能"""
        # 测试视频模型
        video_models = get_available_models("video")
        self.assertIn("keling", video_models)
        self.assertIn("pika", video_models)
        self.assertIn("runway", video_models)
        self.assertIn("wan", video_models)
        
        # 测试语音工具
        voice_tools = get_available_models("voice")
        self.assertIn("elevenlabs", voice_tools)
        self.assertIn("playht", voice_tools)
        self.assertIn("deepseek_tencent", voice_tools)
        
        # 测试音乐工具
        music_tools = get_available_models("music")
        self.assertIn("suno", music_tools)
        self.assertIn("aiva", music_tools)
        self.assertIn("soundraw", music_tools)

    @patch('agents.visual_agent.VideoGenerationAPI')
    def test_visual_agent_model_selection(self, mock_api):
        """测试视觉生成代理的模型选择功能"""
        # 设置模拟API实例
        mock_api_instance = MagicMock()
        mock_api_instance.generate_video.return_value = {
            "success": True,
            "file_path": "mock_path.mp4",
            "duration": 10.0,
            "resolution": "1080x1920",
            "model": "test_model",
            "model_version": "1.0"
        }
        mock_api.return_value = mock_api_instance
        
        # 创建异步测试
        async def run_test():
            # 初始化视觉生成代理
            agent = VisualAgent()
            await agent.initialize()
            
            # 验证代理初始化了所有支持的模型
            self.assertEqual(len(agent.video_apis), 4)
            self.assertIn("keling", agent.video_apis)
            self.assertIn("pika", agent.video_apis)
            self.assertIn("runway", agent.video_apis)
            self.assertIn("wan", agent.video_apis)
            
            # 创建测试消息
            message = Message(
                message_id="test_id",
                sender=AgentType.CENTRAL,
                receiver=AgentType.VISUAL,
                message_type=MessageType.COMMAND,
                content={
                    "command": "generate_videos",
                    "parameters": {
                        "session_id": "test_session",
                        "script_sections": [
                            {
                                "id": "section1",
                                "content": "测试内容",
                                "visual_description": "测试场景",
                                "duration": 10.0
                            }
                        ],
                        "video_model": "keling",  # 指定使用可灵模型
                        "resolution": "1080x1920",
                        "style": "realistic"
                    }
                }
            )
            
            # 处理消息
            response = await agent.handle_command(message)
            
            # 验证响应
            self.assertIsNotNone(response)
            self.assertTrue(response.content.get("success", False))
            
            # 验证使用了正确的模型
            mock_api_instance.generate_video.assert_called_once()
            
            # 测试模型回退机制
            # 创建一个指定不存在模型的消息
            message.content["parameters"]["video_model"] = "nonexistent_model"
            response = await agent.handle_command(message)
            
            # 验证响应（应该使用可用模型之一）
            self.assertIsNotNone(response)
            self.assertTrue(response.content.get("success", False))
        
        # 运行异步测试
        asyncio.run(run_test())

    @patch('agents.audio_agent.VoiceSynthesisAPI')
    @patch('agents.audio_agent.MusicGenerationAPI')
    def test_audio_agent_tool_selection(self, mock_music_api, mock_voice_api):
        """测试音频生成代理的工具选择功能"""
        # 设置模拟API实例
        mock_voice_api_instance = MagicMock()
        mock_voice_api_instance.synthesize_speech.return_value = {
            "success": True,
            "file_path": "mock_voice.mp3",
            "duration": 5.0,
            "format": "mp3",
            "tool": "test_tool",
            "tool_version": "1.0"
        }
        mock_voice_api.return_value = mock_voice_api_instance
        
        mock_music_api_instance = MagicMock()
        mock_music_api_instance.generate_music.return_value = {
            "success": True,
            "file_path": "mock_music.mp3",
            "duration": 30.0,
            "format": "mp3",
            "tool": "test_tool",
            "tool_version": "1.0"
        }
        mock_music_api.return_value = mock_music_api_instance
        
        # 创建异步测试
        async def run_test():
            # 初始化音频生成代理
            agent = AudioAgent()
            await agent.initialize()
            
            # 验证代理初始化了所有支持的工具
            self.assertEqual(len(agent.voice_apis), 3)
            self.assertIn("elevenlabs", agent.voice_apis)
            self.assertIn("playht", agent.voice_apis)
            self.assertIn("deepseek_tencent", agent.voice_apis)
            
            self.assertEqual(len(agent.music_apis), 3)
            self.assertIn("suno", agent.music_apis)
            self.assertIn("aiva", agent.music_apis)
            self.assertIn("soundraw", agent.music_apis)
            
            # 创建测试消息
            message = Message(
                message_id="test_id",
                sender=AgentType.CENTRAL,
                receiver=AgentType.AUDIO,
                message_type=MessageType.COMMAND,
                content={
                    "command": "generate_audio",
                    "parameters": {
                        "session_id": "test_session",
                        "script_sections": [
                            {
                                "id": "section1",
                                "content": "测试内容",
                                "duration": 10.0
                            }
                        ],
                        "voice_tool": "elevenlabs",  # 指定使用ElevenLabs
                        "music_tool": "suno",        # 指定使用Suno
                        "language": "zh",
                        "voice_character": "xiaoming",
                        "music_style": "pop"
                    }
                }
            )
            
            # 处理消息
            response = await agent.handle_command(message)
            
            # 验证响应
            self.assertIsNotNone(response)
            self.assertTrue(response.content.get("success", False))
            
            # 验证使用了正确的工具
            mock_voice_api_instance.synthesize_speech.assert_called_once()
            mock_music_api_instance.generate_music.assert_called_once()
            
            # 测试工具回退机制
            # 创建一个指定不存在工具的消息
            message.content["parameters"]["voice_tool"] = "nonexistent_tool"
            message.content["parameters"]["music_tool"] = "nonexistent_tool"
            response = await agent.handle_command(message)
            
            # 验证响应（应该使用可用工具之一）
            self.assertIsNotNone(response)
            self.assertTrue(response.content.get("success", False))
        
        # 运行异步测试
        asyncio.run(run_test())

    def test_model_config_parameters(self):
        """测试模型配置参数的完整性"""
        # 检查视频模型配置
        for model_name, config in MODEL_CONFIG.items():
            self.assertIn("name", config)
            self.assertIn("base_url", config)
            self.assertIn("version", config)
            self.assertIn("max_duration", config)
            self.assertIn("supported_resolutions", config)
            self.assertIn("supported_styles", config)
            self.assertIn("default_style", config)
            self.assertIn("fps", config)
            self.assertIn("temperature", config)
            self.assertIn("top_p", config)
            self.assertIn("timeout", config)
            self.assertIn("max_retries", config)
            self.assertIn("rate_limit", config)
        
        # 检查音频工具配置
        for tool_name, config in AUDIO_CONFIG.items():
            self.assertIn("name", config)
            self.assertIn("base_url", config)
            self.assertIn("version", config)
            self.assertIn("timeout", config)
            self.assertIn("max_retries", config)
            
            # 语音合成工具特有配置
            if tool_name in ["elevenlabs", "playht", "deepseek_tencent"]:
                self.assertIn("speed", config)
                self.assertIn("pitch", config)
                self.assertIn("volume", config)
                self.assertIn("voices", config)
            
            # 音乐生成工具特有配置
            if tool_name in ["suno", "aiva", "soundraw"]:
                self.assertIn("tempo", config)
                self.assertIn("intensity", config)
                self.assertIn("styles", config)


if __name__ == "__main__":
    unittest.main() 