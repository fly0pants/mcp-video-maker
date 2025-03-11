"""
Unit tests for PostProdAgent
"""
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from agents.postprod_agent import PostProdAgent
from models.message import Message, MessageType, MessageStatus, AgentType
from models.video import (
    Script, ScriptSection, Shot, ShotType, Transition, TransitionType,
    AudioTrack, AudioType, AudioEffect, EffectType, VideoEdit, EditType
)


@pytest.fixture
def postprod_agent():
    """Return a PostProdAgent instance for testing"""
    with patch('agents.postprod_agent.file_manager') as mock_file_manager:
        with patch('agents.postprod_agent.prompt_manager') as mock_prompt_manager:
            agent = PostProdAgent()
            agent.logger = MagicMock()
            agent.openai_client = MagicMock()
            agent.openai_client.chat.completions.create = AsyncMock()
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
def mock_message(mock_script, mock_shots, mock_transitions, mock_audio_tracks, mock_audio_effects):
    """Return a mock message for testing"""
    return Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.POSTPROD,
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


@pytest.fixture
def mock_edit_data():
    """Return mock edit data for testing"""
    return {
        "timeline": [
            {
                "type": "VIDEO",
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
            },
            {
                "type": "AUDIO",
                "source": "track_12345678",
                "start_time": 0.0,
                "end_time": 15.0,
                "track": 1,
                "effects": [
                    {
                        "type": "FADE",
                        "parameters": {
                            "start_volume": 0.0,
                            "end_volume": 1.0,
                            "duration": 1.0
                        }
                    }
                ]
            }
        ],
        "metadata": {
            "total_duration": 15.0,
            "resolution": "1920x1080",
            "fps": 30,
            "output_format": "mp4"
        }
    }


@pytest.mark.asyncio
async def test_handle_command_create_video_edit(postprod_agent, mock_message, mock_edit_data):
    """Test handling create video edit command"""
    # Setup mock response
    mock_edit = VideoEdit(
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
    
    # Mock _generate_video_edit to return our mock edit
    postprod_agent._generate_video_edit = AsyncMock(return_value=mock_edit)
    
    # Mock file_manager.save_json_file
    postprod_agent.file_manager.save_json_file = AsyncMock(return_value="temp/test_session/edits/test_edit.json")
    
    # Call handle_command
    response = await postprod_agent.handle_command(mock_message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.POSTPROD
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is True
    assert "edit" in response.content["data"]
    assert response.content["data"]["file_path"] == "temp/test_session/edits/test_edit.json"
    
    # Verify function calls
    postprod_agent._generate_video_edit.assert_called_once()
    postprod_agent.file_manager.save_json_file.assert_called_once()


@pytest.mark.asyncio
async def test_generate_video_edit(postprod_agent, mock_message, mock_edit_data):
    """Test _generate_video_edit method"""
    script = Script(**mock_message.content["parameters"]["script"])
    shots = [Shot(**shot) for shot in mock_message.content["parameters"]["shots"]]
    transitions = [Transition(**trans) for trans in mock_message.content["parameters"]["transitions"]]
    audio_tracks = [AudioTrack(**track) for track in mock_message.content["parameters"]["audio_tracks"]]
    audio_effects = [AudioEffect(**effect) for effect in mock_message.content["parameters"]["audio_effects"]]
    parameters = mock_message.content["parameters"]
    session_id = mock_message.content["session_id"]
    
    # Setup mock openai response
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_edit_data)
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    postprod_agent.openai_client.chat.completions.create.return_value = mock_response
    
    # Mock prompt_manager.render_template and get_system_role
    postprod_agent.prompt_manager.render_template = MagicMock(return_value="Mocked prompt")
    postprod_agent.prompt_manager.get_system_role = MagicMock(return_value="Mocked system role")
    
    # Call _generate_video_edit
    edit = await postprod_agent._generate_video_edit(
        script, shots, transitions, audio_tracks, audio_effects, parameters, session_id
    )
    
    # Assertions
    assert edit is not None
    assert len(edit.timeline) == len(mock_edit_data["timeline"])
    assert edit.metadata["total_duration"] == mock_edit_data["metadata"]["total_duration"]
    assert edit.metadata["resolution"] == mock_edit_data["metadata"]["resolution"]
    assert edit.metadata["fps"] == mock_edit_data["metadata"]["fps"]
    
    # Verify function calls
    postprod_agent.prompt_manager.render_template.assert_called_once()
    postprod_agent.prompt_manager.get_system_role.assert_called_once()
    postprod_agent.openai_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_revise_video_edit(postprod_agent, mock_edit_data):
    """Test handling revise video edit command"""
    # Create a mock message for video edit revision
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.POSTPROD,
        content={
            "action": "revise_video_edit",
            "parameters": {
                "edit": {
                    "id": "edit_12345678",
                    "timeline": [
                        {
                            "type": "VIDEO",
                            "source": "shot_12345678",
                            "start_time": 0.0,
                            "end_time": 5.0,
                            "track": 0,
                            "effects": []
                        }
                    ],
                    "metadata": {
                        "total_duration": 15.0,
                        "resolution": "1920x1080",
                        "fps": 30,
                        "output_format": "mp4"
                    }
                },
                "feedback": "需要添加更多视觉效果和转场",
            },
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Create mock revised edit
    revised_edit = VideoEdit(
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
                    },
                    {
                        "type": "MOTION_GRAPHICS",
                        "parameters": {
                            "template": "modern_title",
                            "text": "精彩日常"
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
    
    # Mock _revise_video_edit to return our mock revised edit
    postprod_agent._revise_video_edit = AsyncMock(return_value=revised_edit)
    
    # Mock file_manager.save_json_file
    postprod_agent.file_manager.save_json_file = AsyncMock(return_value="temp/test_session/edits/revised_edit.json")
    
    # Call handle_command
    response = await postprod_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.POSTPROD
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is True
    assert "edit" in response.content["data"]
    assert response.content["data"]["file_path"] == "temp/test_session/edits/revised_edit.json"
    
    # Verify function calls
    postprod_agent._revise_video_edit.assert_called_once()
    postprod_agent.file_manager.save_json_file.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_invalid_action(postprod_agent):
    """Test handling invalid action"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.POSTPROD,
        content={
            "action": "invalid_action",
            "parameters": {},
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Call handle_command
    response = await postprod_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.POSTPROD
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is False
    assert "error" in response.content
    assert "Unsupported action" in response.content["error"]


@pytest.mark.asyncio
async def test_handle_command_missing_parameters(postprod_agent):
    """Test handling missing parameters"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.POSTPROD,
        content={
            "action": "create_video_edit",
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Call handle_command
    response = await postprod_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.POSTPROD
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is False
    assert "error" in response.content
    assert "Missing required parameters" in response.content["error"] 