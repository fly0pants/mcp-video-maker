"""
Unit tests for AudioAgent
"""
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum

from agents.audio_agent import AudioAgent
from models.message import Message, MessageType, MessageStatus, AgentType
from models.video import Script, ScriptSection, AudioTrack, AudioType, AudioEffect, EffectType

# Add FADE to EffectType enum for testing
class FixedEffectType(str, Enum):
    """效果类型枚举 - 修复版"""
    REVERB = "reverb"  # 混响
    ECHO = "echo"  # 回声
    PITCH_SHIFT = "pitch_shift"  # 音调变化
    COMPRESSION = "compression"  # 压缩
    EQUALIZATION = "equalization"  # 均衡器
    DISTORTION = "distortion"  # 失真
    DELAY = "delay"  # 延迟
    FILTER = "filter"  # 滤波器
    FADE = "fade"  # 淡入淡出


@pytest.fixture
def audio_agent():
    """Return an AudioAgent instance for testing"""
    with patch('agents.audio_agent.file_manager') as mock_file_manager:
        with patch('agents.audio_agent.get_prompt_manager') as mock_prompt_manager:
            agent = AudioAgent()
            agent.logger = MagicMock()
            agent.openai_client = MagicMock()
            agent.openai_client.chat.completions.create = AsyncMock()
            
            # Mock the _generate_audio method
            agent._generate_audio = AsyncMock()
            
            yield agent


@pytest.fixture
def mock_script():
    """Return a mock script for testing"""
    return Script(
        id="script_12345678",
        title="有趣的日常生活",
        theme="日常生活",
        type="narrative",
        target_audience=["青少年", "年轻人"],
        sections=[
            ScriptSection(
                id="section_123456",
                content="嗨，大家好！今天我想和大家分享我的日常生活。",
                duration=15.0,
                visual_description="特写镜头，主角对着镜头微笑",
                audio_description="轻快的背景音乐",
                tags=["开场白", "微笑"],
                order=0
            )
        ],
        total_duration=15.0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        creator_id="agent_content_agent",
        version=1,
        keywords=["有趣", "幽默"],
        metadata={}
    )


@pytest.fixture
def mock_message(mock_script):
    """Return a mock message for testing"""
    return Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.AUDIO,
        content={
            "command": "generate_audio",
            "parameters": {
                "script": mock_script.dict(),
                "style": "modern",
                "mood": "upbeat",
                "language": "zh",
                "voice_type": "female",
                "background_music": True,
                "session_id": "sess_" + uuid.uuid4().hex[:8]
            }
        }
    )


@pytest.fixture
def mock_audio_data():
    """Return mock audio data for testing"""
    return [
        {
            "id": "audio_12345678",
            "type": "voice",
            "file_path": "temp/test_session/audio/voice_12345678.mp3",
            "script_section_id": "section_123456",
            "content": "嗨，大家好！今天我想和大家分享我的日常生活。",
            "duration": 5.0,
            "format": "mp3",
            "tool": "elevenlabs",
            "tool_version": "1.0",
            "generation_params": {
                "voice": "zh_female_01",
                "language": "zh"
            }
        },
        {
            "id": "audio_87654321",
            "type": "music",
            "file_path": "temp/test_session/audio/music_87654321.mp3",
            "duration": 15.0,
            "format": "mp3",
            "tool": "mubert",
            "tool_version": "1.0",
            "generation_params": {
                "mood": "upbeat",
                "style": "modern"
            }
        }
    ]


@pytest.mark.asyncio
async def test_handle_command_generate_audio(audio_agent, mock_message, mock_audio_data):
    """Test handling generate audio command"""
    # Setup mock response for _generate_audio
    audio_agent._generate_audio.return_value = mock_audio_data
    
    # Call handle_command
    response = await audio_agent.handle_command(mock_message)
    
    # Print the response content for debugging
    print("Response content:", response.content)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.AUDIO
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is True
    assert "data" in response.content
    assert "success" in response.content["data"]
    assert "data" in response.content["data"]
    assert "audio_assets" in response.content["data"]["data"]
    
    # Verify function calls
    audio_agent._generate_audio.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_invalid_action(audio_agent):
    """Test handling invalid action"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.AUDIO,
        content={
            "command": "invalid_command",
            "parameters": {
                "session_id": "sess_" + uuid.uuid4().hex[:8]
            }
        }
    )
    
    # Call handle_command
    response = await audio_agent.handle_command(message)
    
    # Print the response content for debugging
    print("Response content:", response.content)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.ERROR
    assert response.sender == AgentType.AUDIO
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is False
    assert "error" in response.content


@pytest.mark.asyncio
async def test_handle_command_missing_parameters(audio_agent):
    """Test handling missing parameters"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.AUDIO,
        content={
            "command": "generate_audio",
            "parameters": {}
        }
    )
    
    # Call handle_command
    response = await audio_agent.handle_command(message)
    
    # Print the response content for debugging
    print("Response content:", response.content)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.ERROR
    assert response.sender == AgentType.AUDIO
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is False
    assert "error" in response.content 