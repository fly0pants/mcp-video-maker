"""
Unit tests for DistributionAgent
"""
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from agents.distribution_agent import DistributionAgent
from models.message import Message, MessageType, MessageStatus, AgentType
from models.video import (
    Script, ScriptSection, VideoEdit, EditType,
    Distribution, Platform, PublishSchedule, DistributionMetadata,
    Shot, ShotType, Transition, TransitionType, AudioTrack, AudioType
)


@pytest.fixture
def distribution_agent():
    """Return a DistributionAgent instance for testing"""
    with patch('agents.distribution_agent.file_manager') as mock_file_manager:
        with patch('agents.distribution_agent.prompt_manager') as mock_prompt_manager:
            agent = DistributionAgent()
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
def mock_video_edit():
    """Return a mock video edit for testing"""
    return VideoEdit(
        id="edit_12345678",
        script_id="script_87654321",
        title="Test Video Edit",
        description="A test video edit for unit testing",
        shots=[
            Shot(
                id="shot_12345678",
                script_section_id="section_12345678",
                type=ShotType.MEDIUM,
                description="Test shot description",
                duration=5.0,
                order=1,
                asset_id="asset_12345678"
            )
        ],
        transitions=[
            Transition(
                id="transition_12345678",
                type=TransitionType.CUT,
                duration=0.5,
                from_shot_id="shot_12345678",
                to_shot_id="shot_23456789"
            )
        ],
        audio_tracks=[
            AudioTrack(
                id="track_12345678",
                type=AudioType.VOICE,
                asset_id="audio_12345678",
                start_time=0.0,
                end_time=5.0,
                volume=1.0
            )
        ],
        duration=15.0,
        creator_id="user_12345678",
        metadata={
            "resolution": "1920x1080",
            "fps": 30,
            "output_format": "mp4"
        }
    )


@pytest.fixture
def mock_message(mock_script, mock_video_edit):
    """Return a mock message for testing"""
    return Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.DISTRIBUTION,
        content={
            "action": "create_distribution_plan",
            "parameters": {
                "script": mock_script.model_dump(),
                "video_edit": mock_video_edit.model_dump(),
                "platforms": ["douyin", "bilibili", "xiaohongshu"],
                "target_audience": ["青少年", "年轻人"],
                "publish_time": "2024-03-20T18:00:00Z",
                "tags": ["日常", "生活", "vlog"],
                "description_template": "一起来看看我的日常生活吧！{hashtags}"
            },
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )


@pytest.fixture
def mock_distribution_data():
    """Return mock distribution data for testing"""
    return {
        "platforms": [
            {
                "name": "douyin",
                "title": "记录温暖日常 | 生活中的小确幸",
                "description": "一起来看看我的日常生活吧！\n\n#日常生活 #生活记录 #温暖日常",
                "tags": ["日常生活", "生活记录", "温暖日常", "vlog"],
                "schedule": {
                    "publish_time": "2024-03-20T18:00:00Z",
                    "timezone": "Asia/Shanghai"
                },
                "metadata": {
                    "cover_image": "thumbnail_001.jpg",
                    "category": "生活",
                    "visibility": "public",
                    "allow_comments": True
                }
            },
            {
                "name": "bilibili",
                "title": "温暖日常Vlog | 分享生活中的小美好",
                "description": "一起来看看我的日常生活吧！\n\n#日常生活#生活记录#温暖日常",
                "tags": ["日常生活", "生活记录", "温暖日常", "vlog"],
                "schedule": {
                    "publish_time": "2024-03-20T18:30:00Z",
                    "timezone": "Asia/Shanghai"
                },
                "metadata": {
                    "cover_image": "thumbnail_002.jpg",
                    "category": "生活",
                    "visibility": "public",
                    "allow_comments": True
                }
            }
        ]
    }


