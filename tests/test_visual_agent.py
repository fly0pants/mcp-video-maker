"""
Unit tests for VisualAgent
"""
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from agents.visual_agent import VisualAgent
from models.message import Message, MessageType, MessageStatus, AgentType
from models.video import Script, ScriptSection, Shot, ShotType, Transition, TransitionType


@pytest.fixture
def visual_agent():
    """Return a VisualAgent instance for testing"""
    with patch('agents.visual_agent.file_manager') as mock_file_manager:
        with patch('agents.visual_agent.prompt_manager') as mock_prompt_manager:
            agent = VisualAgent()
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
def mock_message(mock_script):
    """Return a mock message for testing"""
    return Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.VISUAL,
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


@pytest.fixture
def mock_shots_data():
    """Return mock shots data for testing"""
    return {
        "shots": [
            {
                "type": "CLOSE_UP",
                "description": "特写镜头，主角面带微笑对着镜头",
                "duration": 5.0,
                "camera_movement": "STATIC",
                "composition": "居中构图，主角面部占据画面中心",
                "lighting": "自然光，补光灯提亮面部",
                "props": ["补光灯"],
                "special_effects": ["温暖色调"],
                "tags": ["开场", "微笑", "特写"]
            },
            {
                "type": "MEDIUM",
                "description": "中景镜头，展示主角上半身和周围环境",
                "duration": 5.0,
                "camera_movement": "SLOW_ZOOM_IN",
                "composition": "三分法构图，主角位于左侧",
                "lighting": "自然光为主，侧光营造氛围",
                "props": ["环境装饰"],
                "special_effects": ["景深效果"],
                "tags": ["环境", "氛围", "中景"]
            }
        ],
        "transitions": [
            {
                "type": "FADE",
                "duration": 0.5,
                "description": "淡入淡出过渡",
                "parameters": {
                    "color": "#000000"
                }
            }
        ]
    }


@pytest.mark.asyncio
async def test_handle_command_create_shots(visual_agent, mock_message, mock_shots_data):
    """Test handling create shots command"""
    # Setup mock response
    mock_shots = [
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
    
    mock_transitions = [
        Transition(
            id="transition_12345678",
            type=TransitionType.FADE,
            duration=0.5,
            description="淡入淡出过渡",
            parameters={"color": "#000000"},
            order=0
        )
    ]
    
    # Mock _generate_shots to return our mock shots and transitions
    visual_agent._generate_shots = AsyncMock(return_value=(mock_shots, mock_transitions))
    
    # Mock file_manager.save_json_file
    visual_agent.file_manager.save_json_file = AsyncMock(return_value="temp/test_session/shots/test_shots.json")
    
    # Call handle_command
    response = await visual_agent.handle_command(mock_message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.VISUAL
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is True
    assert "shots" in response.content["data"]
    assert "transitions" in response.content["data"]
    assert response.content["data"]["file_path"] == "temp/test_session/shots/test_shots.json"
    
    # Verify function calls
    visual_agent._generate_shots.assert_called_once()
    visual_agent.file_manager.save_json_file.assert_called_once()


@pytest.mark.asyncio
async def test_generate_shots(visual_agent, mock_message, mock_shots_data):
    """Test _generate_shots method"""
    script = Script(**mock_message.content["parameters"]["script"])
    parameters = mock_message.content["parameters"]
    session_id = mock_message.content["session_id"]
    
    # Setup mock openai response
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_shots_data)
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    visual_agent.openai_client.chat.completions.create.return_value = mock_response
    
    # Mock prompt_manager.render_template and get_system_role
    visual_agent.prompt_manager.render_template = MagicMock(return_value="Mocked prompt")
    visual_agent.prompt_manager.get_system_role = MagicMock(return_value="Mocked system role")
    
    # Call _generate_shots
    shots, transitions = await visual_agent._generate_shots(script, parameters, session_id)
    
    # Assertions
    assert shots is not None
    assert transitions is not None
    assert len(shots) == len(mock_shots_data["shots"])
    assert len(transitions) == len(mock_shots_data["transitions"])
    assert shots[0].type == ShotType.CLOSE_UP
    assert transitions[0].type == TransitionType.FADE
    
    # Verify function calls
    visual_agent.prompt_manager.render_template.assert_called_once()
    visual_agent.prompt_manager.get_system_role.assert_called_once()
    visual_agent.openai_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_revise_shots(visual_agent, mock_shots_data):
    """Test handling revise shots command"""
    # Create a mock message for shots revision
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.VISUAL,
        content={
            "action": "revise_shots",
            "parameters": {
                "shots": [
                    {
                        "id": "shot_12345678",
                        "type": "CLOSE_UP",
                        "description": "特写镜头，主角面带微笑对着镜头",
                        "duration": 5.0,
                        "camera_movement": "STATIC",
                        "composition": "居中构图",
                        "lighting": "自然光",
                        "props": ["补光灯"],
                        "special_effects": [],
                        "tags": ["开场", "微笑"],
                        "order": 0,
                        "section_id": "section_123456"
                    }
                ],
                "transitions": [
                    {
                        "id": "transition_12345678",
                        "type": "CUT",
                        "duration": 0.0,
                        "description": "直接切换",
                        "parameters": {},
                        "order": 0
                    }
                ],
                "feedback": "需要更多动态的镜头和特效",
            },
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Create mock revised shots and transitions
    revised_shots = [
        Shot(
            id="shot_12345678",
            type=ShotType.CLOSE_UP,
            description="特写镜头，主角面带微笑对着镜头，缓慢旋转",
            duration=5.0,
            camera_movement="SLOW_ROTATE",
            composition="动态居中构图",
            lighting="自然光，补光灯提亮面部",
            props=["补光灯", "旋转台"],
            special_effects=["温暖色调", "光晕效果"],
            tags=["开场", "微笑", "动态"],
            order=0,
            section_id="section_123456"
        )
    ]
    
    revised_transitions = [
        Transition(
            id="transition_12345678",
            type=TransitionType.ZOOM_BLUR,
            duration=0.8,
            description="带模糊效果的缩放过渡",
            parameters={"blur_intensity": 0.5},
            order=0
        )
    ]
    
    # Mock _revise_shots to return our mock revised shots and transitions
    visual_agent._revise_shots = AsyncMock(return_value=(revised_shots, revised_transitions))
    
    # Mock file_manager.save_json_file
    visual_agent.file_manager.save_json_file = AsyncMock(return_value="temp/test_session/shots/revised_shots.json")
    
    # Call handle_command
    response = await visual_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.VISUAL
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is True
    assert "shots" in response.content["data"]
    assert "transitions" in response.content["data"]
    assert response.content["data"]["file_path"] == "temp/test_session/shots/revised_shots.json"
    
    # Verify function calls
    visual_agent._revise_shots.assert_called_once()
    visual_agent.file_manager.save_json_file.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_invalid_action(visual_agent):
    """Test handling invalid action"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.VISUAL,
        content={
            "action": "invalid_action",
            "parameters": {},
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Call handle_command
    response = await visual_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.VISUAL
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is False
    assert "error" in response.content
    assert "Unsupported action" in response.content["error"]


@pytest.mark.asyncio
async def test_handle_command_missing_parameters(visual_agent):
    """Test handling missing parameters"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.VISUAL,
        content={
            "action": "create_shots",
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Call handle_command
    response = await visual_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.VISUAL
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is False
    assert "error" in response.content
    assert "Missing required parameters" in response.content["error"] 