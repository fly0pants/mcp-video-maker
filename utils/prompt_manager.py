import os
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Union


class PromptManager:
    def __init__(self, config_path: str = "config/prompts"):
        self.config_path = config_path
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger("PromptManager")
        self.last_load_time: Dict[str, float] = {}
        self._lock = threading.RLock()
        self.load_templates()

    def load_templates(self) -> None:
        """
        Load all JSON prompt template files from the configuration directory.
        """
        with self._lock:
            try:
                if not os.path.exists(self.config_path):
                    self.logger.warning(f"Prompt configuration directory {self.config_path} does not exist. Using empty templates.")
                    return
                
                for filename in os.listdir(self.config_path):
                    if filename.endswith(".json"):
                        file_path = os.path.join(self.config_path, filename)
                        
                        # 检查文件是否已经加载或被修改
                        file_mtime = os.path.getmtime(file_path)
                        if filename in self.last_load_time and file_mtime <= self.last_load_time[filename]:
                            continue  # 文件未修改，跳过
                            
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                key = os.path.splitext(filename)[0]
                                self.templates[key] = data
                                self.last_load_time[filename] = file_mtime
                                self.logger.info(f"Loaded prompt template file: {filename}")
                        except Exception as e:
                            self.logger.error(f"Error loading {filename}: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error scanning prompt configuration directory: {str(e)}")

    def reload_templates(self) -> None:
        """Force reload all template files."""
        with self._lock:
            self.templates.clear()
            self.last_load_time.clear()
            self.load_templates()
            self.logger.info("All prompt templates reloaded")

    def reload_template(self, file_key: str) -> bool:
        """
        Reload a specific template file.
        :param file_key: Template file key (without .json extension)
        :return: True if reload successful, False otherwise
        """
        with self._lock:
            filename = f"{file_key}.json"
            file_path = os.path.join(self.config_path, filename)
            
            if not os.path.exists(file_path):
                self.logger.warning(f"Template file {filename} does not exist")
                return False
                
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.templates[file_key] = data
                    self.last_load_time[filename] = os.path.getmtime(file_path)
                    self.logger.info(f"Reloaded prompt template file: {filename}")
                    return True
            except Exception as e:
                self.logger.error(f"Error reloading {filename}: {str(e)}")
                return False

    def get_template(self, file_key: str, template_key: str) -> str:
        """
        Retrieve a specific prompt template given file key and template key.
        If not found, return an empty string.
        :param file_key: Name of the prompt config file without extension (e.g., 'content_agent_prompts')
        :param template_key: Key for the specific template (e.g., 'create_script')
        :return: Template string
        """
        # 检查文件是否被修改，需要重新加载
        self._check_file_modified(f"{file_key}.json")
        
        with self._lock:
            data = self.templates.get(file_key, {})
            template_info = data.get(template_key, {})
            
            if isinstance(template_info, dict):
                return template_info.get("template", "")
            return ""

    def get_system_role(self, file_key: str, template_key: str) -> str:
        """
        Retrieve the system role for a specific template.
        :param file_key: Template file key
        :param template_key: Template key
        :return: System role string or empty string if not found
        """
        # 检查文件是否被修改，需要重新加载
        self._check_file_modified(f"{file_key}.json")
        
        with self._lock:
            data = self.templates.get(file_key, {})
            system_roles = data.get("system_role", {})
            
            if isinstance(system_roles, dict):
                return system_roles.get(template_key, "")
            return ""

    def get_parameters(self, file_key: str, template_key: str) -> Dict[str, Any]:
        """
        Retrieve parameters for a specific template.
        :param file_key: Template file key
        :param template_key: Template key
        :return: Dictionary of parameters or empty dict if not found
        """
        # 检查文件是否被修改，需要重新加载
        self._check_file_modified(f"{file_key}.json")
        
        with self._lock:
            data = self.templates.get(file_key, {})
            template_info = data.get(template_key, {})
            
            if isinstance(template_info, dict):
                return template_info.get("parameters", {})
            return {}

    def render_template(self, file_key: str, template_key: str, parameters: Dict[str, Any]) -> str:
        """
        Get and render a template with parameters.
        :param file_key: Template file key
        :param template_key: Template key
        :param parameters: Parameters for templating
        :return: Rendered template string
        """
        template = self.get_template(file_key, template_key)
        return self._render(template, parameters)

    def _render(self, template: str, parameters: Dict[str, Any]) -> str:
        """
        Render the template by substituting placeholders using parameters.
        Placeholders are denoted by {{variable}} in the template.
        :param template: The raw template string
        :param parameters: Dictionary of parameter values
        :return: The rendered template string
        """
        rendered = template
        for key, value in parameters.items():
            # 处理列表类型参数 
            if isinstance(value, list):
                if all(isinstance(item, str) for item in value):
                    value = ', '.join(value)
            
            # 进行参数替换
            placeholder = f"{{{{{key}}}}}"
            if placeholder in rendered:
                rendered = rendered.replace(placeholder, str(value))
                
        return rendered

    def _check_file_modified(self, filename: str) -> bool:
        """
        Check if a template file has been modified and reload if necessary.
        :param filename: Template filename with extension
        :return: True if file was reloaded, False otherwise
        """
        with self._lock:
            file_path = os.path.join(self.config_path, filename)
            if not os.path.exists(file_path):
                return False
                
            file_mtime = os.path.getmtime(file_path)
            if filename in self.last_load_time and file_mtime > self.last_load_time[filename]:
                # 文件已被修改，重新加载
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        key = os.path.splitext(filename)[0]
                        self.templates[key] = data
                        self.last_load_time[filename] = file_mtime
                        self.logger.info(f"Auto-reloaded modified template file: {filename}")
                        return True
                except Exception as e:
                    self.logger.error(f"Error auto-reloading {filename}: {str(e)}")
            
            return False


# Singleton instance for convenience
_prompt_manager_instance = None

def get_prompt_manager() -> PromptManager:
    global _prompt_manager_instance
    if _prompt_manager_instance is None:
        _prompt_manager_instance = PromptManager()
    return _prompt_manager_instance 