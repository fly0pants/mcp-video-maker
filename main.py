"""
MCP Video Maker 主程序入口
TikTok 风格短视频多代理协作生成系统
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents import (
    CentralAgent,
    ContentAgent,
    VisualAgent,
    AudioAgent,
    PostProductionAgent,
    DistributionAgent,
)
from config import config
from utils import file_manager, message_bus, setup_logger, get_logger


# 全局代理实例
agents = {}
logger = None


class CreateVideoRequest(BaseModel):
    """创建视频请求"""
    theme: str = Field(..., description="视频主题")
    style: str = Field(default="幽默", description="视频风格")
    duration: int = Field(default=60, description="视频时长（秒）")
    target_audience: str = Field(default="年轻人", description="目标受众")
    video_style: str = Field(default="realistic", description="视觉风格")
    voice_style: str = Field(default="natural", description="语音风格")
    music_style: str = Field(default="upbeat", description="音乐风格")
    aspect_ratio: str = Field(default="9:16", description="宽高比")
    quality: str = Field(default="high", description="输出质量")
    auto_distribute: bool = Field(default=False, description="是否自动分发")
    platforms: list = Field(default=["tiktok"], description="分发平台")


class WorkflowStatusRequest(BaseModel):
    """工作流状态请求"""
    workflow_id: str = Field(..., description="工作流ID")


class UserSelectionRequest(BaseModel):
    """用户选择请求"""
    workflow_id: str = Field(..., description="工作流ID")
    selection_type: str = Field(..., description="选择类型")
    selection_value: str = Field(..., description="选择值")


async def initialize_agents():
    """初始化所有代理"""
    global agents, logger
    
    logger = get_logger("main")
    logger.info("初始化代理系统...")
    
    # 创建代理实例
    agents["central"] = CentralAgent()
    agents["content"] = ContentAgent()
    agents["visual"] = VisualAgent()
    agents["audio"] = AudioAgent()
    agents["postprod"] = PostProductionAgent()
    agents["distribution"] = DistributionAgent()
    
    # 启动消息总线
    await message_bus.start()
    logger.info("消息总线已启动")
    
    # 初始化文件管理器
    await file_manager.initialize()
    logger.info("文件管理器已初始化")
    
    # 初始化并启动所有代理
    for name, agent in agents.items():
        await agent.initialize()
        await agent.start()
        logger.info(f"代理 {name} 已启动")
    
    logger.info("所有代理初始化完成")


async def shutdown_agents():
    """关闭所有代理"""
    global agents, logger
    
    if logger:
        logger.info("正在关闭代理系统...")
    
    # 停止所有代理
    for name, agent in agents.items():
        await agent.stop()
        if logger:
            logger.info(f"代理 {name} 已停止")
    
    # 停止消息总线
    await message_bus.stop()
    if logger:
        logger.info("消息总线已停止")
    
    if logger:
        logger.info("代理系统已关闭")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    setup_logger(
        log_level="INFO",
        log_file="./logs/mcp_video_maker.log",
        rotation="10 MB",
        retention="7 days"
    )
    await initialize_agents()
    
    yield
    
    # 关闭时清理
    await shutdown_agents()


# 创建 FastAPI 应用
app = FastAPI(
    title="MCP Video Maker",
    description="TikTok 风格短视频多代理协作生成系统",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "MCP Video Maker",
        "version": "1.0.0",
        "status": "running",
        "description": "TikTok 风格短视频多代理协作生成系统"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    agent_status = {}
    for name, agent in agents.items():
        status = agent.get_status()
        agent_status[name] = {
            "status": status["status"],
            "uptime": status["uptime"],
            "messages_processed": status["messages_processed"]
        }
    
    return {
        "status": "healthy",
        "agents": agent_status,
        "message_bus": message_bus.get_metrics()
    }


@app.post("/api/videos/create")
async def create_video(request: CreateVideoRequest):
    """
    创建视频
    
    启动一个新的视频生成工作流
    """
    central_agent = agents.get("central")
    if not central_agent:
        raise HTTPException(status_code=500, detail="中央代理未初始化")
    
    try:
        # 创建工作流
        from models.mcp import create_command_message
        
        command_msg = create_command_message(
            source="api",
            target="central_agent",
            action="create_video",
            parameters=request.model_dump()
        )
        
        # 发送命令
        await message_bus.publish(command_msg)
        
        # 等待响应
        response = await message_bus.wait_for_response(
            message_id=command_msg.header.message_id,
            timeout=10.0,
            expected_source="central_agent"
        )
        
        if response and response.body.success:
            return {
                "success": True,
                "data": response.body.data
            }
        else:
            error_msg = response.body.message if response else "请求超时"
            raise HTTPException(status_code=400, detail=error_msg)
            
    except Exception as e:
        logger.error(f"创建视频失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """
    获取工作流状态
    
    查询指定工作流的当前状态和进度
    """
    central_agent = agents.get("central")
    if not central_agent:
        raise HTTPException(status_code=500, detail="中央代理未初始化")
    
    workflow = central_agent.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_id} 不存在")
    
    return {
        "success": True,
        "data": workflow.to_dict()
    }


@app.post("/api/videos/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """
    取消工作流
    
    取消正在进行的视频生成工作流
    """
    central_agent = agents.get("central")
    if not central_agent:
        raise HTTPException(status_code=500, detail="中央代理未初始化")
    
    workflow = central_agent.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_id} 不存在")
    
    try:
        from models.mcp import create_command_message
        
        command_msg = create_command_message(
            source="api",
            target="central_agent",
            action="cancel_workflow",
            parameters={"workflow_id": workflow_id}
        )
        
        await message_bus.publish(command_msg)
        
        response = await message_bus.wait_for_response(
            message_id=command_msg.header.message_id,
            timeout=5.0,
            expected_source="central_agent"
        )
        
        if response and response.body.success:
            return {
                "success": True,
                "data": response.body.data
            }
        else:
            error_msg = response.body.message if response else "请求超时"
            raise HTTPException(status_code=400, detail=error_msg)
            
    except Exception as e:
        logger.error(f"取消工作流失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/videos/{workflow_id}/select")
async def user_selection(workflow_id: str, request: UserSelectionRequest):
    """
    用户选择
    
    在需要用户干预的场景中提交用户选择
    """
    central_agent = agents.get("central")
    if not central_agent:
        raise HTTPException(status_code=500, detail="中央代理未初始化")
    
    try:
        from models.mcp import create_command_message
        
        command_msg = create_command_message(
            source="api",
            target="central_agent",
            action="user_selection",
            parameters={
                "workflow_id": workflow_id,
                "selection_type": request.selection_type,
                "selection_value": request.selection_value
            }
        )
        
        await message_bus.publish(command_msg)
        
        response = await message_bus.wait_for_response(
            message_id=command_msg.header.message_id,
            timeout=5.0,
            expected_source="central_agent"
        )
        
        if response and response.body.success:
            return {
                "success": True,
                "data": response.body.data
            }
        else:
            error_msg = response.body.message if response else "请求超时"
            raise HTTPException(status_code=400, detail=error_msg)
            
    except Exception as e:
        logger.error(f"提交用户选择失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos")
async def list_workflows(status: Optional[str] = None, limit: int = 10):
    """
    列出工作流
    
    获取所有或筛选后的工作流列表
    """
    central_agent = agents.get("central")
    if not central_agent:
        raise HTTPException(status_code=500, detail="中央代理未初始化")
    
    workflows = central_agent.get_all_workflows()
    
    # 筛选状态
    if status:
        workflows = [w for w in workflows if w.status.value == status]
    
    # 排序和限制
    workflows = sorted(workflows, key=lambda w: w.created_at, reverse=True)[:limit]
    
    return {
        "success": True,
        "data": {
            "workflows": [w.to_dict() for w in workflows],
            "total": len(workflows)
        }
    }


@app.get("/api/models/video")
async def list_video_models():
    """列出可用的视频模型"""
    visual_agent = agents.get("visual")
    if not visual_agent:
        raise HTTPException(status_code=500, detail="视觉代理未初始化")
    
    return {
        "success": True,
        "data": visual_agent._video_models
    }


@app.get("/api/models/voice")
async def list_voice_models():
    """列出可用的语音模型"""
    audio_agent = agents.get("audio")
    if not audio_agent:
        raise HTTPException(status_code=500, detail="音频代理未初始化")
    
    return {
        "success": True,
        "data": {
            "models": audio_agent._voice_models,
            "presets": audio_agent._voice_presets
        }
    }


@app.get("/api/models/music")
async def list_music_models():
    """列出可用的音乐模型"""
    audio_agent = agents.get("audio")
    if not audio_agent:
        raise HTTPException(status_code=500, detail="音频代理未初始化")
    
    return {
        "success": True,
        "data": audio_agent._music_models
    }


@app.get("/api/platforms")
async def list_platforms():
    """列出支持的分发平台"""
    distribution_agent = agents.get("distribution")
    if not distribution_agent:
        raise HTTPException(status_code=500, detail="分发代理未初始化")
    
    return {
        "success": True,
        "data": distribution_agent._platforms
    }


@app.get("/api/styles")
async def list_styles():
    """列出支持的视频风格"""
    return {
        "success": True,
        "data": {
            "content_styles": config.workflow.supported_styles,
            "video_styles": ["realistic", "cinematic", "creative", "artistic", "anime"],
            "voice_styles": ["natural", "expressive", "professional"],
            "music_styles": ["upbeat", "calm", "emotional", "energetic", "ambient"]
        }
    }


@app.get("/api/stats")
async def get_system_stats():
    """获取系统统计信息"""
    agent_status = {}
    total_messages = 0
    
    for name, agent in agents.items():
        status = agent.get_status()
        agent_status[name] = status
        total_messages += status["messages_processed"]
    
    return {
        "success": True,
        "data": {
            "agents": agent_status,
            "message_bus": message_bus.get_metrics(),
            "storage": await file_manager.get_storage_stats(),
            "total_messages_processed": total_messages
        }
    }


def main():
    """主函数"""
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
        log_level="info"
    )


if __name__ == "__main__":
    main()
