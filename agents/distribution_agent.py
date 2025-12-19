"""
分发代理
负责将视频发布到各个平台
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents.mcp_base_agent import MCPBaseAgent
from models.mcp import MCPCommand, MCPMessage


class DistributionAgent(MCPBaseAgent):
    """
    分发代理
    
    职责：
    1. 将视频发布到各个社交媒体平台
    2. 管理发布计划和定时发布
    3. 优化视频元数据（标题、标签等）
    4. 跟踪发布状态和分析数据
    """
    
    def __init__(self):
        super().__init__(agent_id="distribution_agent", agent_name="分发代理")
        
        # 命令处理器映射
        self._command_handlers = {
            "distribute_video": self._handle_distribute_video,
            "publish_to_platform": self._handle_publish_to_platform,
            "schedule_publish": self._handle_schedule_publish,
            "optimize_metadata": self._handle_optimize_metadata,
            "get_publish_status": self._handle_get_publish_status,
            "list_platforms": self._handle_list_platforms,
            "cancel_scheduled": self._handle_cancel_scheduled,
        }
        
        # 支持的平台
        self._platforms = {
            "tiktok": {
                "name": "TikTok",
                "description": "全球流行的短视频平台",
                "max_duration": 180,
                "supported_formats": ["mp4", "mov"],
                "aspect_ratios": ["9:16"],
                "max_file_size_mb": 287,
                "features": ["直接发布", "定时发布", "私密发布"]
            },
            "douyin": {
                "name": "抖音",
                "description": "国内领先的短视频平台",
                "max_duration": 180,
                "supported_formats": ["mp4", "mov"],
                "aspect_ratios": ["9:16"],
                "max_file_size_mb": 128,
                "features": ["直接发布", "定时发布", "合拍", "贴纸"]
            },
            "kuaishou": {
                "name": "快手",
                "description": "国内主流短视频平台",
                "max_duration": 180,
                "supported_formats": ["mp4"],
                "aspect_ratios": ["9:16", "16:9", "1:1"],
                "max_file_size_mb": 100,
                "features": ["直接发布", "定时发布"]
            },
            "youtube_shorts": {
                "name": "YouTube Shorts",
                "description": "YouTube 短视频",
                "max_duration": 60,
                "supported_formats": ["mp4", "mov", "webm"],
                "aspect_ratios": ["9:16"],
                "max_file_size_mb": 128,
                "features": ["直接发布", "定时发布", "货币化"]
            },
            "instagram_reels": {
                "name": "Instagram Reels",
                "description": "Instagram 短视频",
                "max_duration": 90,
                "supported_formats": ["mp4", "mov"],
                "aspect_ratios": ["9:16"],
                "max_file_size_mb": 100,
                "features": ["直接发布", "定时发布", "分享到故事"]
            },
            "bilibili": {
                "name": "哔哩哔哩",
                "description": "国内知名视频平台",
                "max_duration": 600,
                "supported_formats": ["mp4", "flv"],
                "aspect_ratios": ["16:9", "9:16", "1:1"],
                "max_file_size_mb": 8192,
                "features": ["直接发布", "定时发布", "分P", "互动视频"]
            },
        }
        
        # 发布记录
        self._publish_records: Dict[str, Dict[str, Any]] = {}
        
        # 定时发布任务
        self._scheduled_tasks: Dict[str, Dict[str, Any]] = {}
    
    async def handle_command(self, message: MCPMessage) -> Optional[MCPMessage]:
        """处理命令消息"""
        if not isinstance(message.body, MCPCommand):
            return message.create_error_response(
                error_code="INVALID_MESSAGE",
                error_message="预期收到命令消息"
            )
        
        command = message.body
        action = command.action
        
        self.logger.info(f"收到命令: {action}")
        
        handler = self._command_handlers.get(action)
        if not handler:
            return message.create_error_response(
                error_code="UNKNOWN_COMMAND",
                error_message=f"未知命令: {action}"
            )
        
        try:
            result = await handler(command.parameters, message.header.session_id)
            return message.create_response(
                success=True,
                message=f"命令 {action} 执行成功",
                data=result
            )
        except Exception as e:
            self.logger.error(f"执行命令 {action} 时发生错误: {str(e)}", exc_info=True)
            return message.create_error_response(
                error_code="EXECUTION_ERROR",
                error_message=f"执行命令时发生错误: {str(e)}"
            )
    
    async def _handle_distribute_video(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """分发视频到多个平台"""
        video = parameters.get("video")
        platforms = parameters.get("platforms", ["tiktok"])
        schedule = parameters.get("schedule")
        metadata = parameters.get("metadata", {})
        
        if not video:
            raise ValueError("缺少必要参数: video")
        
        self.logger.info(f"分发视频到平台: {platforms}")
        
        distribution_id = f"dist_{uuid.uuid4().hex[:8]}"
        results = {}
        
        for platform in platforms:
            if platform not in self._platforms:
                results[platform] = {
                    "status": "failed",
                    "error": f"不支持的平台: {platform}"
                }
                continue
            
            try:
                if schedule:
                    # 定时发布
                    result = await self._schedule_publish_to_platform(
                        video, platform, schedule, metadata, session_id
                    )
                else:
                    # 立即发布
                    result = await self._publish_to_platform(
                        video, platform, metadata, session_id
                    )
                results[platform] = result
            except Exception as e:
                results[platform] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        # 记录分发
        self._publish_records[distribution_id] = {
            "distribution_id": distribution_id,
            "session_id": session_id,
            "video": video,
            "platforms": platforms,
            "results": results,
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "distribution_id": distribution_id,
            "results": results,
            "success_count": sum(1 for r in results.values() if r.get("status") == "published"),
            "total_platforms": len(platforms)
        }
    
    async def _publish_to_platform(
        self,
        video: Dict[str, Any],
        platform: str,
        metadata: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """发布到单个平台"""
        platform_config = self._platforms.get(platform)
        
        # 验证视频兼容性
        self._validate_video_for_platform(video, platform_config)
        
        # 模拟发布延迟
        await asyncio.sleep(random.uniform(2, 5))
        
        publish_id = f"pub_{uuid.uuid4().hex[:8]}"
        
        # 模拟发布成功（实际会调用平台 API）
        return {
            "publish_id": publish_id,
            "platform": platform,
            "status": "published",
            "url": f"https://{platform}.com/video/{publish_id}",
            "video_id": video.get("video_id"),
            "title": metadata.get("title", ""),
            "published_at": datetime.now().isoformat()
        }
    
    async def _schedule_publish_to_platform(
        self,
        video: Dict[str, Any],
        platform: str,
        schedule: str,
        metadata: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """定时发布到平台"""
        schedule_id = f"sched_{uuid.uuid4().hex[:8]}"
        
        # 解析发布时间
        try:
            publish_time = datetime.fromisoformat(schedule)
        except ValueError:
            raise ValueError(f"无效的发布时间格式: {schedule}")
        
        # 创建定时任务
        self._scheduled_tasks[schedule_id] = {
            "schedule_id": schedule_id,
            "video": video,
            "platform": platform,
            "metadata": metadata,
            "session_id": session_id,
            "publish_time": publish_time.isoformat(),
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "schedule_id": schedule_id,
            "platform": platform,
            "status": "scheduled",
            "publish_time": publish_time.isoformat()
        }
    
    def _validate_video_for_platform(
        self,
        video: Dict[str, Any],
        platform_config: Dict[str, Any]
    ):
        """验证视频是否符合平台要求"""
        # 检查时长
        duration = video.get("duration", 0)
        max_duration = platform_config.get("max_duration", 180)
        if duration > max_duration:
            raise ValueError(f"视频时长超过平台限制: {duration}s > {max_duration}s")
        
        # 这里可以添加更多验证，如文件大小、格式等
    
    async def _handle_publish_to_platform(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """发布到单个平台"""
        video = parameters.get("video")
        platform = parameters.get("platform")
        metadata = parameters.get("metadata", {})
        
        if not video or not platform:
            raise ValueError("缺少必要参数: video 或 platform")
        
        if platform not in self._platforms:
            raise ValueError(f"不支持的平台: {platform}")
        
        return await self._publish_to_platform(video, platform, metadata, session_id)
    
    async def _handle_schedule_publish(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """安排定时发布"""
        video = parameters.get("video")
        platform = parameters.get("platform")
        schedule = parameters.get("schedule")
        metadata = parameters.get("metadata", {})
        
        if not all([video, platform, schedule]):
            raise ValueError("缺少必要参数")
        
        if platform not in self._platforms:
            raise ValueError(f"不支持的平台: {platform}")
        
        return await self._schedule_publish_to_platform(
            video, platform, schedule, metadata, session_id
        )
    
    async def _handle_optimize_metadata(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """优化视频元数据"""
        video = parameters.get("video")
        platform = parameters.get("platform", "tiktok")
        script = parameters.get("script", {})
        
        if not video:
            raise ValueError("缺少必要参数: video")
        
        # 模拟处理延迟
        await asyncio.sleep(random.uniform(0.5, 1))
        
        # 生成优化后的元数据
        theme = script.get("metadata", {}).get("theme", "")
        style = script.get("metadata", {}).get("style", "")
        
        # 根据平台生成优化的标题
        titles = {
            "tiktok": f"🔥 {theme}必看！#{style}",
            "douyin": f"【{theme}】这个必须知道！",
            "youtube_shorts": f"{theme} - You Need to Know This!",
            "instagram_reels": f"✨ {theme} | #{style}",
            "bilibili": f"【{style}】关于{theme}的一切",
        }
        
        title = titles.get(platform, f"{theme} | {style}")
        
        # 生成标签
        base_tags = script.get("ending", {}).get("hashtags", [])
        platform_tags = {
            "tiktok": ["#fyp", "#foryou", "#viral"],
            "douyin": ["#上热门", "#推荐", "#必看"],
            "youtube_shorts": ["#Shorts", "#Viral", "#Trending"],
            "instagram_reels": ["#Reels", "#Explore", "#Trending"],
            "bilibili": ["#必剪创作", "#知识分享", "#干货"],
        }
        
        tags = base_tags + platform_tags.get(platform, [])
        
        return {
            "title": title,
            "description": f"关于{theme}的精彩内容，{style}风格呈现！",
            "tags": tags,
            "platform": platform,
            "optimized_at": datetime.now().isoformat()
        }
    
    async def _handle_get_publish_status(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """获取发布状态"""
        publish_id = parameters.get("publish_id")
        distribution_id = parameters.get("distribution_id")
        
        if publish_id:
            # 查找单个发布记录
            for record in self._publish_records.values():
                for platform, result in record.get("results", {}).items():
                    if result.get("publish_id") == publish_id:
                        return result
            raise ValueError(f"发布记录不存在: {publish_id}")
        
        if distribution_id:
            # 查找分发记录
            if distribution_id in self._publish_records:
                return self._publish_records[distribution_id]
            raise ValueError(f"分发记录不存在: {distribution_id}")
        
        raise ValueError("需要提供 publish_id 或 distribution_id")
    
    async def _handle_list_platforms(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """列出支持的平台"""
        return {
            "platforms": self._platforms
        }
    
    async def _handle_cancel_scheduled(
        self,
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """取消定时发布"""
        schedule_id = parameters.get("schedule_id")
        
        if not schedule_id:
            raise ValueError("缺少必要参数: schedule_id")
        
        if schedule_id not in self._scheduled_tasks:
            raise ValueError(f"定时任务不存在: {schedule_id}")
        
        task = self._scheduled_tasks[schedule_id]
        if task["status"] != "scheduled":
            raise ValueError(f"任务状态不允许取消: {task['status']}")
        
        task["status"] = "cancelled"
        task["cancelled_at"] = datetime.now().isoformat()
        
        return {
            "schedule_id": schedule_id,
            "status": "cancelled"
        }
