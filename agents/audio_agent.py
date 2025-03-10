import asyncio
import uuid
import json
import os
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from models.message import Message, MessageType, AgentType
from models.video import AudioAsset
from agents.base_agent import BaseAgent
from utils.file_manager import file_manager
from utils.logger import system_logger
from config.config import SYSTEM_CONFIG, AUDIO_CONFIG, API_KEYS


class VoiceSynthesisAPI:
    """语音合成API接口封装"""
    
    def __init__(self, tool_name: str, api_key: str):
        self.tool_name = tool_name
        self.api_key = api_key
        self.base_url = AUDIO_CONFIG.get(tool_name, {}).get("base_url", "")
        self.model_version = AUDIO_CONFIG.get(tool_name, {}).get("version", "1.0")
        self.request_timeout = AUDIO_CONFIG.get(tool_name, {}).get("timeout", 60)
        self.max_retries = AUDIO_CONFIG.get(tool_name, {}).get("max_retries", 3)
        
    async def synthesize_speech(self, 
                              text: str, 
                              voice: str = None,
                              language: str = "zh",
                              **kwargs) -> Dict[str, Any]:
        """
        合成语音
        
        Args:
            text: 文本内容
            voice: 声音ID或名称
            language: 语言代码
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 合成结果，包含音频文件路径等信息
        """
        # 当前为模拟实现，实际使用时请替换为真实API调用
        system_logger.log_api_call(
            service=f"voice_synthesis_{self.tool_name}",
            endpoint="synthesize_speech",
            params={
                "text": text,
                "voice": voice,
                "language": language,
                "model_version": self.model_version,
                **kwargs
            }
        )
        
        # 模拟API调用延迟
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # 模拟文件生成
        file_id = str(uuid.uuid4())
        file_path = f"mock_audio/{file_id}.mp3"
        
        # 模拟API响应
        return {
            "success": True,
            "file_path": file_path,
            "duration": len(text) * 0.1,  # 简单估算时长
            "format": "mp3",
            "tool": self.tool_name,
            "tool_version": self.model_version,
            "voice": voice,
            "language": language,
            "generation_params": {
                "text": text,
                **kwargs
            }
        }


class MusicGenerationAPI:
    """音乐生成API接口封装"""
    
    def __init__(self, tool_name: str, api_key: str):
        self.tool_name = tool_name
        self.api_key = api_key
        self.base_url = AUDIO_CONFIG.get(tool_name, {}).get("base_url", "")
        self.model_version = AUDIO_CONFIG.get(tool_name, {}).get("version", "1.0")
        self.request_timeout = AUDIO_CONFIG.get(tool_name, {}).get("timeout", 60)
        self.max_retries = AUDIO_CONFIG.get(tool_name, {}).get("max_retries", 3)
        
    async def generate_music(self, 
                           mood: str, 
                           duration: float,
                           style: str = None,
                           **kwargs) -> Dict[str, Any]:
        """
        生成音乐
        
        Args:
            mood: 情绪或氛围
            duration: 时长（秒）
            style: 音乐风格
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 生成结果，包含音频文件路径等信息
        """
        # 当前为模拟实现，实际使用时请替换为真实API调用
        system_logger.log_api_call(
            service=f"music_generation_{self.tool_name}",
            endpoint="generate_music",
            params={
                "mood": mood,
                "duration": duration,
                "style": style,
                "model_version": self.model_version,
                **kwargs
            }
        )
        
        # 模拟API调用延迟
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # 模拟文件生成
        file_id = str(uuid.uuid4())
        file_path = f"mock_audio/{file_id}.mp3"
        
        # 模拟API响应
        return {
            "success": True,
            "file_path": file_path,
            "duration": duration,
            "format": "mp3",
            "tool": self.tool_name,
            "tool_version": self.model_version,
            "mood": mood,
            "style": style,
            "generation_params": {
                **kwargs
            }
        }


