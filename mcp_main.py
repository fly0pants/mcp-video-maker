#!/usr/bin/env python3
"""
基于MCP协议的多代理视频生成系统主程序
"""

import asyncio
import logging
import os
import signal
import sys
from typing import List, Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入MCP相关模块
from models.mcp import (
    MCPMessage, MCPMessageType, MCPStatus, MCPPriority,
    create_command_message, create_event_message
)
from utils.mcp_message_bus import mcp_message_bus
from agents.mcp_central_agent import MCPCentralAgent
from agents.mcp_content_agent import MCPContentAgent
from agents.mcp_visual_agent import MCPVisualAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mcp_system.log")
    ]
)
logger = logging.getLogger("mcp_main")

# 创建FastAPI应用
app = FastAPI(
    title="MCP视频生成系统API",
    description="基于MCP协议的多代理视频生成系统API",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 代理实例
central_agent = None
content_agent = None
visual_agent = None
agents = []

# API模型
class VideoCreationRequest(BaseModel):
    """视频创建请求"""
    theme: str = Field(..., description="视频主题")
    style: str = Field("幽默", description="视频风格")
    script_type: str = Field("知识普及", description="脚本类型")
    target_audience: List[str] = Field(["年轻人", "学生"], description="目标受众")
    duration: float = Field(60.0, description="视频时长(秒)")
    language: str = Field("zh", description="语言")
    keywords: Optional[List[str]] = Field(None, description="关键词")
    special_requirements: Optional[str] = Field(None, description="特殊要求")
    video_model: str = Field("wan", description="视频生成模型")
    resolution: str = Field("1080x1920", description="分辨率")

class WorkflowStatusResponse(BaseModel):
    """工作流状态响应"""
    workflow_id: str
    session_id: str
    status: str
    current_stage: str
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    stages: Dict[str, Dict[str, Any]]
    errors: List[Dict[str, Any]]
    has_assets: Dict[str, bool]

class AgentStatusResponse(BaseModel):
    """代理状态响应"""
    agent_statuses: Dict[str, Dict[str, Any]]

# 启动时初始化
@app.on_event("startup")
async def startup():
    """启动时初始化代理系统"""
    global central_agent, content_agent, visual_agent, agents
    
    logger.info("Starting MCP agent system...")
    
    try:
        # 启动消息总线
        await mcp_message_bus.start()
        logger.info("MCP Message Bus started")
        
        # 创建代理实例
        central_agent = MCPCentralAgent()
        content_agent = MCPContentAgent()
        visual_agent = MCPVisualAgent()
        
        # 保存代理列表
        agents = [central_agent, content_agent, visual_agent]
        
        # 初始化并启动代理
        for agent in agents:
            await agent.initialize()
            await agent.start()
            logger.info(f"Agent {agent.agent_name} ({agent.agent_id}) started")
            
        logger.info("MCP agent system started successfully")
        
    except Exception as e:
        logger.error(f"Error starting MCP agent system: {str(e)}")
        # 尝试清理已启动的资源
        await shutdown()
        raise

# 关闭时清理
@app.on_event("shutdown")
async def shutdown():
    """关闭时清理资源"""
    logger.info("Shutting down MCP agent system...")
    
    # 停止代理
    if agents:
        for agent in reversed(agents):  # 反向停止，先停中央代理
            if agent and agent.is_running:
                try:
                    await agent.stop()
                    logger.info(f"Agent {agent.agent_name} ({agent.agent_id}) stopped")
                except Exception as e:
                    logger.error(f"Error stopping agent {agent.agent_id}: {str(e)}")
    
    # 停止消息总线
    try:
        await mcp_message_bus.stop()
        logger.info("MCP Message Bus stopped")
    except Exception as e:
        logger.error(f"Error stopping MCP Message Bus: {str(e)}")
    
    logger.info("MCP agent system shutdown complete")

# API路由
@app.post("/api/videos", response_model=Dict[str, Any], tags=["视频生成"])
async def create_video(request: VideoCreationRequest):
    """创建视频"""
    if not central_agent or not central_agent.is_running:
        raise HTTPException(status_code=503, detail="Central agent is not available")
    
    try:
        # 创建会话ID
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # 发送命令给中央代理
        response = await central_agent.send_command(
            target="central_agent",
            action="create_video",
            parameters=request.dict(),
            session_id=session_id,
            wait_for_response=True,
            response_timeout=30.0
        )
        
        if not response:
            raise HTTPException(status_code=504, detail="Timeout waiting for response from central agent")
            
        # 检查响应
        if response.header.message_type == MCPMessageType.ERROR:
            error_message = "Unknown error"
            if hasattr(response.body, "error_message"):
                error_message = response.body.error_message
            raise HTTPException(status_code=500, detail=error_message)
            
        # 返回工作流信息
        return {
            "success": True,
            "message": "Video creation workflow started",
            "workflow_id": response.body.data.get("workflow_id"),
            "session_id": response.body.data.get("session_id")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating video: {str(e)}")

@app.get("/api/workflows/{workflow_id}", response_model=WorkflowStatusResponse, tags=["工作流"])
async def get_workflow_status(workflow_id: str):
    """获取工作流状态"""
    if not central_agent or not central_agent.is_running:
        raise HTTPException(status_code=503, detail="Central agent is not available")
    
    try:
        # 发送命令给中央代理
        response = await central_agent.send_command(
            target="central_agent",
            action="get_workflow_status",
            parameters={"workflow_id": workflow_id},
            wait_for_response=True,
            response_timeout=10.0
        )
        
        if not response:
            raise HTTPException(status_code=504, detail="Timeout waiting for response from central agent")
            
        # 检查响应
        if response.header.message_type == MCPMessageType.ERROR:
            error_message = "Unknown error"
            if hasattr(response.body, "error_message"):
                error_message = response.body.error_message
            raise HTTPException(status_code=500, detail=error_message)
            
        # 获取工作流状态
        workflow_status = response.body.data.get("workflow_status", {})
        
        if workflow_status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
            
        return workflow_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting workflow status: {str(e)}")

@app.get("/api/agents/status", response_model=AgentStatusResponse, tags=["代理"])
async def get_agent_status():
    """获取所有代理状态"""
    if not central_agent or not central_agent.is_running:
        raise HTTPException(status_code=503, detail="Central agent is not available")
    
    try:
        # 发送命令给中央代理
        response = await central_agent.send_command(
            target="central_agent",
            action="get_agent_status",
            parameters={},
            wait_for_response=True,
            response_timeout=10.0
        )
        
        if not response:
            raise HTTPException(status_code=504, detail="Timeout waiting for response from central agent")
            
        # 检查响应
        if response.header.message_type == MCPMessageType.ERROR:
            error_message = "Unknown error"
            if hasattr(response.body, "error_message"):
                error_message = response.body.error_message
            raise HTTPException(status_code=500, detail=error_message)
            
        # 返回代理状态
        return {
            "agent_statuses": response.body.data.get("agent_statuses", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting agent status: {str(e)}")

@app.get("/api/health", tags=["系统"])
async def health_check():
    """系统健康检查"""
    # 检查消息总线状态
    bus_metrics = mcp_message_bus.get_metrics()
    
    # 检查代理状态
    agents_status = {
        "central_agent": central_agent.is_running if central_agent else False,
        "content_agent": content_agent.is_running if content_agent else False,
        "visual_agent": visual_agent.is_running if visual_agent else False
    }
    
    return {
        "status": "ok",
        "message_bus": {
            "running": True,
            "uptime_seconds": bus_metrics.get("uptime_seconds", 0),
            "messages_processed": bus_metrics.get("messages_processed", 0),
            "queue_size": bus_metrics.get("queue_size", 0)
        },
        "agents": agents_status
    }

# 处理信号
def handle_signals():
    """设置信号处理器"""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(shutdown())
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# 直接运行
if __name__ == "__main__":
    handle_signals()
    uvicorn.run("mcp_main:app", host="0.0.0.0", port=8000, reload=False) 