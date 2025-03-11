"""
Unit tests for CentralAgent
"""
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from agents.central_agent import CentralAgent
from models.message import Message, MessageType, MessageStatus, AgentType
from models.video import (
    Script, ScriptSection, Shot, ShotType, Transition, TransitionType,
    AudioTrack, AudioType, AudioEffect, EffectType, VideoEdit, EditType,
    Distribution, Platform, PublishSchedule, DistributionMetadata
)


@pytest.fixture
def central_agent():
    """Return a CentralAgent instance for testing"""
    with patch('agents.central_agent.file_manager') as mock_file_manager:
        with patch('agents.central_agent.prompt_manager') as mock_prompt_manager:
            agent = CentralAgent()
            agent.logger = MagicMock()
            agent.openai_client = MagicMock()
            agent.openai_client.chat.completions.create = AsyncMock()
            
            # Mock all sub-agents
            agent.content_agent = MagicMock()
            agent.content_agent.handle_command = AsyncMock()
            
            agent.visual_agent = MagicMock()
            agent.visual_agent.handle_command = AsyncMock()
            
            agent.audio_agent = MagicMock()
            agent.audio_agent.handle_command = AsyncMock()
            
            agent.postprod_agent = MagicMock()
            agent.postprod_agent.handle_command = AsyncMock()
            
            agent.distribution_agent = MagicMock()
            agent.distribution_agent.handle_command = AsyncMock()
            
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
def mock_shots():
    """Return mock shots for testing"""
    return [
        Shot(
            id="shot_12345678",
            type=ShotType.CLOSE_UP,
            description="特写镜头，主角面带微笑对着镜头",
            duration=5.0,
            camera_movement="STATIC",
            composition="居中构图，主角面部占据画面中心",
            lighting="自然光，补光灯提亮面部",
            props=["补光灯"],
            special_effects=["温暖色调"],
            tags=["开场", "微笑", "特写"],
            order=0,
            section_id="section_123456"
        )
    ]


@pytest.fixture
def mock_transitions():
    """Return mock transitions for testing"""
    return [
        Transition(
            id="transition_12345678",
            type=TransitionType.FADE,
            duration=0.5,
            description="淡入淡出过渡",
            parameters={"color": "#000000"},
            order=0
        )
    ]


@pytest.fixture
def mock_audio_tracks():
    """Return mock audio tracks for testing"""
    return [
        AudioTrack(
            id="track_12345678",
            type=AudioType.VOICE,
            description="主播声音，女声，清晰活泼",
            duration=15.0,
            source="tts_engine",
            content="嗨，大家好！今天我想和大家分享我的日常生活。",
            parameters={
                "voice_id": "zh_female_01",
                "speed": 1.0,
                "pitch": 1.0
            },
            tags=["旁白", "开场"],
            order=0,
            section_id="section_123456"
        )
    ]


@pytest.fixture
def mock_audio_effects():
    """Return mock audio effects for testing"""
    return [
        AudioEffect(
            id="effect_12345678",
            type=EffectType.FADE,
            description="背景音乐淡入",
            duration=1.0,
            parameters={
                "start_volume": 0.0,
                "end_volume": 0.5
            },
            order=0
        )
    ]


@pytest.fixture
def mock_video_edit():
    """Return a mock video edit for testing"""
    return VideoEdit(
        id="edit_12345678",
        timeline=[
            {
                "type": EditType.VIDEO,
                "source": "shot_12345678",
                "start_time": 0.0,
                "end_time": 5.0,
                "track": 0,
                "effects": [
                    {
                        "type": "COLOR_GRADE",
                        "parameters": {
                            "temperature": 5500,
                            "tint": 0,
                            "saturation": 1.1
                        }
                    }
                ]
            }
        ],
        metadata={
            "total_duration": 15.0,
            "resolution": "1920x1080",
            "fps": 30,
            "output_format": "mp4"
        }
    )


