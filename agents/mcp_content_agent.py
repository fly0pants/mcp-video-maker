import json
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.mcp import (
    MCPMessage, MCPMessageType, MCPStatus, MCPPriority, MCPCommand, MCPResponse,
    create_command_message
)
from agents.mcp_base_agent import MCPBaseAgent
from models.video import Script, ScriptSection
from utils.prompt_manager import get_prompt_manager
import openai

# 检查是否处于测试模式
def is_test_mode():
    try:
        import sys
        return any("test" in arg for arg in sys.argv)
    except:
        return False


class MCPContentAgent(MCPBaseAgent):
    """基于MCP协议的内容生成代理，负责创建和修改视频脚本"""
    
    def __init__(self):
        """初始化内容代理"""
        super().__init__(
            agent_id="content_agent",
            agent_name="Content Generation Agent"
        )
        self.openai_client = None
        self.test_mode = is_test_mode()
        
    async def on_start(self):
        """代理启动时的自定义逻辑，初始化OpenAI客户端"""
        try:
            # 从环境变量读取API密钥
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            
            # 初始化OpenAI客户端
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.logger.warning("OpenAI API Key not found, using mock mode")
                # 模拟模式，不需要实际API密钥
                self.openai_client = None
            else:
                # 修复: 不使用proxies参数
                self.openai_client = openai.AsyncOpenAI(api_key=api_key)
                self.logger.info("OpenAI client initialized")
                
        except Exception as e:
            self.logger.error(f"Error initializing OpenAI client: {str(e)}")
            
    async def handle_command(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理命令消息
        
        Args:
            message: 命令消息
            
        Returns:
            响应消息
        """
        # 验证是否为命令消息
        if message.header.message_type != MCPMessageType.COMMAND or not isinstance(message.body, MCPCommand):
            return message.create_error_response(
                error_code="INVALID_MESSAGE",
                error_message="Expected a command message"
            )
        
        # 根据命令类型分发处理
        command = message.body
        session_id = message.header.session_id or "default_session"
        
        try:
            if command.action == "create_script":
                # 创建视频脚本
                script = await self._create_script(command.parameters, session_id)
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message="Script created successfully",
                    data={"script": script.dict() if script else None}
                )
                
            elif command.action == "modify_script":
                # 修改视频脚本
                script_data = command.parameters.get("script")
                feedback = command.parameters.get("feedback")
                
                if not script_data or not feedback:
                    return message.create_error_response(
                        error_code="INVALID_PARAMETERS",
                        error_message="Missing required parameters: script and feedback"
                    )
                
                # 将字典转换为Script对象
                original_script = Script(**script_data)
                
                # 修改脚本
                modified_script = await self._modify_script(original_script, feedback, session_id)
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message="Script modified successfully",
                    data={"script": modified_script.dict() if modified_script else None}
                )
                
            elif command.action == "generate_storyboard_content":
                # 生成分镜内容
                script_data = command.parameters.get("script")
                style = command.parameters.get("style", "storyboard")
                
                if not script_data:
                    return message.create_error_response(
                        error_code="INVALID_PARAMETERS",
                        error_message="Missing required parameter: script"
                    )
                
                # 将字典转换为Script对象
                script = Script(**script_data)
                
                # 生成分镜内容
                storyboard_data = await self._generate_storyboard_content(script, style, session_id)
                
                # 返回响应
                return message.create_response(
                    success=True,
                    message="Storyboard content generated successfully",
                    data={"storyboard_data": storyboard_data}
                )
                
            else:
                return message.create_error_response(
                    error_code="UNKNOWN_COMMAND",
                    error_message=f"Unknown action: {command.action}"
                )
                
        except Exception as e:
            self.logger.error(f"Error handling command: {str(e)}")
            return message.create_error_response(
                error_code="COMMAND_ERROR",
                error_message=f"Error processing command: {str(e)}"
            )
    
    async def _create_script(self, parameters: Dict[str, Any], session_id: str) -> Optional[Script]:
        """
        创建视频脚本
        
        Args:
            parameters: 创建脚本的参数
            session_id: 会话ID
            
        Returns:
            创建的脚本对象
        """
        try:
            # 提取参数
            theme = parameters.get("theme", "")
            style = parameters.get("style", "幽默")
            script_type = parameters.get("script_type", "知识普及")
            target_audience = parameters.get("target_audience", ["年轻人", "学生"])
            duration = parameters.get("duration", 60.0)
            language = parameters.get("language", "zh")
            keywords = parameters.get("keywords", [])
            special_requirements = parameters.get("special_requirements", "")
            
            self.logger.info(f"Creating script for theme: {theme}, style: {style}")
            
            # 获取prompt管理器
            prompt_manager = get_prompt_manager()
            
            # 计算片段数量，基于总时长
            num_sections = max(1, min(10, int(duration / 10)))
            
            if self.openai_client:
                # 使用OpenAI创建脚本
                # 准备模板参数
                template_params = {
                    "theme": theme,
                    "style": style,
                    "script_type": script_type,
                    "target_audience": target_audience,
                    "duration": duration,
                    "language": language,
                    "keywords": keywords if keywords else "无特定关键词",
                    "special_requirements": special_requirements if special_requirements else "无特殊要求",
                    "num_sections": num_sections
                }
                
                # 渲染prompt模板
                prompt = prompt_manager.render_template(
                    file_key="content_agent_prompts", 
                    template_key="create_script", 
                    parameters=template_params
                )
                
                # 获取系统角色提示
                system_role = prompt_manager.get_system_role(
                    file_key="content_agent_prompts",
                    template_key="create_script"
                )
                
                # 调用API
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_role},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                # 解析响应内容
                content = response.choices[0].message.content
                script_data = json.loads(content)
                
                # 创建脚本对象
                script = Script(
                    id=f"script_{uuid.uuid4().hex[:8]}",
                    title=script_data.get("title", f"{theme}短视频脚本"),
                    theme=theme,
                    style=style,
                    type=script_type,
                    target_audience=target_audience,
                    language=language,
                    total_duration=duration,
                    keywords=keywords,
                    created_at=datetime.now().isoformat(),
                    creator_id=f"agent_{self.agent_id}",
                    sections=[]
                )
                
                # 添加场景
                for i, section_data in enumerate(script_data.get("sections", [])):
                    section = ScriptSection(
                        id=f"section_{uuid.uuid4().hex[:8]}",
                        content=section_data.get("content", ""),
                        visual_description=section_data.get("visual_description", ""),
                        audio_description=section_data.get("audio_description", ""),
                        duration=float(section_data.get("duration", 5.0)),
                        tags=section_data.get("tags", []),
                        order=i
                    )
                    script.sections.append(section)
                    
                # 更新总时长
                script.update_duration()
                
                self.logger.info(f"Created script '{script.title}' with {len(script.sections)} sections")
                
                return script
                
            else:
                # 使用模拟数据
                return self._generate_mock_script(theme, style, script_type, duration)
            
        except Exception as e:
            self.logger.error(f"Error creating script: {str(e)}")
            raise
    
    def _generate_mock_script(self, theme: str, style: str, script_type: str, duration: float) -> Script:
        """
        生成模拟脚本（当无法使用OpenAI API时）
        
        Args:
            theme: 脚本主题
            style: 脚本风格
            script_type: 脚本类型
            duration: 脚本时长
            
        Returns:
            模拟的脚本对象
        """
        self.logger.info("Using mock script generation")
        
        # 生成模拟脚本ID
        script_id = f"mock_script_{uuid.uuid4().hex[:8]}"
        
        # 计算场景数量
        num_sections = max(1, min(10, int(duration / 10)))
        
        # 创建脚本对象
        script = Script(
            id=script_id,
            title=f"{theme} - {style}风格短视频",
            theme=theme,
            style=style,
            type=script_type,
            target_audience=["年轻人", "学生"],
            language="zh",
            total_duration=duration,
            keywords=[theme, style, script_type],
            created_at=datetime.now().isoformat(),
            creator_id=f"agent_{self.agent_id}",
            sections=[]
        )
        
        # 添加模拟场景
        section_duration = duration / num_sections
        for i in range(num_sections):
            section = ScriptSection(
                id=f"mock_section_{i}_{uuid.uuid4().hex[:6]}",
                content=f"这是关于{theme}的第{i+1}个场景，采用{style}风格。",
                visual_description=f"展示{theme}相关的{style}风格图像",
                audio_description=f"背景音乐：{style}风格轻音乐",
                duration=section_duration,
                tags=[theme, style, f"场景{i+1}"],
                order=i
            )
            script.sections.append(section)
        
        # 更新总时长
        script.update_duration()
        
        self.logger.info(f"Generated mock script '{script.title}' with {len(script.sections)} sections")
        
        return script
    
    async def _modify_script(self, script: Script, feedback: str, session_id: str) -> Optional[Script]:
        """
        根据反馈修改脚本
        
        Args:
            script: 原始脚本
            feedback: 用户反馈
            session_id: 会话ID
            
        Returns:
            修改后的脚本
        """
        try:
            self.logger.info(f"Modifying script '{script.title}' based on feedback")
            
            # 获取prompt管理器
            prompt_manager = get_prompt_manager()
            
            if self.openai_client:
                # 将脚本转换为JSON字符串
                script_json = script.model_dump_json(indent=2)
                
                # 准备模板参数并渲染
                template_params = {
                    "script_json": script_json,
                    "feedback": feedback
                }
                
                # 渲染prompt模板
                prompt = prompt_manager.render_template(
                    file_key="content_agent_prompts", 
                    template_key="modify_script", 
                    parameters=template_params
                )
                
                # 获取系统角色提示
                system_role = prompt_manager.get_system_role(
                    file_key="content_agent_prompts",
                    template_key="modify_script"
                )
                
                # 调用API
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_role},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                # 解析响应
                content = response.choices[0].message.content
                revised_script_data = json.loads(content)
                
                # 创建修改后的脚本对象，保留原始ID
                revised_script = Script(
                    id=script.id,
                    title=revised_script_data.get("title", script.title),
                    theme=revised_script_data.get("theme", script.theme),
                    style=revised_script_data.get("style", script.style),
                    type=revised_script_data.get("type", script.type),
                    target_audience=revised_script_data.get("target_audience", script.target_audience),
                    language=revised_script_data.get("language", script.language),
                    total_duration=revised_script_data.get("total_duration", script.total_duration),
                    keywords=revised_script_data.get("keywords", script.keywords),
                    created_at=script.created_at,
                    updated_at=datetime.now().isoformat(),
                    creator_id=script.creator_id,
                    sections=[]
                )
                
                # 添加修改后的场景
                section_map = {section.id: section for section in script.sections}
                
                for i, section_data in enumerate(revised_script_data.get("sections", [])):
                    # 尽量保留原始场景ID
                    original_id = section_data.get("id")
                    if original_id and original_id in section_map:
                        section_id = original_id
                    else:
                        section_id = f"section_{uuid.uuid4().hex[:8]}"
                        
                    section = ScriptSection(
                        id=section_id,
                        content=section_data.get("content", ""),
                        visual_description=section_data.get("visual_description", ""),
                        audio_description=section_data.get("audio_description", ""),
                        duration=float(section_data.get("duration", 5.0)),
                        tags=section_data.get("tags", []),
                        order=i
                    )
                    revised_script.sections.append(section)
                
                # 更新总时长
                revised_script.update_duration()
                
                self.logger.info(f"Modified script '{revised_script.title}', now with {len(revised_script.sections)} sections")
                
                return revised_script
                
            else:
                # 简单地添加反馈到脚本标题
                script.title = f"{script.title} (已根据反馈修改)"
                script.updated_at = datetime.now().isoformat()
                
                # 修改第一个场景的内容，添加反馈信息
                if script.sections:
                    script.sections[0].content = f"{script.sections[0].content}\n[按照反馈 '{feedback}' 修改]"
                
                self.logger.info(f"Applied mock modifications to script '{script.title}'")
                
                return script
            
        except Exception as e:
            self.logger.error(f"Error modifying script: {str(e)}")
            raise
    
    async def _analyze_trend(self, topic: str) -> Dict[str, Any]:
        """
        分析话题趋势
        
        Args:
            topic: 话题
            
        Returns:
            趋势分析结果
        """
        self.logger.info(f"Analyzing trend for topic: {topic}")
        
        # 这里使用模拟数据，实际应用中可以连接到实时数据源
        return {
            "topic": topic,
            "popularity_score": 8.5,
            "trending_hashtags": [f"#{topic}", f"#{topic}挑战", f"#{topic}2023"],
            "recent_growth": "+15%",
            "audience_demographics": {
                "age_groups": ["18-24", "25-34"],
                "gender_ratio": {"male": 45, "female": 55},
                "top_regions": ["北京", "上海", "广州"]
            },
            "content_suggestions": [
                f"{topic}挑战赛",
                f"{topic}小知识",
                f"如何正确理解{topic}"
            ],
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    async def _generate_storyboard_content(self, script: Script, style: str, session_id: str) -> Dict[str, Any]:
        """
        生成分镜内容
        
        Args:
            script: 脚本对象
            style: 分镜风格
            session_id: 会话ID
            
        Returns:
            分镜数据
        """
        self.logger.info(f"Generating storyboard content for script: {script.id} with style: {style}")
        
        try:
            if self.openai_client:
                # 获取提示管理器
                prompt_manager = get_prompt_manager()
                
                # 准备生成分镜的提示参数
                script_sections_content = ""
                for section in script.sections:
                    script_sections_content += f"场景 {section.order + 1}:\n"
                    script_sections_content += f"内容: {section.content}\n"
                    script_sections_content += f"视觉描述: {section.visual_description}\n"
                    if section.audio_description:
                        script_sections_content += f"音频描述: {section.audio_description}\n"
                    script_sections_content += "\n"
                
                prompt_params = {
                    "title": script.title,
                    "theme": script.theme,
                    "type": script.type,
                    "style": style,
                    "duration": script.total_duration,
                    "script_content": script_sections_content,
                    "storyboard_style": style
                }
                
                # 渲染提示模板
                prompt = prompt_manager.render_template(
                    "storyboard_agent_prompts", 
                    "create_storyboard", 
                    prompt_params
                )
                system_role = prompt_manager.get_system_role("storyboard_agent_prompts", "create_storyboard")
                
                # 调用OpenAI API
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_role},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4000
                )
                
                storyboard_text = response.choices[0].message.content
                
                # 解析生成的分镜内容
                # 这里只返回原始内容，具体的解析和创建Storyboard对象的工作交给MCPStoryboardAgent
                storyboard_data = {
                    "raw_content": storyboard_text,
                    "style": style,
                    "frames": self._parse_storyboard_frames(storyboard_text, script),
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "model": "gpt-4"
                    }
                }
                
                return storyboard_data
            else:
                # 模拟分镜数据
                return self._generate_mock_storyboard_data(script, style)
                
        except Exception as e:
            self.logger.error(f"Error generating storyboard content: {str(e)}")
            raise
    
    def _parse_storyboard_frames(self, storyboard_text: str, script: Script) -> List[Dict[str, Any]]:
        """
        从生成的文本中解析分镜帧
        
        Args:
            storyboard_text: 生成的分镜文本
            script: 脚本对象
            
        Returns:
            分镜帧列表
        """
        # 简单实现：为每个脚本场景创建一个分镜帧
        frames = []
        
        for i, section in enumerate(script.sections):
            frame_id = f"frame_{uuid.uuid4().hex[:8]}"
            
            frame = {
                "id": frame_id,
                "order": i,
                "script_section_id": section.id,
                "frame_type": "SCENE",
                "shot_type": "MEDIUM",
                "content": section.content,
                "visual_description": section.visual_description,
                "audio_description": section.audio_description,
                "duration": section.duration or 5.0,
                "metadata": {}
            }
            
            frames.append(frame)
        
        return frames
    
    def _generate_mock_storyboard_data(self, script: Script, style: str) -> Dict[str, Any]:
        """
        生成模拟的分镜数据
        
        Args:
            script: 脚本对象
            style: 分镜风格
            
        Returns:
            模拟的分镜数据
        """
        frames = self._parse_storyboard_frames("", script)
        
        return {
            "raw_content": f"模拟分镜内容 - {script.title}",
            "style": style,
            "frames": frames,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "mock": True
            }
        } 