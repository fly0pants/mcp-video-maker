import os
import json
import logging
import threading
import time
import re
from typing import Dict, Any, Optional, List, Union, Tuple
from string import Formatter


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
        加载配置目录中的所有JSON提示模板文件
        """
        with self._lock:
            try:
                if not os.path.exists(self.config_path):
                    self.logger.warning(f"Prompt配置目录 {self.config_path} 不存在。使用空模板。")
                    return
                
                # 遍历目录及子目录
                for root, dirs, files in os.walk(self.config_path):
                    for filename in files:
                        if filename.endswith(".json"):
                            file_path = os.path.join(root, filename)
                            
                            # 检查文件是否已经加载或被修改
                            file_mtime = os.path.getmtime(file_path)
                            if filename in self.last_load_time and file_mtime <= self.last_load_time[filename]:
                                continue  # 文件未修改，跳过
                                
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    
                                    # 创建相对于config_path的路径作为key
                                    rel_path = os.path.relpath(file_path, self.config_path)
                                    key = os.path.splitext(rel_path)[0]
                                    
                                    self.templates[key] = data
                                    self.last_load_time[filename] = file_mtime
                                    self.logger.info(f"加载提示模板文件: {rel_path}")
                            except Exception as e:
                                self.logger.error(f"加载 {file_path} 出错: {str(e)}")
            except Exception as e:
                self.logger.error(f"扫描提示配置目录出错: {str(e)}")

    def reload_templates(self) -> None:
        """强制重新加载所有模板文件"""
        with self._lock:
            self.templates.clear()
            self.last_load_time.clear()
            self.load_templates()
            self.logger.info("所有提示模板已重新加载")

    def reload_template(self, file_key: str) -> bool:
        """
        重新加载特定模板文件
        :param file_key: 模板文件key（不含.json扩展名）
        :return: 重新加载是否成功
        """
        with self._lock:
            # 将key转换为文件路径
            file_path = os.path.join(self.config_path, f"{file_key}.json")
            
            if not os.path.exists(file_path):
                self.logger.warning(f"模板文件 {file_key}.json 不存在")
                return False
                
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.templates[file_key] = data
                    self.last_load_time[os.path.basename(file_path)] = os.path.getmtime(file_path)
                    self.logger.info(f"重新加载提示模板文件: {file_key}.json")
                    return True
            except Exception as e:
                self.logger.error(f"重新加载 {file_key}.json 出错: {str(e)}")
                return False

    def get_template(self, file_key: str, template_key: str) -> str:
        """
        获取指定的提示模板
        :param file_key: 提示配置文件名，不含扩展名（如 'content_agent_prompts'）
        :param template_key: 特定模板的键（如 'create_script'）
        :return: 模板字符串
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
        获取特定模板的系统角色
        :param file_key: 模板文件key
        :param template_key: 模板key
        :return: 系统角色字符串，如果未找到则返回空字符串
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
        获取特定模板的参数
        :param file_key: 模板文件key
        :param template_key: 模板key
        :return: 参数字典，如果未找到则返回空字典
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
        获取并渲染带参数的模板
        :param file_key: 模板文件key
        :param template_key: 模板key
        :param parameters: 渲染参数
        :return: 渲染后的模板字符串
        """
        template = self.get_template(file_key, template_key)
        return self._render(template, parameters)
    
    def compose_template(self, 
                        main_file_key: str, 
                        main_template_key: str, 
                        components: List[Tuple[str, str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        组合多个模板，创建完整的提示配置
        
        :param main_file_key: 主模板文件key
        :param main_template_key: 主模板key
        :param components: 组件列表，每项为 (file_key, template_key, parameters)
        :return: 组合后的模板配置，包含system_role、template和parameters
        """
        result = {
            "system_role": self.get_system_role(main_file_key, main_template_key),
            "template": self.get_template(main_file_key, main_template_key),
            "parameters": self.get_parameters(main_file_key, main_template_key).copy()
        }
        
        # 如果有组件，进行组合
        if components:
            for file_key, template_key, params in components:
                # 获取组件模板
                component_template = self.get_template(file_key, template_key)
                # 渲染组件模板
                if params:
                    component_content = self._render(component_template, params)
                else:
                    component_content = component_template
                
                # 将组件内容添加到主模板中
                result["template"] += f"\n\n{component_content}"
                
                # 合并参数
                component_params = self.get_parameters(file_key, template_key)
                if component_params:
                    result["parameters"].update(component_params)
                
                # 合并系统角色（可选，这里简单添加）
                component_role = self.get_system_role(file_key, template_key)
                if component_role and result["system_role"]:
                    result["system_role"] += f"\n\n另外，{component_role}"
        
        return result
    
    def build_prompt(self, 
                    file_key: str, 
                    template_key: str, 
                    parameters: Dict[str, Any],
                    include_system_role: bool = True) -> Union[str, List[Dict[str, str]]]:
        """
        构建完整的提示，包括系统角色和用户提示
        
        :param file_key: 模板文件key
        :param template_key: 模板key
        :param parameters: 渲染参数
        :param include_system_role: 是否包含系统角色
        :return: 如果include_system_role为True，返回消息列表；否则仅返回用户提示
        """
        # 渲染用户提示
        user_prompt = self.render_template(file_key, template_key, parameters)
        
        if include_system_role:
            # 获取系统角色
            system_role = self.get_system_role(file_key, template_key)
            
            # 构建消息列表
            messages = []
            if system_role:
                messages.append({"role": "system", "content": system_role})
            messages.append({"role": "user", "content": user_prompt})
            return messages
        else:
            return user_prompt
    
    def get_required_parameters(self, file_key: str, template_key: str) -> List[str]:
        """
        获取模板所需的所有参数名
        
        :param file_key: 模板文件key
        :param template_key: 模板key
        :return: 参数名列表
        """
        template = self.get_template(file_key, template_key)
        if not template:
            return []
        
        # 使用string.Formatter提取参数名
        param_names = []
        for _, field_name, _, _ in Formatter().parse(template):
            if field_name is not None and field_name not in param_names:
                param_names.append(field_name)
        
        return param_names
    
    def list_templates(self, file_key: str = None) -> Dict[str, Any]:
        """
        列出可用的模板
        
        :param file_key: 可选，限制为特定文件的模板
        :return: 模板信息字典
        """
        result = {}
        
        with self._lock:
            if file_key:
                # 仅返回指定文件的模板
                if file_key in self.templates:
                    return {file_key: self.templates[file_key]}
                return {}
            else:
                # 返回所有模板
                return self.templates.copy()
    
    def get_template_info(self, file_key: str, template_key: str) -> Dict[str, Any]:
        """
        获取模板的完整信息
        
        :param file_key: 模板文件key
        :param template_key: 模板key
        :return: 模板信息字典
        """
        # 检查文件是否被修改，需要重新加载
        self._check_file_modified(f"{file_key}.json")
        
        with self._lock:
            data = self.templates.get(file_key, {})
            return {
                "template": self.get_template(file_key, template_key),
                "system_role": self.get_system_role(file_key, template_key),
                "parameters": self.get_parameters(file_key, template_key),
                "required_params": self.get_required_parameters(file_key, template_key)
            }

    def _check_file_modified(self, filename: str) -> None:
        """
        检查文件是否被修改，如果是则重新加载
        :param filename: 文件名
        """
        try:
            file_path = os.path.join(self.config_path, filename)
            if os.path.exists(file_path):
                file_mtime = os.path.getmtime(file_path)
                if filename in self.last_load_time and file_mtime > self.last_load_time[filename]:
                    # 文件已修改，重新加载
                    key = os.path.splitext(filename)[0]
                    self.reload_template(key)
        except Exception as e:
            self.logger.error(f"检查文件修改时出错 {filename}: {str(e)}")

    def _render(self, template: str, parameters: Dict[str, Any]) -> str:
        """
        使用参数渲染模板
        :param template: 模板字符串
        :param parameters: 参数字典
        :return: 渲染后的字符串
        """
        if not template:
            return ""
            
        try:
            # 处理参数，转换非字符串值
            processed_params = {}
            for k, v in parameters.items():
                if isinstance(v, (list, tuple)):
                    processed_params[k] = ", ".join(str(item) for item in v)
                elif isinstance(v, dict):
                    processed_params[k] = json.dumps(v, ensure_ascii=False, indent=2)
                else:
                    processed_params[k] = str(v)
            
            # 使用正则表达式替换所有 {{param}} 格式的变量
            result = template
            for key, value in processed_params.items():
                pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
                result = re.sub(pattern, value, result)
            
            # 查找所有未替换的变量
            remaining_vars = re.findall(r"\{\{\s*(\w+)\s*\}\}", result)
            if remaining_vars:
                self.logger.warning(f"模板中存在未替换的变量: {', '.join(remaining_vars)}")
                
            return result
        except Exception as e:
            self.logger.error(f"渲染模板出错: {str(e)}")
            return template


# 单例实例，方便使用
_prompt_manager_instance = None

def get_prompt_manager() -> PromptManager:
    global _prompt_manager_instance
    if _prompt_manager_instance is None:
        _prompt_manager_instance = PromptManager()
    return _prompt_manager_instance 