import asyncio
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Any, Optional

from models.message import AgentType
from models.user import VideoCreationRequest
from agents.central_agent import CentralAgent
from agents.content_agent import ContentAgent
from agents.visual_agent import VisualAgent
from agents.audio_agent import AudioAgent
from agents.postprod_agent import PostProdAgent
from agents.distribution_agent import DistributionAgent
from utils.logger import system_logger
from utils.file_manager import file_manager

# 创建FastAPI应用
app = FastAPI(
    title="TikTok风格短视频多代理协作生成系统",
    description="通过多代理协作生成高质量的TikTok风格短视频",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建代理实例
central_agent = CentralAgent()
content_agent = ContentAgent()
visual_agent = VisualAgent()
audio_agent = AudioAgent()
postprod_agent = PostProdAgent()
distribution_agent = DistributionAgent()

# 代理映射
agents = {
    AgentType.CENTRAL: central_agent,
    AgentType.CONTENT: content_agent,
    AgentType.VISUAL: visual_agent,
    AgentType.AUDIO: audio_agent,
    AgentType.POSTPROD: postprod_agent,
    AgentType.DISTRIBUTION: distribution_agent
}

# 确保目录存在
os.makedirs("temp", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 挂载静态文件目录
app.mount("/output", StaticFiles(directory="output"), name="output")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化所有代理"""
    system_logger.info("Starting TikTok-style video generation system")
    
    # 初始化所有代理
    for agent_type, agent in agents.items():
        await agent.initialize()
        system_logger.info(f"Initialized {agent_type.value} agent")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时关闭所有代理"""
    system_logger.info("Shutting down TikTok-style video generation system")
    
    # 关闭所有代理
    for agent_type, agent in agents.items():
        await agent.shutdown()
        system_logger.info(f"Shut down {agent_type.value} agent")


@app.post("/api/videos/create")
async def create_video(request: VideoCreationRequest, background_tasks: BackgroundTasks):
    """创建新视频"""
    try:
        # 使用临时用户ID（实际项目中应该从认证中获取）
        user_id = "user_temp"
        
        # 调用中央代理创建会话
        session_id = await central_agent.create_session(user_id, request)
        
        return {
            "success": True,
            "message": "Video creation process started",
            "session_id": session_id
        }
    except Exception as e:
        system_logger.error(f"Error creating video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/status/{session_id}")
async def get_video_status(session_id: str):
    """获取视频创建状态"""
    try:
        # 检查会话是否存在
        if session_id not in central_agent.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # 获取会话状态
        workflow = central_agent.active_sessions[session_id]
        
        return {
            "success": True,
            "session_id": session_id,
            "status": workflow.current_stage,
            "started_at": workflow.started_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"Error getting video status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/videos/user-response/{session_id}")
async def submit_user_response(session_id: str, response: Dict[str, Any]):
    """提交用户响应"""
    try:
        # 检查会话是否存在
        if session_id not in central_agent.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # 检查响应数据
        if "choice" not in response:
            raise HTTPException(status_code=400, detail="Missing 'choice' in response")
            
        # 发送用户响应给中央代理
        message_id = await central_agent.send_message(
            to_agent=AgentType.CENTRAL,
            content={
                "action": "user_response",
                "session_id": session_id,
                "choice": response["choice"],
                "feedback": response.get("feedback")
            }
        )
        
        return {
            "success": True,
            "message": "User response submitted",
            "session_id": session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"Error submitting user response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/result/{session_id}")
async def get_video_result(session_id: str):
    """获取视频创建结果"""
    try:
        # 检查会话是否存在
        if session_id not in central_agent.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # 获取会话状态
        workflow = central_agent.active_sessions[session_id]
        
        # 检查是否已完成
        if workflow.current_stage != "completed":
            return {
                "success": True,
                "session_id": session_id,
                "status": workflow.current_stage,
                "message": "Video creation is still in progress"
            }
            
        # 获取最终视频
        final_video = workflow.created_assets.get("final_video")
        if not final_video:
            raise HTTPException(status_code=404, detail="Final video not found")
            
        return {
            "success": True,
            "session_id": session_id,
            "status": "completed",
            "video": {
                "id": final_video["id"],
                "title": final_video["title"],
                "file_path": final_video["file_path"],
                "url": f"/output/{session_id}/videos/{os.path.basename(final_video['file_path'])}",
                "thumbnail": final_video.get("thumbnail"),
                "duration": final_video["duration"],
                "created_at": final_video["created_at"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"Error getting video result: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/videos/{session_id}")
async def cancel_video_creation(session_id: str):
    """取消视频创建"""
    try:
        # 检查会话是否存在
        if session_id not in central_agent.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # 发送取消命令给中央代理
        message_id = await central_agent.send_message(
            to_agent=AgentType.CENTRAL,
            content={
                "action": "cancel_session",
                "session_id": session_id
            }
        )
        
        return {
            "success": True,
            "message": "Video creation cancelled",
            "session_id": session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"Error cancelling video creation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trending-topics")
async def get_trending_topics():
    """获取热门话题"""
    try:
        # 发送命令给分发代理
        message_id = await central_agent.send_message(
            to_agent=AgentType.DISTRIBUTION,
            content={
                "action": "get_trending_topics"
            }
        )
        
        # 等待响应
        response = await central_agent.wait_for_response(
            message_id=message_id,
            from_agent=AgentType.DISTRIBUTION
        )
        
        if not response or not response.content.get("success"):
            error_msg = "Failed to get trending topics" if not response else response.content.get("error", "Unknown error")
            raise HTTPException(status_code=500, detail=error_msg)
            
        trending_topics = response.content.get("data", {}).get("trending_topics", [])
        
        return {
            "success": True,
            "trending_topics": trending_topics
        }
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"Error getting trending topics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # 运行FastAPI应用
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 