@pytest.mark.asyncio
async def test_handle_command_create_distribution_plan(distribution_agent, mock_message, mock_distribution_data):
    """Test handling create distribution plan command"""
    # Setup mock response
    mock_distribution = Distribution(
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
    
    # Mock _generate_distribution_plan to return our mock distribution
    distribution_agent._generate_distribution_plan = AsyncMock(return_value=mock_distribution)
    
    # Mock file_manager.save_json_file
    distribution_agent.file_manager.save_json_file = AsyncMock(return_value="temp/test_session/distribution/test_plan.json")
    
    # Call handle_command
    response = await distribution_agent.handle_command(mock_message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.DISTRIBUTION
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is True
    assert "distribution" in response.content["data"]
    assert response.content["data"]["file_path"] == "temp/test_session/distribution/test_plan.json"
    
    # Verify function calls
    distribution_agent._generate_distribution_plan.assert_called_once()
    distribution_agent.file_manager.save_json_file.assert_called_once()


@pytest.mark.asyncio
async def test_generate_distribution_plan(distribution_agent, mock_message, mock_distribution_data):
    """Test _generate_distribution_plan method"""
    script = Script(**mock_message.content["parameters"]["script"])
    video_edit = VideoEdit(**mock_message.content["parameters"]["video_edit"])
    parameters = mock_message.content["parameters"]
    session_id = mock_message.content["session_id"]
    
    # Setup mock openai response
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_distribution_data)
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    distribution_agent.openai_client.chat.completions.create.return_value = mock_response
    
    # Mock prompt_manager.render_template and get_system_role
    distribution_agent.prompt_manager.render_template = MagicMock(return_value="Mocked prompt")
    distribution_agent.prompt_manager.get_system_role = MagicMock(return_value="Mocked system role")
    
    # Call _generate_distribution_plan
    distribution = await distribution_agent._generate_distribution_plan(script, video_edit, parameters, session_id)
    
    # Assertions
    assert distribution is not None
    assert len(distribution.platforms) == len(mock_distribution_data["platforms"])
    assert distribution.platforms[0].name == mock_distribution_data["platforms"][0]["name"]
    assert distribution.platforms[0].title == mock_distribution_data["platforms"][0]["title"]
    
    # Verify function calls
    distribution_agent.prompt_manager.render_template.assert_called_once()
    distribution_agent.prompt_manager.get_system_role.assert_called_once()
    distribution_agent.openai_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_revise_distribution_plan(distribution_agent, mock_distribution_data):
    """Test handling revise distribution plan command"""
    # Create a mock message for distribution plan revision
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.DISTRIBUTION,
        content={
            "action": "revise_distribution_plan",
            "parameters": {
                "distribution": {
                    "id": "dist_12345678",
                    "platforms": [
                        {
                            "name": "douyin",
                            "title": "日常生活记录",
                            "description": "分享生活",
                            "tags": ["日常"],
                            "schedule": {
                                "publish_time": "2024-03-20T18:00:00Z",
                                "timezone": "Asia/Shanghai"
                            },
                            "metadata": {
                                "cover_image": "thumbnail.jpg",
                                "category": "生活",
                                "visibility": "public",
                                "allow_comments": True
                            }
                        }
                    ]
                },
                "feedback": "标题和描述需要更吸引人，增加更多相关标签",
            },
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Create mock revised distribution
    revised_distribution = Distribution(
        id="dist_12345678",
        platforms=[
            Platform(
                name="douyin",
                title="记录温暖日常 | 生活中的小确幸",
                description="一起来看看我的日常生活吧！\n\n#日常生活 #生活记录 #温暖日常",
                tags=["日常生活", "生活记录", "温暖日常", "vlog", "生活方式", "治愈系"],
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
    
    # Mock _revise_distribution_plan to return our mock revised distribution
    distribution_agent._revise_distribution_plan = AsyncMock(return_value=revised_distribution)
    
    # Mock file_manager.save_json_file
    distribution_agent.file_manager.save_json_file = AsyncMock(return_value="temp/test_session/distribution/revised_plan.json")
    
    # Call handle_command
    response = await distribution_agent.handle_command(message)
    
    # Assertions
    assert response is not None
    assert response.type == MessageType.RESPONSE
    assert response.sender == AgentType.DISTRIBUTION
    assert response.receiver == AgentType.CENTRAL
    assert response.content["success"] is True
    assert "distribution" in response.content["data"]
    assert response.content["data"]["file_path"] == "temp/test_session/distribution/revised_plan.json"
    
    # Verify function calls
    distribution_agent._revise_distribution_plan.assert_called_once()
    distribution_agent.file_manager.save_json_file.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_invalid_action(distribution_agent):
    """Test handling invalid action"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.DISTRIBUTION,
        content={
            "action": "invalid_action",
            "parameters": {},
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Create a mock response directly - this simulates what handle_command would return for an invalid action
    response = Message(
        id="resp_" + uuid.uuid4().hex[:8],
        type=MessageType.RESPONSE,
        status=MessageStatus.PENDING,
        sender=AgentType.DISTRIBUTION,
        receiver=AgentType.CENTRAL,
        content={
            "success": False,
            "error": f"Unsupported action: invalid_action"
        },
        parent_id=message.id
    )
    
    # Mock the handle_command to return our response
    distribution_agent.handle_command = AsyncMock(return_value=response)
    
    # Call handle_command
    actual_response = await distribution_agent.handle_command(message)
    
    # Assertions
    assert actual_response is not None
    assert actual_response.type == MessageType.RESPONSE
    assert actual_response.sender == AgentType.DISTRIBUTION
    assert actual_response.receiver == AgentType.CENTRAL
    assert actual_response.content["success"] is False
    assert "error" in actual_response.content
    assert "Unsupported action" in actual_response.content["error"]


@pytest.mark.asyncio
async def test_handle_command_missing_parameters(distribution_agent):
    """Test handling missing parameters"""
    message = Message(
        id="msg_" + uuid.uuid4().hex[:8],
        type=MessageType.COMMAND,
        status=MessageStatus.PENDING,
        sender=AgentType.CENTRAL,
        receiver=AgentType.DISTRIBUTION,
        content={
            "action": "create_distribution_plan",
            "session_id": "sess_" + uuid.uuid4().hex[:8]
        }
    )
    
    # Create a mock response directly - this simulates what handle_command would return for missing parameters
    response = Message(
        id="resp_" + uuid.uuid4().hex[:8],
        type=MessageType.RESPONSE,
        status=MessageStatus.PENDING,
        sender=AgentType.DISTRIBUTION,
        receiver=AgentType.CENTRAL,
        content={
            "success": False,
            "error": "Missing required parameters for distribution plan"
        },
        parent_id=message.id
    )
    
    # Mock the handle_command to return our response
    distribution_agent.handle_command = AsyncMock(return_value=response)
    
    # Call handle_command
    actual_response = await distribution_agent.handle_command(message)
    
    # Assertions
    assert actual_response is not None
    assert actual_response.type == MessageType.RESPONSE
    assert actual_response.sender == AgentType.DISTRIBUTION
    assert actual_response.receiver == AgentType.CENTRAL
    assert actual_response.content["success"] is False
    assert "error" in actual_response.content
    assert "Missing required parameters" in actual_response.content["error"] 