"""
代理测试
测试各个代理的基本功能
"""

import asyncio
import pytest

from agents import (
    CentralAgent,
    ContentAgent,
    VisualAgent,
    AudioAgent,
    PostProductionAgent,
    DistributionAgent,
)
from models.mcp import create_command_message
from utils.mcp_message_bus import MCPMessageBus


@pytest.fixture
async def message_bus():
    """创建测试用消息总线"""
    bus = MCPMessageBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def content_agent(message_bus):
    """创建内容代理"""
    agent = ContentAgent()
    await agent.initialize()
    await agent.start()
    yield agent
    await agent.stop()


@pytest.fixture
async def visual_agent(message_bus):
    """创建视觉代理"""
    agent = VisualAgent()
    await agent.initialize()
    await agent.start()
    yield agent
    await agent.stop()


@pytest.fixture
async def audio_agent(message_bus):
    """创建音频代理"""
    agent = AudioAgent()
    await agent.initialize()
    await agent.start()
    yield agent
    await agent.stop()


class TestContentAgent:
    """内容代理测试"""
    
    @pytest.mark.asyncio
    async def test_create_script(self, content_agent, message_bus):
        """测试创建脚本"""
        command = create_command_message(
            source="test",
            target="content_agent",
            action="create_script",
            parameters={
                "theme": "人工智能",
                "style": "科技",
                "duration": 60,
                "target_audience": "年轻人"
            }
        )
        
        await message_bus.publish(command)
        
        response = await message_bus.wait_for_response(
            message_id=command.header.message_id,
            timeout=30.0,
            expected_source="content_agent"
        )
        
        assert response is not None
        assert response.body.success is True
        assert "script_id" in response.body.data
        assert "script" in response.body.data
        
        script = response.body.data["script"]
        assert "title" in script
        assert "scenes" in script
        assert len(script["scenes"]) > 0
    
    @pytest.mark.asyncio
    async def test_suggest_hooks(self, content_agent, message_bus):
        """测试生成开场钩子"""
        command = create_command_message(
            source="test",
            target="content_agent",
            action="suggest_hooks",
            parameters={
                "theme": "健康生活",
                "style": "生活",
                "count": 3
            }
        )
        
        await message_bus.publish(command)
        
        response = await message_bus.wait_for_response(
            message_id=command.header.message_id,
            timeout=10.0,
            expected_source="content_agent"
        )
        
        assert response is not None
        assert response.body.success is True
        assert "hooks" in response.body.data
        assert len(response.body.data["hooks"]) <= 3


class TestVisualAgent:
    """视觉代理测试"""
    
    @pytest.mark.asyncio
    async def test_list_models(self, visual_agent, message_bus):
        """测试列出视频模型"""
        command = create_command_message(
            source="test",
            target="visual_agent",
            action="list_models",
            parameters={}
        )
        
        await message_bus.publish(command)
        
        response = await message_bus.wait_for_response(
            message_id=command.header.message_id,
            timeout=10.0,
            expected_source="visual_agent"
        )
        
        assert response is not None
        assert response.body.success is True
        assert "models" in response.body.data
        assert "keling" in response.body.data["models"]


class TestAudioAgent:
    """音频代理测试"""
    
    @pytest.mark.asyncio
    async def test_list_voices(self, audio_agent, message_bus):
        """测试列出语音模型"""
        command = create_command_message(
            source="test",
            target="audio_agent",
            action="list_voices",
            parameters={}
        )
        
        await message_bus.publish(command)
        
        response = await message_bus.wait_for_response(
            message_id=command.header.message_id,
            timeout=10.0,
            expected_source="audio_agent"
        )
        
        assert response is not None
        assert response.body.success is True
        assert "voice_models" in response.body.data
        assert "voice_presets" in response.body.data


class TestMessageBus:
    """消息总线测试"""
    
    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        """测试发布订阅"""
        bus = MCPMessageBus()
        await bus.start()
        
        received_messages = []
        
        async def callback(message):
            received_messages.append(message)
        
        await bus.subscribe_direct("test_target", callback)
        
        command = create_command_message(
            source="test_source",
            target="test_target",
            action="test_action",
            parameters={"key": "value"}
        )
        
        await bus.publish(command)
        
        # 等待消息处理
        await asyncio.sleep(0.5)
        
        assert len(received_messages) == 1
        assert received_messages[0].header.message_id == command.header.message_id
        
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_metrics(self):
        """测试指标收集"""
        bus = MCPMessageBus()
        await bus.start()
        
        metrics = bus.get_metrics()
        
        assert "messages_processed" in metrics
        assert "messages_published" in metrics
        assert "queue_size" in metrics
        
        await bus.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
