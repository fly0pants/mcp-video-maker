"""
内容创作代理
负责生成视频脚本、文案和创意内容
"""

import asyncio
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.mcp_base_agent import MCPBaseAgent
from models.mcp import MCPCommand, MCPMessage


class ContentAgent(MCPBaseAgent):
    """
    内容创作代理
    
    职责：
    1. 根据主题和风格生成视频脚本
    2. 创建分镜描述
    3. 生成字幕和文案
    4. 提供多个创意方案供用户选择
    """
    
    def __init__(self):
        super().__init__(agent_id="content_agent", agent_name="内容创作代理")
        
        # 命令处理器映射
        self._command_handlers = {
            "create_script": self._handle_create_script,
            "generate_storyboard": self._handle_generate_storyboard,
            "refine_script": self._handle_refine_script,
            "generate_captions": self._handle_generate_captions,
            "suggest_hooks": self._handle_suggest_hooks,
        }
        
        # 风格模板
        self._style_templates = {
            "幽默": {
                "tone": "轻松幽默",
                "elements": ["反转", "梗", "夸张表情"],
                "structure": "hook -> 铺垫 -> 反转 -> 结尾金句"
            },
            "励志": {
                "tone": "积极向上",
                "elements": ["个人故事", "名言金句", "情感共鸣"],
                "structure": "痛点 -> 转折 -> 成长 -> 号召"
            },
            "教育": {
                "tone": "专业易懂",
                "elements": ["数据", "案例", "步骤"],
                "structure": "问题 -> 原理 -> 方法 -> 总结"
            },
            "娱乐": {
                "tone": "活泼有趣",
                "elements": ["热梗", "流行元素", "互动"],
                "structure": "吸睛开场 -> 高潮 -> 互动引导"
            },
            "科技": {
                "tone": "专业前沿",
                "elements": ["技术原理", "应用场景", "未来展望"],
                "structure": "现象 -> 技术 -> 影响 -> 展望"
            },
            "生活": {
                "tone": "温馨真实",
                "elements": ["日常场景", "实用技巧", "情感共鸣"],
                "structure": "场景引入 -> 内容展开 -> 实用总结"
            },
        }
    
    async def handle_command(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理命令消息"""
        if not isinstance(message.body, MCPCommand):
            return message.create_error_response(
                error_code="INVALID_MESSAGE",
                error_message="预期收到命令消息"
            )
        
        command = message.body
        action = command.action
        
        self.logger.info(f"收到命令: {action}")
        
        handler = self._command_handlers.get(action)
        if not handler:
            return message.create_error_response(
                error_code="UNKNOWN_COMMAND",
                error_message=f"未知命令: {action}"
            )
        
        try:
            result = await handler(command.parameters, message.header.session_id)
            return message.create_response(
                success=True,
                message=f"命令 {action} 执行成功",
                data=result
            )
        except Exception as e:
            self.logger.error(f"执行命令 {action} 时发生错误: {str(e)}", exc_info=True)
            return message.create_error_response(
                error_code="EXECUTION_ERROR",
                error_message=f"执行命令时发生错误: {str(e)}"
            )
    
    async def _handle_create_script(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """创建视频脚本"""
        theme = parameters.get("theme")
        style = parameters.get("style", "幽默")
        duration = parameters.get("duration", 60)
        target_audience = parameters.get("target_audience", "年轻人")
        
        if not theme:
            raise ValueError("缺少必要参数: theme")
        
        self.logger.info(f"创建脚本: 主题={theme}, 风格={style}, 时长={duration}秒")
        
        # 获取风格模板
        style_template = self._style_templates.get(style, self._style_templates["幽默"])
        
        # 模拟脚本生成（实际应用中会调用 AI 模型）
        script = await self._generate_script(
            theme=theme,
            style=style,
            style_template=style_template,
            duration=duration,
            target_audience=target_audience
        )
        
        script_id = f"script_{uuid.uuid4().hex[:8]}"
        
        return {
            "script_id": script_id,
            "script": script,
            "metadata": {
                "theme": theme,
                "style": style,
                "duration": duration,
                "target_audience": target_audience,
                "created_at": datetime.now().isoformat()
            }
        }
    
    async def _generate_script(
        self,
        theme: str,
        style: str,
        style_template: Dict,
        duration: int,
        target_audience: str
    ) -> Dict[str, Any]:
        """生成脚本内容"""
        # 模拟 AI 生成延迟
        await asyncio.sleep(random.uniform(1, 3))
        
        # 计算分镜数量（假设每个分镜约 5-10 秒）
        num_scenes = max(3, duration // 8)
        
        # 生成标题
        title = f"【{style}】{theme}的那些事儿"
        
        # 生成 hook（开场钩子）
        hooks = [
            f"你知道{theme}背后的秘密吗？",
            f"关于{theme}，99%的人都不知道这个...",
            f"震惊！{theme}竟然可以这样...",
            f"3分钟带你了解{theme}的真相",
        ]
        hook = random.choice(hooks)
        
        # 生成分镜
        scenes = []
        scene_duration = duration / num_scenes
        
        for i in range(num_scenes):
            scene = {
                "scene_id": i + 1,
                "duration": scene_duration,
                "description": f"场景{i+1}: {self._generate_scene_description(theme, style, i, num_scenes)}",
                "visual_prompt": self._generate_visual_prompt(theme, style, i),
                "narration": self._generate_narration(theme, style, i, num_scenes),
                "text_overlay": self._generate_text_overlay(theme, i),
                "transition": "fade" if i < num_scenes - 1 else None
            }
            scenes.append(scene)
        
        # 生成结尾
        ending = {
            "call_to_action": "点赞关注，了解更多精彩内容！",
            "hashtags": self._generate_hashtags(theme, style),
        }
        
        return {
            "title": title,
            "hook": hook,
            "tone": style_template["tone"],
            "structure": style_template["structure"],
            "total_duration": duration,
            "scenes": scenes,
            "ending": ending,
            "target_audience": target_audience
        }
    
    def _generate_scene_description(
        self,
        theme: str,
        style: str,
        scene_index: int,
        total_scenes: int
    ) -> str:
        """生成分镜描述"""
        if scene_index == 0:
            return f"开场：引入{theme}话题，吸引观众注意力"
        elif scene_index == total_scenes - 1:
            return f"结尾：总结{theme}要点，引导互动"
        else:
            return f"主体内容：展示{theme}的第{scene_index}个关键点"
    
    def _generate_visual_prompt(
        self,
        theme: str,
        style: str,
        scene_index: int
    ) -> str:
        """生成视觉提示词"""
        base_prompts = {
            "幽默": f"搞笑风格，夸张表情，{theme}相关场景，明亮色调，动感画面",
            "励志": f"温暖感人，自然光线，{theme}相关场景，正能量画面",
            "教育": f"清晰专业，简洁背景，{theme}相关图表或演示，信息可视化",
            "娱乐": f"潮流时尚，动感十足，{theme}相关元素，流行风格",
            "科技": f"未来感，科技蓝色调，{theme}相关技术元素，现代设计",
            "生活": f"温馨日常，自然舒适，{theme}生活场景，真实感",
        }
        return base_prompts.get(style, f"{theme}相关画面，高质量，适合短视频")
    
    def _generate_narration(
        self,
        theme: str,
        style: str,
        scene_index: int,
        total_scenes: int
    ) -> str:
        """生成旁白文案"""
        if scene_index == 0:
            return f"大家好，今天我们来聊聊{theme}这个话题..."
        elif scene_index == total_scenes - 1:
            return f"以上就是关于{theme}的分享，如果对你有帮助的话，别忘了点赞关注哦！"
        else:
            return f"关于{theme}，还有一个很重要的点就是..."
    
    def _generate_text_overlay(self, theme: str, scene_index: int) -> Optional[str]:
        """生成文字叠加"""
        if scene_index == 0:
            return f"#{theme}"
        return None
    
    def _generate_hashtags(self, theme: str, style: str) -> List[str]:
        """生成话题标签"""
        base_tags = [f"#{theme}", "#短视频", "#涨知识"]
        style_tags = {
            "幽默": ["#搞笑", "#段子", "#笑死我了"],
            "励志": ["#励志", "#正能量", "#人生感悟"],
            "教育": ["#知识分享", "#干货", "#学习"],
            "娱乐": ["#娱乐", "#热门", "#好玩"],
            "科技": ["#科技", "#黑科技", "#前沿"],
            "生活": ["#生活", "#日常", "#生活小妙招"],
        }
        return base_tags + style_tags.get(style, [])
    
    async def _handle_generate_storyboard(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """生成分镜脚本"""
        script = parameters.get("script")
        if not script:
            raise ValueError("缺少必要参数: script")
        
        # 模拟处理延迟
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        storyboard = []
        for scene in script.get("scenes", []):
            storyboard.append({
                "scene_id": scene["scene_id"],
                "shot_type": random.choice(["wide", "medium", "close-up", "detail"]),
                "camera_movement": random.choice(["static", "pan_left", "pan_right", "zoom_in", "zoom_out"]),
                "duration": scene["duration"],
                "visual_description": scene["description"],
                "audio_cue": scene.get("narration", ""),
                "notes": "自动生成的分镜建议"
            })
        
        return {
            "storyboard_id": f"sb_{uuid.uuid4().hex[:8]}",
            "storyboard": storyboard
        }
    
    async def _handle_refine_script(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """优化脚本"""
        script = parameters.get("script")
        feedback = parameters.get("feedback", "")
        
        if not script:
            raise ValueError("缺少必要参数: script")
        
        # 模拟处理延迟
        await asyncio.sleep(random.uniform(1, 2))
        
        # 简单地修改一些内容（实际应该使用 AI 进行优化）
        refined_script = script.copy()
        refined_script["title"] = f"[优化版] {script.get('title', '')}"
        refined_script["refined_at"] = datetime.now().isoformat()
        refined_script["feedback_applied"] = feedback
        
        return {
            "script_id": f"script_{uuid.uuid4().hex[:8]}",
            "script": refined_script,
            "changes": ["标题已优化", "内容结构已调整"]
        }
    
    async def _handle_generate_captions(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """生成字幕"""
        script = parameters.get("script")
        style = parameters.get("caption_style", "default")
        
        if not script:
            raise ValueError("缺少必要参数: script")
        
        # 模拟处理延迟
        await asyncio.sleep(random.uniform(0.5, 1))
        
        captions = []
        current_time = 0
        
        for scene in script.get("scenes", []):
            narration = scene.get("narration", "")
            duration = scene.get("duration", 5)
            
            if narration:
                captions.append({
                    "start_time": current_time,
                    "end_time": current_time + duration,
                    "text": narration,
                    "style": style
                })
            
            current_time += duration
        
        return {
            "captions_id": f"cap_{uuid.uuid4().hex[:8]}",
            "captions": captions,
            "format": "srt"
        }
    
    async def _handle_suggest_hooks(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """建议开场钩子"""
        theme = parameters.get("theme")
        style = parameters.get("style", "幽默")
        count = parameters.get("count", 5)
        
        if not theme:
            raise ValueError("缺少必要参数: theme")
        
        # 模拟处理延迟
        await asyncio.sleep(random.uniform(0.3, 0.8))
        
        hook_templates = [
            f"你知道{theme}背后的秘密吗？",
            f"关于{theme}，99%的人都不知道这个...",
            f"震惊！{theme}竟然可以这样...",
            f"3分钟带你了解{theme}的真相",
            f"别再被{theme}误导了！真相是...",
            f"我花了3年研究{theme}，总结出这些...",
            f"如果你对{theme}感兴趣，一定要看完这个视频",
            f"今天来聊一个大家都关心的话题：{theme}",
        ]
        
        hooks = random.sample(hook_templates, min(count, len(hook_templates)))
        
        return {
            "theme": theme,
            "style": style,
            "hooks": [{"text": hook, "score": random.uniform(0.7, 1.0)} for hook in hooks]
        }
