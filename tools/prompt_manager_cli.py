#!/usr/bin/env python3
"""
Prompt Manager CLI - 命令行工具，用于管理配置化的prompt模板
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.prompt_manager import get_prompt_manager, PromptManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PromptManagerCLI")


def list_templates(args):
    """列出所有可用的模板文件和模板"""
    prompt_manager = get_prompt_manager()
    
    # 强制重新加载所有模板，确保获取最新状态
    prompt_manager.reload_templates()
    
    templates = prompt_manager.templates
    
    if not templates:
        print("未找到任何模板配置文件")
        return
    
    print(f"找到 {len(templates)} 个模板配置文件:\n")
    
    for file_key, template_data in templates.items():
        print(f"- {file_key}.json:")
        
        for template_key in template_data.keys():
            if template_key != "system_role" and isinstance(template_data[template_key], dict):
                description = template_data[template_key].get("description", "无描述")
                print(f"    • {template_key}: {description}")
        
        print()


def show_template(args):
    """显示特定模板的内容"""
    prompt_manager = get_prompt_manager()
    file_key = args.file
    template_key = args.template
    
    templates = prompt_manager.templates
    
    if file_key not in templates:
        print(f"错误: 找不到模板文件 '{file_key}'")
        sys.exit(1)
    
    if template_key not in templates[file_key] or not isinstance(templates[file_key][template_key], dict):
        print(f"错误: 找不到模板 '{template_key}' 在文件 '{file_key}' 中")
        sys.exit(1)
    
    template_data = templates[file_key][template_key]
    template_content = template_data.get("template", "")
    parameters = template_data.get("parameters", {})
    
    # 获取系统角色信息（如果存在）
    system_role = ""
    if "system_role" in templates[file_key] and template_key in templates[file_key]["system_role"]:
        system_role = templates[file_key]["system_role"][template_key]
    
    print(f"模板: {file_key}.json/{template_key}")
    print(f"描述: {template_data.get('description', '无描述')}")
    
    if system_role:
        print("\n系统角色:")
        print(f"{system_role}")
    
    if parameters:
        print("\n参数配置:")
        for key, value in parameters.items():
            print(f"- {key}: {value}")
    
    print("\n模板内容:")
    print(f"{template_content}")


def edit_template(args):
    """编辑特定模板的内容"""
    file_key = args.file
    template_key = args.template
    prompt_manager = get_prompt_manager()
    
    # 构建文件路径
    config_path = prompt_manager.config_path
    file_path = os.path.join(config_path, f"{file_key}.json")
    
    if not os.path.exists(file_path):
        print(f"错误: 找不到模板文件 '{file_path}'")
        sys.exit(1)
    
    # 读取现有配置
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取模板文件 '{file_path}': {e}")
        sys.exit(1)
    
    # 检查模板是否存在
    if template_key not in data or not isinstance(data[template_key], dict):
        print(f"错误: 找不到模板 '{template_key}' 在文件 '{file_key}' 中")
        sys.exit(1)
    
    # 创建临时文件用于编辑
    import tempfile
    
    template_content = data[template_key].get("template", "")
    
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as temp:
        temp.write(template_content)
        temp_path = temp.name
    
    # 使用默认编辑器打开临时文件
    editor = os.environ.get("EDITOR", "nano")
    try:
        os.system(f"{editor} {temp_path}")
    except Exception as e:
        print(f"错误: 无法启动编辑器: {e}")
        os.unlink(temp_path)
        sys.exit(1)
    
    # 读取编辑后的内容
    try:
        with open(temp_path, "r") as f:
            edited_content = f.read()
    except Exception as e:
        print(f"错误: 无法读取编辑后的文件: {e}")
        os.unlink(temp_path)
        sys.exit(1)
    
    # 删除临时文件
    os.unlink(temp_path)
    
    # 更新模板内容
    data[template_key]["template"] = edited_content
    
    # 保存更新后的配置
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"已更新模板 '{template_key}' 在文件 '{file_key}' 中")
    except Exception as e:
        print(f"错误: 无法保存模板文件 '{file_path}': {e}")
        sys.exit(1)
    
    # 重新加载模板
    prompt_manager.reload_template(file_key)


def create_template_file(args):
    """创建新的模板配置文件"""
    file_key = args.file
    prompt_manager = get_prompt_manager()
    
    # 构建文件路径
    config_path = prompt_manager.config_path
    file_path = os.path.join(config_path, f"{file_key}.json")
    
    if os.path.exists(file_path):
        print(f"错误: 模板文件 '{file_path}' 已存在")
        sys.exit(1)
    
    # 创建目录（如果不存在）
    if not os.path.exists(config_path):
        try:
            os.makedirs(config_path)
        except Exception as e:
            print(f"错误: 无法创建目录 '{config_path}': {e}")
            sys.exit(1)
    
    # 创建新的模板文件
    template_data = {
        "example_template": {
            "description": "示例模板",
            "template": "这是一个示例模板，可以使用{{variable}}格式的变量。\n\n请替换为你需要的内容。",
            "parameters": {
                "temperature": 0.7
            }
        },
        "system_role": {
            "example_template": "这是一个示例系统角色提示。"
        }
    }
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        print(f"已创建新的模板文件 '{file_path}'")
    except Exception as e:
        print(f"错误: 无法创建模板文件 '{file_path}': {e}")
        sys.exit(1)
    
    # 重新加载模板
    prompt_manager.reload_templates()


def create_template(args):
    """在现有文件中创建新的模板"""
    file_key = args.file
    template_key = args.template
    prompt_manager = get_prompt_manager()
    
    # 构建文件路径
    config_path = prompt_manager.config_path
    file_path = os.path.join(config_path, f"{file_key}.json")
    
    if not os.path.exists(file_path):
        print(f"错误: 找不到模板文件 '{file_path}'")
        sys.exit(1)
    
    # 读取现有配置
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取模板文件 '{file_path}': {e}")
        sys.exit(1)
    
    # 检查模板是否已存在
    if template_key in data and isinstance(data[template_key], dict):
        print(f"错误: 模板 '{template_key}' 已存在于文件 '{file_key}' 中")
        sys.exit(1)
    
    # 创建新的模板
    data[template_key] = {
        "description": args.description or f"新模板: {template_key}",
        "template": "在此处输入模板内容，可以使用{{variable}}格式的变量。",
        "parameters": {}
    }
    
    # 添加系统角色（如果提供）
    if args.system_role:
        if "system_role" not in data:
            data["system_role"] = {}
        data["system_role"][template_key] = args.system_role
    
    # 保存更新后的配置
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"已创建新模板 '{template_key}' 在文件 '{file_key}' 中")
    except Exception as e:
        print(f"错误: 无法保存模板文件 '{file_path}': {e}")
        sys.exit(1)
    
    # 重新加载模板
    prompt_manager.reload_template(file_key)
    
    # 提示用户编辑新模板
    print(f"新模板已创建。使用 'edit {file_key} {template_key}' 命令来编辑模板内容")


def update_system_role(args):
    """更新特定模板的系统角色"""
    file_key = args.file
    template_key = args.template
    prompt_manager = get_prompt_manager()
    
    # 构建文件路径
    config_path = prompt_manager.config_path
    file_path = os.path.join(config_path, f"{file_key}.json")
    
    if not os.path.exists(file_path):
        print(f"错误: 找不到模板文件 '{file_path}'")
        sys.exit(1)
    
    # 读取现有配置
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取模板文件 '{file_path}': {e}")
        sys.exit(1)
    
    # 检查模板是否存在
    if template_key not in data or not isinstance(data[template_key], dict):
        print(f"错误: 找不到模板 '{template_key}' 在文件 '{file_key}' 中")
        sys.exit(1)
    
    # 获取当前系统角色
    current_role = ""
    if "system_role" in data and template_key in data["system_role"]:
        current_role = data["system_role"][template_key]
    
    # 创建临时文件用于编辑
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as temp:
        temp.write(current_role)
        temp_path = temp.name
    
    # 使用默认编辑器打开临时文件
    editor = os.environ.get("EDITOR", "nano")
    try:
        os.system(f"{editor} {temp_path}")
    except Exception as e:
        print(f"错误: 无法启动编辑器: {e}")
        os.unlink(temp_path)
        sys.exit(1)
    
    # 读取编辑后的内容
    try:
        with open(temp_path, "r") as f:
            edited_content = f.read()
    except Exception as e:
        print(f"错误: 无法读取编辑后的文件: {e}")
        os.unlink(temp_path)
        sys.exit(1)
    
    # 删除临时文件
    os.unlink(temp_path)
    
    # 更新系统角色
    if "system_role" not in data:
        data["system_role"] = {}
    data["system_role"][template_key] = edited_content
    
    # 保存更新后的配置
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"已更新模板 '{template_key}' 的系统角色")
    except Exception as e:
        print(f"错误: 无法保存模板文件 '{file_path}': {e}")
        sys.exit(1)
    
    # 重新加载模板
    prompt_manager.reload_template(file_key)


def update_parameters(args):
    """更新特定模板的参数配置"""
    file_key = args.file
    template_key = args.template
    prompt_manager = get_prompt_manager()
    
    # 构建文件路径
    config_path = prompt_manager.config_path
    file_path = os.path.join(config_path, f"{file_key}.json")
    
    if not os.path.exists(file_path):
        print(f"错误: 找不到模板文件 '{file_path}'")
        sys.exit(1)
    
    # 读取现有配置
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取模板文件 '{file_path}': {e}")
        sys.exit(1)
    
    # 检查模板是否存在
    if template_key not in data or not isinstance(data[template_key], dict):
        print(f"错误: 找不到模板 '{template_key}' 在文件 '{file_key}' 中")
        sys.exit(1)
    
    # 获取当前参数
    current_params = data[template_key].get("parameters", {})
    
    # 创建临时文件用于编辑
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as temp:
        json.dump(current_params, temp, indent=2, ensure_ascii=False)
        temp_path = temp.name
    
    # 使用默认编辑器打开临时文件
    editor = os.environ.get("EDITOR", "nano")
    try:
        os.system(f"{editor} {temp_path}")
    except Exception as e:
        print(f"错误: 无法启动编辑器: {e}")
        os.unlink(temp_path)
        sys.exit(1)
    
    # 读取编辑后的内容
    try:
        with open(temp_path, "r") as f:
            edited_params = json.load(f)
    except Exception as e:
        print(f"错误: 无法解析编辑后的参数: {e}")
        os.unlink(temp_path)
        sys.exit(1)
    
    # 删除临时文件
    os.unlink(temp_path)
    
    # 更新参数
    data[template_key]["parameters"] = edited_params
    
    # 保存更新后的配置
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"已更新模板 '{template_key}' 的参数配置")
    except Exception as e:
        print(f"错误: 无法保存模板文件 '{file_path}': {e}")
        sys.exit(1)
    
    # 重新加载模板
    prompt_manager.reload_template(file_key)


def render_template(args):
    """渲染模板并展示结果"""
    file_key = args.file
    template_key = args.template
    prompt_manager = get_prompt_manager()
    
    # 构建文件路径
    config_path = prompt_manager.config_path
    file_path = os.path.join(config_path, f"{file_key}.json")
    
    if not os.path.exists(file_path):
        print(f"错误: 找不到模板文件 '{file_path}'")
        sys.exit(1)
    
    # 检查模板是否存在
    templates = prompt_manager.templates
    if file_key not in templates or template_key not in templates[file_key]:
        print(f"错误: 找不到模板 '{template_key}' 在文件 '{file_key}' 中")
        sys.exit(1)
    
    # 解析参数
    parameters = {}
    if args.params:
        for param in args.params:
            if "=" not in param:
                print(f"错误: 参数格式错误 '{param}'，应为 'key=value'")
                sys.exit(1)
            key, value = param.split("=", 1)
            parameters[key] = value
    
    # 渲染模板
    try:
        rendered = prompt_manager.render_template(file_key, template_key, parameters)
        print("\n=== 渲染结果 ===\n")
        print(rendered)
        print("\n=== 结果结束 ===")
    except Exception as e:
        print(f"错误: 无法渲染模板: {e}")
        sys.exit(1)


def reload_templates(args):
    """重新加载所有模板"""
    prompt_manager = get_prompt_manager()
    prompt_manager.reload_templates()
    print("已重新加载所有模板")


def setup_args():
    parser = argparse.ArgumentParser(description="Prompt模板管理器命令行工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # list命令
    list_parser = subparsers.add_parser("list", help="列出所有可用的模板")
    list_parser.set_defaults(func=list_templates)
    
    # show命令
    show_parser = subparsers.add_parser("show", help="显示特定模板的内容")
    show_parser.add_argument("file", help="模板文件名（不含扩展名）")
    show_parser.add_argument("template", help="模板名称")
    show_parser.set_defaults(func=show_template)
    
    # edit命令
    edit_parser = subparsers.add_parser("edit", help="编辑特定模板的内容")
    edit_parser.add_argument("file", help="模板文件名（不含扩展名）")
    edit_parser.add_argument("template", help="模板名称")
    edit_parser.set_defaults(func=edit_template)
    
    # create-file命令
    create_file_parser = subparsers.add_parser("create-file", help="创建新的模板配置文件")
    create_file_parser.add_argument("file", help="新模板文件名（不含扩展名）")
    create_file_parser.set_defaults(func=create_template_file)
    
    # create命令
    create_parser = subparsers.add_parser("create", help="在现有文件中创建新的模板")
    create_parser.add_argument("file", help="模板文件名（不含扩展名）")
    create_parser.add_argument("template", help="新模板名称")
    create_parser.add_argument("--description", "-d", help="模板描述")
    create_parser.add_argument("--system-role", "-s", help="系统角色提示")
    create_parser.set_defaults(func=create_template)
    
    # system-role命令
    system_role_parser = subparsers.add_parser("system-role", help="更新特定模板的系统角色")
    system_role_parser.add_argument("file", help="模板文件名（不含扩展名）")
    system_role_parser.add_argument("template", help="模板名称")
    system_role_parser.set_defaults(func=update_system_role)
    
    # parameters命令
    params_parser = subparsers.add_parser("parameters", help="更新特定模板的参数配置")
    params_parser.add_argument("file", help="模板文件名（不含扩展名）")
    params_parser.add_argument("template", help="模板名称")
    params_parser.set_defaults(func=update_parameters)
    
    # render命令
    render_parser = subparsers.add_parser("render", help="渲染模板并展示结果")
    render_parser.add_argument("file", help="模板文件名（不含扩展名）")
    render_parser.add_argument("template", help="模板名称")
    render_parser.add_argument("--params", "-p", nargs="+", help="参数，格式为key=value")
    render_parser.set_defaults(func=render_template)
    
    # reload命令
    reload_parser = subparsers.add_parser("reload", help="重新加载所有模板")
    reload_parser.set_defaults(func=reload_templates)
    
    return parser


def main():
    parser = setup_args()
    args = parser.parse_args()
    
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 