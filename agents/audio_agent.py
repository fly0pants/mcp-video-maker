"""
语音与音乐代理
负责生成语音旁白和背景音乐
"""

import asyncio
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.mcp_base_agent import MCPBaseAgent
from models.mcp import MCPCommand, MCPMessage


class AudioAgent(MCPBaseAgent):
    """
    语音与音乐代理
    
    职责：
    1. 根据脚本生成语音旁白
    2. 生成或选择背景音乐
    3. 音频混合和处理
    4. 支持多种语音和音乐生成模型
    """
    
    def __init__(self):
        super().__init__(agent_id="audio_agent", agent_name="语音与音乐代理")
        
        # 命令处理器映射
        self._command_handlers = {
            "generate_audio": self._handle_generate_audio,
            "generate_voice": self._handle_generate_voice,
            "generate_music": self._handle_generate_music,
            "mix_audio": self._handle_mix_audio,
            "enhance_audio": self._handle_enhance_audio,
            "list_voices": self._handle_list_voices,
            "list_music_styles": self._handle_list_music_styles,
        }
        
        # 支持的语音模型
        self._voice_models = {
            "elevenlabs": {
                "name": "ElevenLabs",
                "description": "提供自然流畅的多语言语音",
                "languages": ["zh-CN", "en-US", "ja-JP", "ko-KR"],
                "voice_styles": ["natural", "expressive", "professional"]
            },
            "playht": {
                "name": "Play.ht",
                "description": "支持多种语言和声音风格",
                "languages": ["zh-CN", "en-US", "es-ES", "fr-FR"],
                "voice_styles": ["conversational", "narrative", "broadcast"]
            },
            "tencent": {
                "name": "腾讯云语音合成",
                "description": "提供中文语音的高质量合成",
                "languages": ["zh-CN", "zh-TW"],
                "voice_styles": ["standard", "emotional", "child"]
            },
        }
        
        # 支持的音乐模型
        self._music_models = {
            "suno": {
                "name": "Suno AI",
                "description": "生成多种风格的原创音乐",
                "styles": ["pop", "rock", "electronic", "classical", "ambient"]
            },
            "aiva": {
                "name": "AIVA",
                "description": "专注于情感和氛围音乐创作",
                "styles": ["cinematic", "emotional", "epic", "peaceful"]
            },
            "soundraw": {
                "name": "SoundRaw",
                "description": "提供无版权的背景音乐",
                "styles": ["corporate", "happy", "inspiring", "chill"]
            },
        }
        
        # 预设音色
        self._voice_presets = {
            "male_young": {"name": "年轻男声", "pitch": 0, "speed": 1.0, "tone": "energetic"},
            "male_mature": {"name": "成熟男声", "pitch": -2, "speed": 0.95, "tone": "professional"},
            "female_young": {"name": "年轻女声", "pitch": 2, "speed": 1.0, "tone": "bright"},
            "female_mature": {"name": "成熟女声", "pitch": 0, "speed": 0.95, "tone": "warm"},
            "child": {"name": "童声", "pitch": 4, "speed": 1.1, "tone": "innocent"},
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
    
    async def _handle_generate_audio(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """生成完整音频（语音+背景音乐）"""
        script = parameters.get("script")
        voice_style = parameters.get("voice_style", "natural")
        music_style = parameters.get("music_style", "upbeat")
        duration = parameters.get("duration", 60)
        
        if not script:
            raise ValueError("缺少必要参数: script")
        
        self.logger.info(f"开始生成音频: 语音风格={voice_style}, 音乐风格={music_style}")
        
        # 并行生成语音和音乐
        voice_task = asyncio.create_task(
            self._generate_voice_for_script(script, voice_style, session_id)
        )
        music_task = asyncio.create_task(
            self._generate_background_music(music_style, duration, session_id)
        )
        
        voice_result, music_result = await asyncio.gather(voice_task, music_task)
        
        # 混合音频
        mixed_audio = await self._mix_voice_and_music(
            voice_result, music_result, session_id
        )
        
        audio_id = f"audio_{uuid.uuid4().hex[:8]}"
        
        return {
            "audio_id": audio_id,
            "voice": voice_result,
            "music": music_result,
            "mixed": mixed_audio,
            "metadata": {
                "voice_style": voice_style,
                "music_style": music_style,
                "duration": duration,
                "created_at": datetime.now().isoformat()
            }
        }
    
    async def _generate_voice_for_script(
        self,
        script: Dict[str, Any],
        voice_style: str,
        session_id: str
    ) -> Dict[str, Any]:
        """根据脚本生成语音"""
        scenes = script.get("scenes", [])
        voice_clips = []
        
        for scene in scenes:
            narration = scene.get("narration", "")
            if narration:
                # 模拟生成延迟
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                clip_id = f"voice_{uuid.uuid4().hex[:8]}"
                voice_clips.append({
                    "clip_id": clip_id,
                    "scene_id": scene.get("scene_id"),
                    "text": narration,
                    "duration": scene.get("duration", 5),
                    "file_path": f"/storage/temp/{session_id}/{clip_id}.mp3"
                })
        
        return {
            "clips": voice_clips,
            "style": voice_style,
            "total_duration": sum(clip["duration"] for clip in voice_clips)
        }
    
    async def _generate_background_music(
        self,
        style: str,
        duration: float,
        session_id: str
    ) -> Dict[str, Any]:
        """生成背景音乐"""
        # 模拟生成延迟
        await asyncio.sleep(random.uniform(2, 4))
        
        music_id = f"music_{uuid.uuid4().hex[:8]}"
        
        return {
            "music_id": music_id,
            "style": style,
            "duration": duration,
            "bpm": random.randint(80, 140),
            "key": random.choice(["C", "D", "E", "F", "G", "A", "B"]) + random.choice(["major", "minor"]),
            "file_path": f"/storage/temp/{session_id}/{music_id}.mp3"
        }
    
    async def _mix_voice_and_music(
        self,
        voice_result: Dict[str, Any],
        music_result: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """混合语音和背景音乐"""
        # 模拟混合延迟
        await asyncio.sleep(random.uniform(1, 2))
        
        mixed_id = f"mixed_{uuid.uuid4().hex[:8]}"
        
        return {
            "mixed_id": mixed_id,
            "voice_volume": 1.0,
            "music_volume": 0.3,  # 背景音乐音量较低
            "file_path": f"/storage/temp/{session_id}/{mixed_id}.mp3"
        }
    
    async def _handle_generate_voice(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """单独生成语音"""
        text = parameters.get("text")
        voice_preset = parameters.get("voice_preset", "male_young")
        speed = parameters.get("speed", 1.0)
        model = parameters.get("model", "elevenlabs")
        
        if not text:
            raise ValueError("缺少必要参数: text")
        
        # 模拟生成延迟
        await asyncio.sleep(random.uniform(1, 3))
        
        voice_id = f"voice_{uuid.uuid4().hex[:8]}"
        preset = self._voice_presets.get(voice_preset, self._voice_presets["male_young"])
        
        # 估算时长（假设中文每秒约 4 个字）
        estimated_duration = len(text) / 4 / speed
        
        return {
            "voice_id": voice_id,
            "text": text,
            "preset": voice_preset,
            "model": model,
            "duration": estimated_duration,
            "file_path": f"/storage/temp/{session_id}/{voice_id}.mp3",
            "settings": {
                "speed": speed,
                "pitch": preset["pitch"],
                "tone": preset["tone"]
            }
        }
    
    async def _handle_generate_music(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """单独生成音乐"""
        style = parameters.get("style", "upbeat")
        duration = parameters.get("duration", 60)
        mood = parameters.get("mood", "happy")
        model = parameters.get("model", "suno")
        prompt = parameters.get("prompt", "")
        
        # 模拟生成延迟
        await asyncio.sleep(random.uniform(3, 6))
        
        music_id = f"music_{uuid.uuid4().hex[:8]}"
        
        return {
            "music_id": music_id,
            "style": style,
            "mood": mood,
            "model": model,
            "duration": duration,
            "file_path": f"/storage/temp/{session_id}/{music_id}.mp3",
            "metadata": {
                "bpm": random.randint(80, 140),
                "key": random.choice(["C", "D", "E", "F", "G", "A", "B"]) + " " + random.choice(["major", "minor"]),
                "instruments": random.sample(["piano", "guitar", "drums", "bass", "synth", "strings"], 3),
                "prompt": prompt
            }
        }
    
    async def _handle_mix_audio(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """混合多个音频轨道"""
        tracks = parameters.get("tracks", [])
        if not tracks:
            raise ValueError("缺少必要参数: tracks")
        
        # 模拟混合延迟
        await asyncio.sleep(random.uniform(1, 3))
        
        mixed_id = f"mixed_{uuid.uuid4().hex[:8]}"
        
        return {
            "mixed_id": mixed_id,
            "tracks_count": len(tracks),
            "file_path": f"/storage/temp/{session_id}/{mixed_id}.mp3",
            "duration": max(track.get("duration", 0) for track in tracks)
        }
    
    async def _handle_enhance_audio(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """增强音频质量"""
        audio_path = parameters.get("audio_path")
        enhancements = parameters.get("enhancements", ["denoise", "normalize"])
        
        if not audio_path:
            raise ValueError("缺少必要参数: audio_path")
        
        # 模拟处理延迟
        await asyncio.sleep(random.uniform(1, 2))
        
        enhanced_id = f"enhanced_{uuid.uuid4().hex[:8]}"
        
        return {
            "enhanced_id": enhanced_id,
            "source_audio": audio_path,
            "enhancements_applied": enhancements,
            "file_path": f"/storage/temp/{session_id}/{enhanced_id}.mp3"
        }
    
    async def _handle_list_voices(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """列出可用的声音"""
        return {
            "voice_models": self._voice_models,
            "voice_presets": self._voice_presets
        }
    
    async def _handle_list_music_styles(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """列出可用的音乐风格"""
        return {
            "music_models": self._music_models
        }
