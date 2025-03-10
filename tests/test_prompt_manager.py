import os
import json
import tempfile
import shutil
import pytest
from unittest.mock import patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.prompt_manager import PromptManager


class TestPromptManager:
    """PromptManager单元测试"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    def sample_template_file(self, temp_config_dir):
        """创建示例模板文件"""
        file_path = os.path.join(temp_config_dir, "test_prompts.json")
        template_data = {
            "test_template": {
                "description": "测试模板",
                "template": "这是一个测试模板，{{param1}}，{{param2}}。",
                "parameters": {
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            },
            "system_role": {
                "test_template": "测试系统角色"
            }
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, ensure_ascii=False)
            
        return file_path
    
    def test_load_templates(self, temp_config_dir, sample_template_file):
        """测试加载模板"""
        # 创建PromptManager实例，使用临时目录
        prompt_manager = PromptManager(config_path=temp_config_dir)
        
        # 验证模板已加载
        assert "test_prompts" in prompt_manager.templates
        assert "test_template" in prompt_manager.templates["test_prompts"]
        
        # 验证模板内容
        template = prompt_manager.get_template("test_prompts", "test_template")
        assert "这是一个测试模板" in template
        
        # 验证系统角色
        system_role = prompt_manager.get_system_role("test_prompts", "test_template")
        assert system_role == "测试系统角色"
        
        # 验证参数
        params = prompt_manager.get_parameters("test_prompts", "test_template")
        assert params["temperature"] == 0.7
        assert params["top_p"] == 0.9
    
    def test_render_template(self, temp_config_dir, sample_template_file):
        """测试渲染模板"""
        prompt_manager = PromptManager(config_path=temp_config_dir)
        
        # 测试渲染
        rendered = prompt_manager.render_template(
            file_key="test_prompts",
            template_key="test_template",
            parameters={"param1": "值1", "param2": "值2"}
        )
        
        assert "这是一个测试模板，值1，值2。" == rendered
    
    def test_render_with_list_parameter(self, temp_config_dir, sample_template_file):
        """测试使用列表参数渲染模板"""
        prompt_manager = PromptManager(config_path=temp_config_dir)
        
        # 使用列表参数测试渲染
        rendered = prompt_manager._render(
            template="列表参数: {{list_param}}",
            parameters={"list_param": ["项目1", "项目2", "项目3"]}
        )
        
        assert "列表参数: 项目1, 项目2, 项目3" == rendered
    
    def test_reload_templates(self, temp_config_dir, sample_template_file):
        """测试重新加载模板"""
        prompt_manager = PromptManager(config_path=temp_config_dir)
        
        # 修改模板文件
        file_path = os.path.join(temp_config_dir, "test_prompts.json")
        template_data = {
            "test_template": {
                "description": "修改后的测试模板",
                "template": "这是修改后的测试模板，{{param1}}，{{param2}}。",
                "parameters": {
                    "temperature": 0.8
                }
            }
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, ensure_ascii=False)
        
        # 强制重新加载
        prompt_manager.reload_templates()
        
        # 验证模板已更新
        template = prompt_manager.get_template("test_prompts", "test_template")
        assert "这是修改后的测试模板" in template
        
        # 验证参数已更新
        params = prompt_manager.get_parameters("test_prompts", "test_template")
        assert params["temperature"] == 0.8
        assert "top_p" not in params
    
    def test_auto_reload_modified_file(self, temp_config_dir, sample_template_file):
        """测试自动重新加载被修改的文件"""
        prompt_manager = PromptManager(config_path=temp_config_dir)
        
        # 获取初始模板
        orig_template = prompt_manager.get_template("test_prompts", "test_template")
        
        # 模拟延迟，确保文件修改时间有变化
        import time
        time.sleep(0.1)
        
        # 修改模板文件
        file_path = os.path.join(temp_config_dir, "test_prompts.json")
        template_data = {
            "test_template": {
                "description": "自动重载测试",
                "template": "这是自动重载的测试模板。",
                "parameters": {}
            }
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, ensure_ascii=False)
        
        # 获取模板，应触发自动重载
        new_template = prompt_manager.get_template("test_prompts", "test_template")
        
        # 验证模板已自动更新
        assert new_template != orig_template
        assert "这是自动重载的测试模板" in new_template 