"""
系统集成测试
测试完整的视频生成工作流
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


class TestSystemIntegration:
    """系统集成测试"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """设置测试环境"""
        # 创建消息总线
        self.message_bus = MCPMessageBus()
        await self.message_bus.start()
        
        # 创建所有代理
        self.agents = {
            "central": CentralAgent(),
            "content": ContentAgent(),
            "visual": VisualAgent(),
            "audio": AudioAgent(),
            "postprod": PostProductionAgent(),
            "distribution": DistributionAgent(),
        }
        
        # 初始化并启动所有代理
        for agent in self.agents.values():
            await agent.initialize()
            await agent.start()
        
        yield
        
        # 清理
        for agent in self.agents.values():
            await agent.stop()
        await self.message_bus.stop()
    
    @pytest.mark.asyncio
    async def test_create_video_workflow(self):
        """测试创建视频工作流"""
        central_agent = self.agents["central"]
        
        # 创建视频请求
        command = create_command_message(
            source="test",
            target="central_agent",
            action="create_video",
            parameters={
                "theme": "人工智能发展",
                "style": "科技",
                "duration": 30,
                "target_audience": "科技爱好者",
                "auto_distribute": False
            }
        )
        
        await self.message_bus.publish(command)
        
        response = await self.message_bus.wait_for_response(
            message_id=command.header.message_id,
            timeout=10.0,
            expected_source="central_agent"
        )
        
        assert response is not None
        assert response.body.success is True
        assert "workflow_id" in response.body.data
        
        workflow_id = response.body.data["workflow_id"]
        
        # 等待工作流执行一段时间
        await asyncio.sleep(2)
        
        # 检查工作流状态
        workflow = central_agent.get_workflow(workflow_id)
        assert workflow is not None
        assert workflow.status.value in ["processing", "completed", "failed"]
    
    @pytest.mark.asyncio
    async def test_get_workflow_status(self):
        """测试获取工作流状态"""
        central_agent = self.agents["central"]
        
        # 首先创建一个工作流
        create_command = create_command_message(
            source="test",
            target="central_agent",
            action="create_video",
            parameters={
                "theme": "测试主题",
                "style": "幽默",
                "duration": 15
            }
        )
        
        await self.message_bus.publish(create_command)
        
        create_response = await self.message_bus.wait_for_response(
            message_id=create_command.header.message_id,
            timeout=10.0,
            expected_source="central_agent"
        )
        
        assert create_response is not None
        workflow_id = create_response.body.data["workflow_id"]
        
        # 查询状态
        status_command = create_command_message(
            source="test",
            target="central_agent",
            action="get_workflow_status",
            parameters={"workflow_id": workflow_id}
        )
        
        await self.message_bus.publish(status_command)
        
        status_response = await self.message_bus.wait_for_response(
            message_id=status_command.header.message_id,
            timeout=5.0,
            expected_source="central_agent"
        )
        
        assert status_response is not None
        assert status_response.body.success is True
        assert status_response.body.data["workflow_id"] == workflow_id
    
    @pytest.mark.asyncio
    async def test_list_workflows(self):
        """测试列出工作流"""
        command = create_command_message(
            source="test",
            target="central_agent",
            action="list_workflows",
            parameters={"limit": 10}
        )
        
        await self.message_bus.publish(command)
        
        response = await self.message_bus.wait_for_response(
            message_id=command.header.message_id,
            timeout=5.0,
            expected_source="central_agent"
        )
        
        assert response is not None
        assert response.body.success is True
        assert "workflows" in response.body.data
        assert "total" in response.body.data
    
    @pytest.mark.asyncio
    async def test_agent_heartbeats(self):
        """测试代理心跳"""
        # 等待心跳发送
        await asyncio.sleep(2)
        
        # 检查所有代理状态
        for name, agent in self.agents.items():
            status = agent.get_status()
            assert status["status"] == "running"
            assert status["uptime"] > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_workflows(self):
        """测试并发工作流"""
        # 同时创建多个工作流
        tasks = []
        for i in range(3):
            command = create_command_message(
                source="test",
                target="central_agent",
                action="create_video",
                parameters={
                    "theme": f"测试主题 {i+1}",
                    "style": "幽默",
                    "duration": 10
                }
            )
            tasks.append(self.message_bus.publish(command))
        
        await asyncio.gather(*tasks)
        
        # 等待处理
        await asyncio.sleep(1)
        
        # 验证所有工作流都已创建
        central_agent = self.agents["central"]
        workflows = central_agent.get_all_workflows()
        assert len(workflows) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
