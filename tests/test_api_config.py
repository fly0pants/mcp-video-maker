"""
测试API模型配置的灵活性
"""

import os
import sys
import unittest
from unittest.mock import patch

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import (
    MODEL_CONFIG, 
    AUDIO_CONFIG, 
    EDITING_CONFIG, 
    API_KEYS, 
    USER_CONFIG, 
    update_user_config, 
    get_model_config
)


class TestAPIConfigFlexibility(unittest.TestCase):
    """测试API模型配置的灵活性"""

    def setUp(self):
        """测试前的准备工作"""
        # 保存原始配置
        self.original_user_config = USER_CONFIG.copy()
        self.original_api_keys = API_KEYS.copy()

    def tearDown(self):
        """测试后的清理工作"""
        # 恢复原始配置
        global USER_CONFIG, API_KEYS
        USER_CONFIG = self.original_user_config
        API_KEYS = self.original_api_keys

    def test_user_config_update(self):
        """测试用户配置更新功能"""
        # 初始值
        self.assertEqual(USER_CONFIG["preferred_video_model"], "wan")
        self.assertEqual(USER_CONFIG["preferred_voice_tool"], "elevenlabs")
        self.assertEqual(USER_CONFIG["preferred_resolution"], "1080x1920")
        
        # 更新配置
        new_config = {
            "preferred_video_model": "pika",
            "preferred_voice_tool": "playht",
            "preferred_resolution": "720x1280",
            "auto_publish": True
        }
        update_user_config(new_config)
        
        # 验证更新后的值
        self.assertEqual(USER_CONFIG["preferred_video_model"], "pika")
        self.assertEqual(USER_CONFIG["preferred_voice_tool"], "playht")
        self.assertEqual(USER_CONFIG["preferred_resolution"], "720x1280")
        self.assertEqual(USER_CONFIG["auto_publish"], True)
        
        # 验证未更新的值保持不变
        self.assertEqual(USER_CONFIG["preferred_music_tool"], "suno")
        self.assertEqual(USER_CONFIG["theme"], "light")

    def test_get_model_config(self):
        """测试获取模型配置功能"""
        # 获取视频模型配置
        keling_config = get_model_config("keling")
        self.assertEqual(keling_config["name"], "可灵视频生成")
        self.assertEqual(keling_config["version"], "1.0")
        self.assertEqual(keling_config["max_duration"], 60)
        
        # 获取语音工具配置
        elevenlabs_config = get_model_config("elevenlabs")
        self.assertEqual(elevenlabs_config["name"], "ElevenLabs")
        self.assertEqual(elevenlabs_config["version"], "1.0")
        self.assertIn("zh", elevenlabs_config["voices"])
        
        # 获取音乐工具配置
        suno_config = get_model_config("suno")
        self.assertEqual(suno_config["name"], "Suno AI")
        self.assertEqual(suno_config["version"], "1.0")
        self.assertIn("pop", suno_config["styles"])
        
        # 获取编辑工具配置
        runway_config = get_model_config("runway")
        self.assertEqual(runway_config["name"], "Runway")
        self.assertEqual(runway_config["version"], "1.0")
        self.assertIn("color_grading", runway_config["supported_effects"])
        
        # 获取不存在的模型配置
        nonexistent_config = get_model_config("nonexistent")
        self.assertEqual(nonexistent_config, {})

    def test_model_config_override(self):
        """测试模型配置覆盖功能"""
        # 修改视频模型配置
        original_keling_config = MODEL_CONFIG["keling"].copy()
        MODEL_CONFIG["keling"]["temperature"] = 0.9
        MODEL_CONFIG["keling"]["top_p"] = 0.95
        MODEL_CONFIG["keling"]["fps"] = 30
        
        # 验证修改生效
        self.assertEqual(MODEL_CONFIG["keling"]["temperature"], 0.9)
        self.assertEqual(MODEL_CONFIG["keling"]["top_p"], 0.95)
        self.assertEqual(MODEL_CONFIG["keling"]["fps"], 30)
        
        # 恢复原始配置
        MODEL_CONFIG["keling"] = original_keling_config

    def test_api_key_override(self):
        """测试API密钥覆盖功能"""
        # 修改API密钥
        API_KEYS["KELING_API_KEY"] = "new_test_key"
        
        # 验证修改生效
        self.assertEqual(API_KEYS["KELING_API_KEY"], "new_test_key")

    @patch.dict(os.environ, {"KELING_API_KEY": "env_test_key"})
    def test_api_key_from_env(self):
        """测试从环境变量获取API密钥"""
        # 重新导入配置模块以应用环境变量
        import importlib
        import config.config
        importlib.reload(config.config)
        
        # 验证环境变量中的API密钥被正确加载
        self.assertEqual(config.config.API_KEYS["KELING_API_KEY"], "env_test_key")

    def test_model_parameter_validation(self):
        """测试模型参数验证"""
        # 检查视频模型参数范围
        for model_name, config in MODEL_CONFIG.items():
            self.assertGreater(config["max_duration"], 0)
            self.assertGreaterEqual(config["temperature"], 0.0)
            self.assertLessEqual(config["temperature"], 1.0)
            self.assertGreaterEqual(config["top_p"], 0.0)
            self.assertLessEqual(config["top_p"], 1.0)
            self.assertGreater(config["fps"], 0)
            self.assertGreater(config["timeout"], 0)
            self.assertGreater(config["max_retries"], 0)
        
        # 检查音频工具参数范围
        for tool_name, config in AUDIO_CONFIG.items():
            self.assertGreater(config["timeout"], 0)
            self.assertGreater(config["max_retries"], 0)
            
            # 语音合成工具特有参数
            if tool_name in ["elevenlabs", "playht", "deepseek_tencent"]:
                self.assertGreaterEqual(config["speed"], 0.5)
                self.assertLessEqual(config["speed"], 2.0)
                self.assertGreaterEqual(config["pitch"], -10)
                self.assertLessEqual(config["pitch"], 10)
                self.assertGreaterEqual(config["volume"], 0.1)
                self.assertLessEqual(config["volume"], 2.0)
            
            # 音乐生成工具特有参数
            if tool_name in ["suno", "aiva", "soundraw"]:
                self.assertIn(config["tempo"], ["slow", "medium", "fast"])
                self.assertGreaterEqual(config["intensity"], 0.1)
                self.assertLessEqual(config["intensity"], 1.0)


if __name__ == "__main__":
    unittest.main() 