import asyncio
import uuid
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import random
import logging
import os

from models.message import Message, MessageType, AgentType
from models.video import Script, ScriptSection, ScriptType
from agents.base_agent import BaseAgent
from utils.file_manager import file_manager
from utils.logger import system_logger
from config.config import SYSTEM_CONFIG
import openai
from utils.prompt_manager import get_prompt_manager


class ContentAgent(BaseAgent):
    """
    内容创作代理 - 系统的"编剧"，生成吸引人的短视频脚本
    
    职责:
    - 根据用户输入的主题和目标受众，创作适合TikTok短视频格式的脚本
    - 利用所选视频生成模型的提示扩展功能丰富脚本细节
    - 确保脚本结构能最大化视觉和情感冲击力
    - 支持多语言内容，利用所选模型的文本生成能力嵌入字幕或描述
    """
    
    def __init__(self):
        super().__init__(AgentType.CONTENT, "ContentAgent")
        self.openai_client = None
        
    async def initialize(self):
        """初始化内容创作代理"""
        await super().initialize()
        
        # 初始化OpenAI客户端
        api_key = SYSTEM_CONFIG.get("openai_api_key")
        if api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=api_key)
            self.logger.info("OpenAI client initialized")
        else:
            self.logger.warning("OpenAI API key not found, some features may be limited")
            
        self.logger.info("Content Agent initialized and ready to create scripts")
        
    async def handle_command(self, message: Message) -> Optional[Message]:
        """处理命令消息"""
        action = message.content.get("action")
        
        if action == "create_script":
            # 创建脚本
            parameters = message.content.get("parameters", {})
            session_id = message.content.get("session_id")
            
            if not parameters:
                return self.create_error_response(message, "Missing script parameters")
                
            try:
                script = await self._generate_script(parameters, session_id)
                
                # 保存脚本到文件
                script_json = script.json(ensure_ascii=False, indent=2)
                file_path = await file_manager.save_json_file(
                    data=json.loads(script_json),
                    filename=f"script_{script.id}.json",
                    session_id=session_id,
                    subdir="scripts"
                )
                
                self.logger.info(f"Script created and saved to {file_path}")
                
                return self.create_success_response(message, {
                    "script": json.loads(script_json),
                    "file_path": file_path
                })
            except Exception as e:
                self.logger.error(f"Error creating script: {str(e)}")
                return self.create_error_response(message, f"Error creating script: {str(e)}")
                
        elif action == "revise_script":
            # 修改脚本
            script_data = message.content.get("script")
            feedback = message.content.get("feedback")
            session_id = message.content.get("session_id")
            
            if not script_data:
                return self.create_error_response(message, "Missing script data")
                
            try:
                # 将脚本数据转换为Script对象
                script = Script(**script_data)
                
                # 根据反馈修改脚本
                revised_script = await self._revise_script(script, feedback, session_id)
                
                # 保存修改后的脚本到文件
                script_json = revised_script.json(ensure_ascii=False, indent=2)
                file_path = await file_manager.save_json_file(
                    data=json.loads(script_json),
                    filename=f"script_{revised_script.id}_revised.json",
                    session_id=session_id,
                    subdir="scripts"
                )
                
                self.logger.info(f"Script revised and saved to {file_path}")
                
                return self.create_success_response(message, {
                    "script": json.loads(script_json),
                    "file_path": file_path
                })
            except Exception as e:
                self.logger.error(f"Error revising script: {str(e)}")
                return self.create_error_response(message, f"Error revising script: {str(e)}")
                
        elif action == "analyze_trend":
            # 分析趋势
            topic = message.content.get("topic")
            
            if not topic:
                return self.create_error_response(message, "Missing topic for trend analysis")
                
            try:
                trend_data = await self._analyze_trend(topic)
                
                return self.create_success_response(message, {
                    "trend_data": trend_data
                })
            except Exception as e:
                self.logger.error(f"Error analyzing trend: {str(e)}")
                return self.create_error_response(message, f"Error analyzing trend: {str(e)}")
                
        else:
            return self.create_error_response(message, f"Unknown action: {action}")
    
    async def _generate_script(self, parameters: Dict[str, Any], session_id: str) -> Script:
        """
        生成视频脚本
        
        Args:
            parameters: 脚本参数
            session_id: 会话ID
            
        Returns:
            生成的脚本
        """
        theme = parameters.get("theme", "")
        style = parameters.get("style", "vlog")
        script_type = parameters.get("script_type", "narrative")
        target_audience = parameters.get("target_audience", [])
        duration = parameters.get("duration", 60.0)
        language = parameters.get("language", "zh")
        keywords = parameters.get("keywords", [])
        special_requirements = parameters.get("special_requirements", "")
        
        self.logger.info(f"Generating script for theme: {theme}, style: {style}, type: {script_type}")
        
        # 使用OpenAI生成脚本内容
        if self.openai_client:
            script_content = await self._generate_script_with_openai(
                theme=theme,
                style=style,
                script_type=script_type,
                target_audience=target_audience,
                duration=duration,
                language=language,
                keywords=keywords,
                special_requirements=special_requirements
            )
        else:
            # 如果没有OpenAI客户端，使用模拟数据
            script_content = self._generate_mock_script(
                theme=theme,
                style=style,
                script_type=script_type,
                duration=duration
            )
            
        # 解析生成的内容，创建Script对象
        script_id = f"script_{uuid.uuid4().hex[:8]}"
        
        # 创建脚本片段
        sections = []
        for i, section_data in enumerate(script_content["sections"]):
            section_id = f"section_{uuid.uuid4().hex[:6]}"
            sections.append(ScriptSection(
                id=section_id,
                content=section_data["content"],
                duration=section_data["duration"],
                visual_description=section_data["visual_description"],
                audio_description=section_data.get("audio_description", ""),
                tags=section_data.get("tags", []),
                order=i
            ))
            
        # 创建完整脚本
        script = Script(
            id=script_id,
            title=script_content["title"],
            theme=theme,
            type=ScriptType(script_type),
            target_audience=target_audience,
            sections=sections,
            total_duration=sum(section.duration for section in sections),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            creator_id=f"agent_{self.id}",
            keywords=keywords,
            metadata={
                "style": style,
                "language": language,
                "special_requirements": special_requirements,
                "session_id": session_id
            }
        )
        
        return script
    
    async def _generate_script_with_openai(self, 
                                          theme: str, 
                                          style: str, 
                                          script_type: str, 
                                          target_audience: List[str],
                                          duration: float,
                                          language: str,
                                          keywords: List[str],
                                          special_requirements: str) -> Dict[str, Any]:
        """
        使用OpenAI生成脚本内容
        
        Args:
            theme: 主题
            style: 风格
            script_type: 脚本类型
            target_audience: 目标受众
            duration: 时长（秒）
            language: 语言
            keywords: 关键词
            special_requirements: 特殊要求
            
        Returns:
            脚本内容
        """
        # 计算片段数量，基于总时长
        num_sections = max(1, min(10, int(duration / 10)))
        
        # 获取prompt管理器
        prompt_manager = get_prompt_manager()
        
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
        
        try:
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
                script_id=f"script_{uuid.uuid4().hex[:8]}",
                title=script_data.get("title", f"{theme}短视频脚本"),
                theme=theme,
                style=style,
                type=script_type,
                target_audience=target_audience,
                language=language,
                total_duration=duration,
                keywords=keywords,
                created_at=datetime.now().isoformat(),
                sections=[]
            )
            
            # 添加场景
            for section_data in script_data.get("sections", []):
                section = ScriptSection(
                    section_id=f"section_{uuid.uuid4().hex[:8]}",
                    content=section_data.get("content", ""),
                    visual_description=section_data.get("visual_description", ""),
                    audio_description=section_data.get("audio_description", ""),
                    duration=float(section_data.get("duration", 5.0)),
                    tags=section_data.get("tags", [])
                )
                script.sections.append(section)
                
            # 更新总时长
            script.update_duration()
            
            # 记录日志
            self.logger.info(f"为会话 {session_id} 创建了脚本: '{script.title}', 包含 {len(script.sections)} 个场景")
            
            return script
            
        except Exception as e:
            self.logger.error(f"创建脚本失败: {str(e)}")
            raise
    
    def _generate_mock_script(self, 
                             theme: str, 
                             style: str, 
                             script_type: str, 
                             duration: float) -> Dict[str, Any]:
        """
        生成模拟脚本数据（当OpenAI不可用时使用）
        
        Args:
            theme: 主题
            style: 风格
            script_type: 脚本类型
            duration: 时长（秒）
            
        Returns:
            模拟脚本内容
        """
        # 计算片段数量，基于总时长
        num_sections = max(1, min(10, int(duration / 10)))
        
        # 创建标题
        title = f"{theme}的{style}风格短视频"
        
        # 创建片段
        sections = []
        section_duration = duration / num_sections
        
        for i in range(num_sections):
            section = {
                "content": f"第{i+1}个场景：关于{theme}的内容描述。这是一段{style}风格的{script_type}类型内容。",
                "visual_description": f"画面展示{theme}相关的{style}风格视觉元素。",
                "audio_description": f"背景音乐：{style}风格的轻快音乐。",
                "duration": section_duration,
                "tags": [theme, style, script_type]
            }
            sections.append(section)
            
        return {
            "title": title,
            "sections": sections
        }
    
    async def _revise_script(self, 
                            script: Script, 
                            feedback: str, 
                            session_id: str) -> Script:
        """
        根据反馈修改脚本
        
        Args:
            script: 原始脚本
            feedback: 用户反馈
            session_id: 会话ID
            
        Returns:
            修改后的脚本
        """
        if not self.openai_client:
            # 如果没有OpenAI客户端，简单修改脚本标题
            script.title = f"{script.title} (已根据反馈修改)"
            script.updated_at = datetime.now()
            script.version += 1
            return script
            
        # 获取prompt管理器
        prompt_manager = get_prompt_manager()
        
        # 将脚本转换为JSON字符串
        script_json = script.json(ensure_ascii=False)
        
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
        
        try:
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
                script_id=script.script_id,
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
                sections=[]
            )
            
            # 添加修改后的场景
            section_map = {section.section_id: section for section in script.sections}
            
            for section_data in revised_script_data.get("sections", []):
                # 尽量保留原始场景ID
                original_id = section_data.get("section_id")
                if original_id and original_id in section_map:
                    section_id = original_id
                else:
                    section_id = f"section_{uuid.uuid4().hex[:8]}"
                    
                section = ScriptSection(
                    section_id=section_id,
                    content=section_data.get("content", ""),
                    visual_description=section_data.get("visual_description", ""),
                    audio_description=section_data.get("audio_description", ""),
                    duration=float(section_data.get("duration", 5.0)),
                    tags=section_data.get("tags", [])
                )
                revised_script.sections.append(section)
            
            # 更新总时长
            revised_script.update_duration()
            
            self.logger.info(f"已修改脚本 '{revised_script.title}', 现包含 {len(revised_script.sections)} 个场景")
            
            return revised_script
            
        except Exception as e:
            self.logger.error(f"修改脚本失败: {str(e)}")
            raise
    
    async def _analyze_trend(self, topic: str) -> Dict[str, Any]:
        """
        分析主题趋势
        
        Args:
            topic: 主题
            
        Returns:
            趋势数据
        """
        # 这里应该集成实际的TikTok趋势分析API
        # 目前使用模拟数据
        
        # 模拟热门标签
        popular_tags = [
            f"{topic}挑战",
            f"{topic}教程",
            f"{topic}搞笑",
            f"{topic}日常",
            f"{topic}创意"
        ]
        
        # 模拟热门音乐
        popular_music = [
            {"name": "热门歌曲1", "artist": "艺术家1", "usage_count": random.randint(10000, 1000000)},
            {"name": "热门歌曲2", "artist": "艺术家2", "usage_count": random.randint(10000, 1000000)},
            {"name": "热门歌曲3", "artist": "艺术家3", "usage_count": random.randint(10000, 1000000)}
        ]
        
        # 模拟内容类型分布
        content_distribution = {
            "教程": random.randint(10, 30),
            "搞笑": random.randint(20, 40),
            "日常": random.randint(15, 35),
            "挑战": random.randint(10, 25),
            "创意": random.randint(5, 20)
        }
        
        # 模拟最佳发布时间
        best_posting_times = [
            {"day": "周一", "time": "18:00-20:00"},
            {"day": "周三", "time": "12:00-14:00"},
            {"day": "周五", "time": "20:00-22:00"},
            {"day": "周六", "time": "10:00-12:00"}
        ]
        
        return {
            "topic": topic,
            "popular_tags": popular_tags,
            "popular_music": popular_music,
            "content_distribution": content_distribution,
            "best_posting_times": best_posting_times,
            "analysis_time": datetime.now().isoformat()
        } 