@pytest.fixture
def mock_distribution():
    """Return a mock distribution plan for testing"""
    return Distribution(
        id="dist_12345678",
        platforms=[
            Platform(
                name="douyin",
                title="记录温暖日常 | 生活中的小确幸",
                description="一起来看看我的日常生活吧！\n\n#日常生活 #生活记录 #温暖日常",
                tags=["日常生活", "生活记录", "温暖日常", "vlog"],
                schedule=PublishSchedule(
                    publish_time="2024-03-20T18:00:00Z",
                    timezone="Asia/Shanghai"
                ),
                metadata=DistributionMetadata(
                    cover_image="thumbnail_001.jpg",
                    category="生活",
                    visibility="public",
                    allow_comments=True
                )
            )
        ]
    )


@pytest.mark.asyncio
async def test_handle_command_create_video(central_agent, mock_script):
    """Test handling create video command"""
    # Create a mock message
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.USER,
        receiver=AgentType.CENTRAL,
        content={
            "action": "create_video",
            "parameters": {
                "theme": "日常生活",
                "style": "vlog",
                "script_type": "narrative",
                "target_audience": ["青少年", "年轻人"],
                "duration": 60.0,
                "language": "zh",
                "keywords": ["有趣", "幽默"],
                "special_requirements": "加入一些有趣的转场",
                "platforms": ["douyin", "bilibili"]
            },
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Mock responses from sub-agents
    central_agent.content_agent.handle_command.return_value = Message(
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
        sender=AgentType.CONTENT,
        receiver=AgentType.CENTRAL,
        content={
            "success": True,
            "data": {
                "script": mock_script.dict(),
                "file_path": "temp/test_session/scripts/test_script.json"
            }
        }
    )
    
    # Call handle_command
    response = await central_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.CENTRAL
    assert response.receiver == AgentType.USER
    assert response.content["success"] is True
    assert "script" in response.content["data"]
    
    # Verify function calls
    central_agent.content_agent.handle_command.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_create_shots(central_agent, mock_script, mock_shots, mock_transitions):
    """Test handling create shots command"""
    # Create a mock message
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.USER,
        receiver=AgentType.CENTRAL,
        content={
            "action": "create_shots",
            "parameters": {
                "script": mock_script.dict(),
                "style": "modern",
                "special_effects": ["transition_effects", "color_grading"],
                "aspect_ratio": "9:16"
            },
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Mock responses from sub-agents
    central_agent.visual_agent.handle_command.return_value = Message(
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
        sender=AgentType.VISUAL,
        receiver=AgentType.CENTRAL,
        content={
            "success": True,
            "data": {
                "shots": [shot.dict() for shot in mock_shots],
                "transitions": [transition.dict() for transition in mock_transitions],
                "file_path": "temp/test_session/shots/test_shots.json"
            }
        }
    )
    
    # Call handle_command
    response = await central_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.CENTRAL
    assert response.receiver == AgentType.USER
    assert response.content["success"] is True
    assert "shots" in response.content["data"]
    assert "transitions" in response.content["data"]
    
    # Verify function calls
    central_agent.visual_agent.handle_command.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_create_audio_tracks(central_agent, mock_script, mock_audio_tracks, mock_audio_effects):
    """Test handling create audio tracks command"""
    # Create a mock message
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.USER,
        receiver=AgentType.CENTRAL,
        content={
            "action": "create_audio_tracks",
            "parameters": {
                "script": mock_script.dict(),
                "style": "modern",
                "mood": "upbeat",
                "language": "zh",
                "voice_type": "female",
                "background_music": True
            },
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Mock responses from sub-agents
    central_agent.audio_agent.handle_command.return_value = Message(
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
        sender=AgentType.AUDIO,
        receiver=AgentType.CENTRAL,
        content={
            "success": True,
            "data": {
                "tracks": [track.dict() for track in mock_audio_tracks],
                "effects": [effect.dict() for effect in mock_audio_effects],
                "file_path": "temp/test_session/audio/test_audio.json"
            }
        }
    )
    
    # Call handle_command
    response = await central_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.CENTRAL
    assert response.receiver == AgentType.USER
    assert response.content["success"] is True
    assert "tracks" in response.content["data"]
    assert "effects" in response.content["data"]
    
    # Verify function calls
    central_agent.audio_agent.handle_command.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_create_video_edit(
    central_agent, mock_script, mock_shots, mock_transitions,
    mock_audio_tracks, mock_audio_effects, mock_video_edit
):
    """Test handling create video edit command"""
    # Create a mock message
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.USER,
        receiver=AgentType.CENTRAL,
        content={
            "action": "create_video_edit",
            "parameters": {
                "script": mock_script.dict(),
                "shots": [shot.dict() for shot in mock_shots],
                "transitions": [transition.dict() for transition in mock_transitions],
                "audio_tracks": [track.dict() for track in mock_audio_tracks],
                "audio_effects": [effect.dict() for effect in mock_audio_effects],
                "style": "modern",
                "special_effects": ["color_grading", "motion_graphics"],
                "output_format": "mp4",
                "resolution": "1080p",
                "fps": 30
            },
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Mock responses from sub-agents
    central_agent.postprod_agent.handle_command.return_value = Message(
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
        sender=AgentType.POSTPROD,
        receiver=AgentType.CENTRAL,
        content={
            "success": True,
            "data": {
                "edit": mock_video_edit.dict(),
                "file_path": "temp/test_session/edits/test_edit.json"
            }
        }
    )
    
    # Call handle_command
    response = await central_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.CENTRAL
    assert response.receiver == AgentType.USER
    assert response.content["success"] is True
    assert "edit" in response.content["data"]
    
    # Verify function calls
    central_agent.postprod_agent.handle_command.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_create_distribution_plan(
    central_agent, mock_script, mock_video_edit, mock_distribution
):
    """Test handling create distribution plan command"""
    # Create a mock message
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.USER,
        receiver=AgentType.CENTRAL,
        content={
            "action": "create_distribution_plan",
            "parameters": {
                "script": mock_script.dict(),
                "video_edit": mock_video_edit.dict(),
                "platforms": ["douyin", "bilibili", "xiaohongshu"],
                "target_audience": ["青少年", "年轻人"],
                "publish_time": "2024-03-20T18:00:00Z",
                "tags": ["日常", "生活", "vlog"],
                "description_template": "一起来看看我的日常生活吧！{hashtags}"
            },
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Mock responses from sub-agents
    central_agent.distribution_agent.handle_command.return_value = Message(
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
        sender=AgentType.DISTRIBUTION,
        receiver=AgentType.CENTRAL,
        content={
            "success": True,
            "data": {
                "distribution": mock_distribution.dict(),
                "file_path": "temp/test_session/distribution/test_plan.json"
            }
        }
    )
    
    # Call handle_command
    response = await central_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.CENTRAL
    assert response.receiver == AgentType.USER
    assert response.content["success"] is True
    assert "distribution" in response.content["data"]
    
    # Verify function calls
    central_agent.distribution_agent.handle_command.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_invalid_action(central_agent):
    """Test handling invalid action"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.USER,
        receiver=AgentType.CENTRAL,
        content={
            "action": "invalid_action",
            "parameters": {},
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Call handle_command
    response = await central_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.CENTRAL
    assert response.receiver == AgentType.USER
    assert response.content["success"] is False
    assert "error" in response.content
    assert "Unsupported action" in response.content["error"]


@pytest.mark.asyncio
async def test_handle_command_missing_parameters(central_agent):
    """Test handling missing parameters"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.USER,
        receiver=AgentType.CENTRAL,
        content={
            "action": "create_video",
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Call handle_command
    response = await central_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.CENTRAL
    assert response.receiver == AgentType.USER
    assert response.content["success"] is False
    assert "error" in response.content
    assert "Missing required parameters" in response.content["error"] 