class AudioAgent(BaseAgent):
    """音频生成代理，负责生成语音和背景音乐"""
    
    # 支持的语音合成工具映射
    VOICE_TOOL_MAP = {
        "elevenlabs": "ElevenLabs",
        "playht": "Play.ht",
        "deepseek_tencent": "腾讯云语音合成"
    }
    
    # 支持的音乐生成工具映射
    MUSIC_TOOL_MAP = {
        "suno": "Suno AI",
        "aiva": "AIVA",
        "soundraw": "SoundRaw"
    }
    
    def __init__(self):
        super().__init__(agent_type=AgentType.AUDIO, name="音频生成代理")
        self.voice_apis = {}  # 存储不同语音合成工具的API实例
        self.music_apis = {}  # 存储不同音乐生成工具的API实例
        
    async def initialize(self):
        """初始化代理"""
        await super().initialize()
        
        # 预初始化所有支持的语音合成工具API
        for tool_name, api_key_name in {
            "elevenlabs": "ELEVENLABS_API_KEY",
            "playht": "PLAYHT_API_KEY",
            "deepseek_tencent": "TENCENT_API_KEY"
        }.items():
            if api_key := API_KEYS.get(api_key_name):
                self.voice_apis[tool_name] = VoiceSynthesisAPI(tool_name, api_key)
                self.logger.info(f"已初始化{self.VOICE_TOOL_MAP.get(tool_name, tool_name)}语音合成API")
            else:
                self.logger.warning(f"未找到{tool_name}工具的API密钥，无法初始化该工具")
                
        # 预初始化所有支持的音乐生成工具API
        for tool_name, api_key_name in {
            "suno": "SUNO_API_KEY",
            "aiva": "AIVA_API_KEY",
            "soundraw": "SOUNDRAW_API_KEY"
        }.items():
            if api_key := API_KEYS.get(api_key_name):
                self.music_apis[tool_name] = MusicGenerationAPI(tool_name, api_key)
                self.logger.info(f"已初始化{self.MUSIC_TOOL_MAP.get(tool_name, tool_name)}音乐生成API")
            else:
                self.logger.warning(f"未找到{tool_name}工具的API密钥，无法初始化该工具")
                
        self.logger.info(f"音频生成代理初始化完成，支持的语音工具: {list(self.voice_apis.keys())}, 支持的音乐工具: {list(self.music_apis.keys())}")
        
    async def handle_command(self, message: Message) -> Optional[Message]:
        """
        处理命令消息
        
        Args:
            message: 接收到的消息
            
        Returns:
            Optional[Message]: 响应消息
        """
        command = message.content.get("command")
        self.logger.info(f"收到命令: {command}")
        
        if command == "generate_audio":
            # 生成音频（语音和音乐）
            try:
                parameters = message.content.get("parameters", {})
                session_id = parameters.get("session_id")
                
                if not session_id:
                    return self.create_error_response(message, "缺少session_id参数")
                
                self.logger.info(f"开始为会话{session_id}生成音频")
                audio_assets = await self._generate_audio(parameters, session_id)
                
                # 返回音频资产列表
                return self.create_success_response(message, {
                    "success": True,
                    "data": {
                        "audio_assets": audio_assets
                    }
                })
                
            except Exception as e:
                self.logger.error(f"音频生成失败: {str(e)}")
                return self.create_error_response(message, f"音频生成失败: {str(e)}")
                
        elif command == "regenerate_voice":
            # 重新生成语音
            try:
                parameters = message.content.get("parameters", {})
                session_id = parameters.get("session_id")
                
                if not session_id:
                    return self.create_error_response(message, "缺少session_id参数")
                    
                self.logger.info(f"开始为会话{session_id}重新生成语音")
                audio_asset = await self._regenerate_voice(parameters, session_id)
                
                # 返回重新生成的音频资产
                return self.create_success_response(message, {
                    "success": True,
                    "data": {
                        "audio_asset": audio_asset
                    }
                })
                
            except Exception as e:
                self.logger.error(f"语音重新生成失败: {str(e)}")
                return self.create_error_response(message, f"语音重新生成失败: {str(e)}")
                
        elif command == "regenerate_music":
            # 重新生成音乐
            try:
                parameters = message.content.get("parameters", {})
                session_id = parameters.get("session_id")
                
                if not session_id:
                    return self.create_error_response(message, "缺少session_id参数")
                    
                self.logger.info(f"开始为会话{session_id}重新生成音乐")
                audio_asset = await self._regenerate_music(parameters, session_id)
                
                # 返回重新生成的音频资产
                return self.create_success_response(message, {
                    "success": True,
                    "data": {
                        "audio_asset": audio_asset
                    }
                })
                
            except Exception as e:
                self.logger.error(f"音乐重新生成失败: {str(e)}")
                return self.create_error_response(message, f"音乐重新生成失败: {str(e)}")
        else:
            return self.create_error_response(message, f"未知命令: {command}")
    
    async def _generate_audio(self, parameters: Dict[str, Any], session_id: str) -> List[Dict[str, Any]]:
        """
        生成音频（语音和音乐）
        
        Args:
            parameters: 参数
            session_id: 会话ID
            
        Returns:
            List[Dict[str, Any]]: 生成的音频资产列表
        """
        script_sections = parameters.get("script_sections", [])
        voice_tool = parameters.get("voice_tool", "elevenlabs")  # 默认使用elevenlabs
        music_tool = parameters.get("music_tool", "suno")  # 默认使用suno
        language = parameters.get("language", "zh")
        voice_character = parameters.get("voice_character")
        music_style = parameters.get("music_style")
        
        audio_assets = []
        
        # 检查选择的语音工具是否可用
        if voice_tool not in self.voice_apis:
            self.logger.warning(f"所选语音工具 {voice_tool} 不可用，将使用默认工具")
            available_tools = list(self.voice_apis.keys())
            if not available_tools:
                raise ValueError("没有可用的语音合成工具")
            voice_tool = available_tools[0]
            
        # 检查选择的音乐工具是否可用
        if music_tool not in self.music_apis:
            self.logger.warning(f"所选音乐工具 {music_tool} 不可用，将使用默认工具")
            available_tools = list(self.music_apis.keys())
            if not available_tools:
                raise ValueError("没有可用的音乐生成工具")
            music_tool = available_tools[0]
            
        self.logger.info(f"使用{self.VOICE_TOOL_MAP.get(voice_tool, voice_tool)}生成语音，使用{self.MUSIC_TOOL_MAP.get(music_tool, music_tool)}生成音乐")
        
        # 获取所选工具的API实例
        voice_api = self.voice_apis[voice_tool]
        music_api = self.music_apis[music_tool]
        
        # 生成语音
        voice_assets = await self._generate_voices(
            voice_api=voice_api,
            script_sections=script_sections,
            language=language,
            voice_character=voice_character,
            session_id=session_id
        )
        audio_assets.extend(voice_assets)
        
        # 生成音乐
        music_assets = await self._generate_music(
            music_api=music_api,
            script_sections=script_sections,
            music_style=music_style,
            session_id=session_id
        )
        audio_assets.extend(music_assets)
        
        self.logger.info(f"已为会话{session_id}生成{len(audio_assets)}个音频资产")
        
        return audio_assets
        
    async def _generate_voices(self,
                             voice_api: VoiceSynthesisAPI,
                             script_sections: List[Dict[str, Any]],
                             language: str,
                             voice_character: Optional[str],
                             session_id: str) -> List[Dict[str, Any]]:
        """
        生成语音
        
        Args:
            voice_api: 语音合成API实例
            script_sections: 脚本片段列表
            language: 语言代码
            voice_character: 声音角色
            session_id: 会话ID
            
        Returns:
            List[Dict[str, Any]]: 生成的语音资产列表
        """
        self.logger.info(f"开始生成{len(script_sections)}个语音片段")
        
        # 获取工具支持的声音列表
        voice_options = AUDIO_CONFIG.get(voice_api.tool_name, {}).get("voices", {}).get(language, [])
        
        # 如果指定了角色但不在支持列表中，使用默认声音
        selected_voice = None
        if voice_character and voice_options:
            if voice_character in voice_options:
                selected_voice = voice_character
            else:
                self.logger.warning(f"指定的声音角色 {voice_character} 不可用，将使用默认声音")
                
        # 如果没有指定角色或指定的角色不可用，使用第一个可用声音
        if not selected_voice and voice_options:
            selected_voice = voice_options[0]
            
        # 并行生成所有语音片段
        tasks = []
        for section in script_sections:
            task = self._generate_single_voice(
                api=voice_api,
                section_id=section["id"],
                text=section["content"],
                language=language,
                voice=selected_voice,
                session_id=session_id
            )
            tasks.append(task)
            
        voice_assets = await asyncio.gather(*tasks)
        self.logger.info(f"已生成{len(voice_assets)}个语音片段")
        
        return voice_assets
        
    async def _generate_single_voice(self,
                                   api: VoiceSynthesisAPI,
                                   section_id: str,
                                   text: str,
                                   language: str,
                                   voice: Optional[str],
                                   session_id: str) -> Dict[str, Any]:
        """
        生成单个语音片段
        
        Args:
            api: 语音合成API实例
            section_id: 脚本片段ID
            text: 文本内容
            language: 语言代码
            voice: 声音ID或名称
            session_id: 会话ID
            
        Returns:
            Dict[str, Any]: 生成的语音资产
        """
        self.logger.info(f"为片段{section_id}生成语音，语言: {language}, 声音: {voice}")
        
        # 调用API合成语音
        synthesis_result = await api.synthesize_speech(
            text=text,
            voice=voice,
            language=language,
            speed=AUDIO_CONFIG.get(api.tool_name, {}).get("speed", 1.0),
            pitch=AUDIO_CONFIG.get(api.tool_name, {}).get("pitch", 0),
            volume=AUDIO_CONFIG.get(api.tool_name, {}).get("volume", 1.0)
        )
        
        # 模拟保存音频文件
        temp_path = f"temp_{uuid.uuid4()}.mp3"
        audio_path = await file_manager.save_text_file(
            content=f"Mock audio content for {section_id}",
            filename=temp_path,
            session_id=session_id,
            is_temp=True,
            subdir="audio"
        )
        
        # 估算时长
        estimated_duration = len(text) * 0.1  # 简单估算：每个字符0.1秒
        
        # 创建音频资产
        asset_id = str(uuid.uuid4())
        audio_asset = {
            "id": asset_id,
            "script_section_id": section_id,
            "file_path": audio_path,
            "url": None,
            "format": "mp3",
            "duration": estimated_duration,
            "type": "voice",
            "created_at": datetime.now().isoformat(),
            "generation_tool": api.tool_name,
            "generation_parameters": {
                "text": text,
                "language": language,
                "voice": voice,
                "tool_version": api.model_version,
                "speed": AUDIO_CONFIG.get(api.tool_name, {}).get("speed", 1.0),
                "pitch": AUDIO_CONFIG.get(api.tool_name, {}).get("pitch", 0),
                "volume": AUDIO_CONFIG.get(api.tool_name, {}).get("volume", 1.0)
            },
            "metadata": {}
        }
        
        return audio_asset
        
    async def _generate_music(self,
                            music_api: MusicGenerationAPI,
                            script_sections: List[Dict[str, Any]],
                            music_style: Optional[str],
                            session_id: str) -> List[Dict[str, Any]]:
        """
        生成背景音乐
        
        Args:
            music_api: 音乐生成API实例
            script_sections: 脚本片段列表
            music_style: 音乐风格
            session_id: 会话ID
            
        Returns:
            List[Dict[str, Any]]: 生成的音乐资产列表
        """
        self.logger.info(f"开始生成背景音乐")
        
        # 获取工具支持的音乐风格列表
        style_options = AUDIO_CONFIG.get(music_api.tool_name, {}).get("styles", [])
        
        # 如果指定了风格但不在支持列表中，使用默认风格
        selected_style = None
        if music_style and style_options:
            if music_style in style_options:
                selected_style = music_style
            else:
                self.logger.warning(f"指定的音乐风格 {music_style} 不可用，将使用默认风格")
                
        # 如果没有指定风格或指定的风格不可用，使用第一个可用风格
        if not selected_style and style_options:
            selected_style = style_options[0]
            
        # 计算总时长
        total_duration = sum(section.get("duration", 0) for section in script_sections)
        
        # 生成背景音乐
        mood = "upbeat"  # 默认情绪
        
        # 根据脚本内容分析情绪（简化实现）
        if script_sections:
            content = " ".join([section.get("content", "") for section in script_sections])
            if "悲伤" in content or "难过" in content:
                mood = "sad"
            elif "激动" in content or "兴奋" in content:
                mood = "energetic"
            elif "放松" in content or "平静" in content:
                mood = "calm"
                
        # 调用API生成音乐
        generation_result = await music_api.generate_music(
            mood=mood,
            duration=total_duration,
            style=selected_style,
            tempo=AUDIO_CONFIG.get(music_api.tool_name, {}).get("tempo", "medium"),
            intensity=AUDIO_CONFIG.get(music_api.tool_name, {}).get("intensity", 0.7)
        )
        
        # 模拟保存音频文件
        temp_path = f"temp_{uuid.uuid4()}.mp3"
        audio_path = await file_manager.save_text_file(
            content=f"Mock music content with mood: {mood}, style: {selected_style}",
            filename=temp_path,
            session_id=session_id,
            is_temp=True,
            subdir="audio"
        )
        
        # 创建音频资产
        asset_id = str(uuid.uuid4())
        audio_asset = {
            "id": asset_id,
            "script_section_id": None,  # 背景音乐不与特定片段关联
            "file_path": audio_path,
            "url": None,
            "format": "mp3",
            "duration": total_duration,
            "type": "music",
            "created_at": datetime.now().isoformat(),
            "generation_tool": music_api.tool_name,
            "generation_parameters": {
                "mood": mood,
                "style": selected_style,
                "tool_version": music_api.model_version,
                "tempo": AUDIO_CONFIG.get(music_api.tool_name, {}).get("tempo", "medium"),
                "intensity": AUDIO_CONFIG.get(music_api.tool_name, {}).get("intensity", 0.7)
            },
            "metadata": {}
        }
        
        return [audio_asset]
        
    async def _regenerate_voice(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        重新生成语音
        
        Args:
            parameters: 参数
            session_id: 会话ID
            
        Returns:
            Dict[str, Any]: 重新生成的语音资产
        """
        section_id = parameters.get("section_id")
        text = parameters.get("text")
        language = parameters.get("language", "zh")
        voice = parameters.get("voice")
        voice_tool = parameters.get("voice_tool", "elevenlabs")
        feedback = parameters.get("feedback", "")
        
        if not all([section_id, text]):
            raise ValueError("缺少必要的参数")
            
        # 检查选择的语音工具是否可用
        if voice_tool not in self.voice_apis:
            self.logger.warning(f"所选语音工具 {voice_tool} 不可用，将使用默认工具")
            available_tools = list(self.voice_apis.keys())
            if not available_tools:
                raise ValueError("没有可用的语音合成工具")
            voice_tool = available_tools[0]
            
        self.logger.info(f"根据反馈 '{feedback}' 重新生成语音")
        
        # 获取所选工具的API实例
        api = self.voice_apis[voice_tool]
        
        # 生成语音
        audio_asset = await self._generate_single_voice(
            api=api,
            section_id=section_id,
            text=text,
            language=language,
            voice=voice,
            session_id=session_id
        )
        
        return audio_asset
        
    async def _regenerate_music(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        重新生成音乐
        
        Args:
            parameters: 参数
            session_id: 会话ID
            
        Returns:
            Dict[str, Any]: 重新生成的音乐资产
        """
        mood = parameters.get("mood", "upbeat")
        duration = parameters.get("duration", 60.0)
        style = parameters.get("style")
        music_tool = parameters.get("music_tool", "suno")
        feedback = parameters.get("feedback", "")
        
        # 检查选择的音乐工具是否可用
        if music_tool not in self.music_apis:
            self.logger.warning(f"所选音乐工具 {music_tool} 不可用，将使用默认工具")
            available_tools = list(self.music_apis.keys())
            if not available_tools:
                raise ValueError("没有可用的音乐生成工具")
            music_tool = available_tools[0]
            
        self.logger.info(f"根据反馈 '{feedback}' 重新生成音乐")
        
        # 获取所选工具的API实例
        api = self.music_apis[music_tool]
        
        # 根据反馈调整参数
        if feedback:
            if "更快" in feedback or "加快" in feedback:
                tempo = "fast"
            elif "更慢" in feedback or "减慢" in feedback:
                tempo = "slow"
            else:
                tempo = AUDIO_CONFIG.get(api.tool_name, {}).get("tempo", "medium")
                
            if "更强" in feedback or "更有力" in feedback:
                intensity = 0.9
            elif "更柔和" in feedback or "更轻" in feedback:
                intensity = 0.5
            else:
                intensity = AUDIO_CONFIG.get(api.tool_name, {}).get("intensity", 0.7)
        else:
            tempo = AUDIO_CONFIG.get(api.tool_name, {}).get("tempo", "medium")
            intensity = AUDIO_CONFIG.get(api.tool_name, {}).get("intensity", 0.7)
            
        # 调用API生成音乐
        generation_result = await api.generate_music(
            mood=mood,
            duration=duration,
            style=style,
            tempo=tempo,
            intensity=intensity
        )
        
        # 模拟保存音频文件
        temp_path = f"temp_{uuid.uuid4()}.mp3"
        audio_path = await file_manager.save_text_file(
            content=f"Mock music content with mood: {mood}, style: {style}",
            filename=temp_path,
            session_id=session_id,
            is_temp=True,
            subdir="audio"
        )
        
        # 创建音频资产
        asset_id = str(uuid.uuid4())
        audio_asset = {
            "id": asset_id,
            "script_section_id": None,  # 背景音乐不与特定片段关联
            "file_path": audio_path,
            "url": None,
            "format": "mp3",
            "duration": duration,
            "type": "music",
            "created_at": datetime.now().isoformat(),
            "generation_tool": api.tool_name,
            "generation_parameters": {
                "mood": mood,
                "style": style,
                "tool_version": api.model_version,
                "tempo": tempo,
                "intensity": intensity
            },
            "metadata": {}
        }
        
        return audio_asset 