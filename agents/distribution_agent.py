import asyncio
import uuid
import json
import os
import random
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.message import Message, MessageType, AgentType
from agents.base_agent import BaseAgent
from utils.file_manager import file_manager
from utils.logger import system_logger
from utils.prompt_manager import get_prompt_manager
from config.config import SYSTEM_CONFIG, API_KEYS

# Initialize prompt manager
prompt_manager = get_prompt_manager()


class TikTokAPI:
    """TikTok API接口封装"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def upload_video(self, 
                         video_path: str, 
                         title: str, 
                         description: str,
                         tags: List[str] = None,
                         **kwargs) -> Dict[str, Any]:
        """
        上传视频到TikTok（模拟实现）
        
        Args:
            video_path: 视频文件路径
            title: 视频标题
            description: 视频描述
            tags: 标签列表
            
        Returns:
            上传结果
        """
        # 实际项目中，这里应该调用真实的TikTok API
        # 目前使用模拟实现
        
        # 模拟API调用延迟
        await asyncio.sleep(random.uniform(2.0, 5.0))
        
        # 模拟上传结果
        video_id = f"tiktok_{uuid.uuid4().hex[:8]}"
        
        return {
            "id": video_id,
            "url": f"https://www.tiktok.com/@ai_video_maker/video/{video_id}",
            "title": title,
            "description": description,
            "tags": tags or [],
            "upload_time": datetime.now().isoformat(),
            "status": "published"
        }
        
    async def get_analytics(self, video_id: str) -> Dict[str, Any]:
        """
        获取视频分析数据（模拟实现）
        
        Args:
            video_id: TikTok视频ID
            
        Returns:
            分析数据
        """
        # 实际项目中，这里应该调用真实的TikTok Analytics API
        # 目前使用模拟实现
        
        # 模拟API调用延迟
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # 模拟分析数据
        return {
            "video_id": video_id,
            "views": random.randint(1000, 100000),
            "likes": random.randint(100, 10000),
            "comments": random.randint(10, 1000),
            "shares": random.randint(5, 500),
            "completion_rate": random.uniform(0.4, 0.9),
            "audience_demographics": {
                "age_groups": {
                    "13-17": random.uniform(0.05, 0.2),
                    "18-24": random.uniform(0.2, 0.4),
                    "25-34": random.uniform(0.2, 0.4),
                    "35+": random.uniform(0.1, 0.3)
                },
                "gender": {
                    "male": random.uniform(0.3, 0.7),
                    "female": random.uniform(0.3, 0.7)
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    async def get_trending_topics(self) -> List[Dict[str, Any]]:
        """
        获取当前热门话题（模拟实现）
        
        Returns:
            热门话题列表
        """
        # 实际项目中，这里应该调用真实的TikTok Trending API
        # 目前使用模拟实现
        
        # 模拟API调用延迟
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # 模拟热门话题
        topics = [
            {"name": "挑战自我", "views": random.randint(1000000, 10000000), "videos": random.randint(1000, 10000)},
            {"name": "美食探店", "views": random.randint(1000000, 10000000), "videos": random.randint(1000, 10000)},
            {"name": "旅行日记", "views": random.randint(1000000, 10000000), "videos": random.randint(1000, 10000)},
            {"name": "生活小技巧", "views": random.randint(1000000, 10000000), "videos": random.randint(1000, 10000)},
            {"name": "搞笑瞬间", "views": random.randint(1000000, 10000000), "videos": random.randint(1000, 10000)}
        ]
        
        return topics


class DistributionAgent(BaseAgent):
    """
    分发代理 - 系统的"营销专家"，优化视频发布并分析表现
    
    职责:
    - 确保视频符合TikTok的内容政策和技术要求
    - 优化元数据（标题、标签、描述），提高视频曝光率
    - 根据受众分析数据安排最佳发布时间
    - 监控发布后表现并为未来优化提供反馈
    """
    
    def __init__(self):
        super().__init__(AgentType.DISTRIBUTION, "DistributionAgent")
        self.tiktok_api = None
        self.file_manager = file_manager
        self.prompt_manager = prompt_manager
        
    async def initialize(self):
        """初始化分发代理"""
        await super().initialize()
        
        # 初始化TikTok API
        tiktok_api_key = API_KEYS.get("tiktok", "")
        if tiktok_api_key:
            self.tiktok_api = TikTokAPI(tiktok_api_key)
            self.logger.info("TikTok API initialized")
        else:
            self.logger.warning("TikTok API key not found, distribution features will be limited")
            
        self.logger.info("Distribution Agent initialized and ready to distribute videos")
        
    async def handle_command(self, message: Message) -> Optional[Message]:
        """处理命令消息"""
        action = message.content.get("action")
        
        if action == "distribute_video":
            # 分发视频
            parameters = message.content.get("parameters", {})
            session_id = message.content.get("session_id")
            
            if not parameters:
                return self.create_error_response(message, "Missing distribution parameters")
                
            try:
                distribution_result = await self._distribute_video(parameters, session_id)
                
                return self.create_success_response(message, {
                    "distribution": distribution_result
                })
            except Exception as e:
                self.logger.error(f"Error distributing video: {str(e)}")
                return self.create_error_response(message, f"Error distributing video: {str(e)}")
                
        elif action == "get_analytics":
            # 获取分析数据
            video_id = message.content.get("video_id")
            
            if not video_id:
                return self.create_error_response(message, "Missing video_id for analytics")
                
            try:
                analytics = await self._get_analytics(video_id)
                
                return self.create_success_response(message, {
                    "analytics": analytics
                })
            except Exception as e:
                self.logger.error(f"Error getting analytics: {str(e)}")
                return self.create_error_response(message, f"Error getting analytics: {str(e)}")
                
        elif action == "get_trending_topics":
            # 获取热门话题
            try:
                trending_topics = await self._get_trending_topics()
                
                return self.create_success_response(message, {
                    "trending_topics": trending_topics
                })
            except Exception as e:
                self.logger.error(f"Error getting trending topics: {str(e)}")
                return self.create_error_response(message, f"Error getting trending topics: {str(e)}")
                
        elif action == "optimize_metadata":
            # 优化元数据
            parameters = message.content.get("parameters", {})
            
            if not parameters:
                return self.create_error_response(message, "Missing metadata parameters")
                
            try:
                optimized_metadata = await self._optimize_metadata(parameters)
                
                return self.create_success_response(message, {
                    "optimized_metadata": optimized_metadata
                })
            except Exception as e:
                self.logger.error(f"Error optimizing metadata: {str(e)}")
                return self.create_error_response(message, f"Error optimizing metadata: {str(e)}")
            
        elif action == "create_distribution_plan":
            # 创建分发计划
            parameters = message.content.get("parameters", {})
            session_id = message.content.get("session_id")
            
            if not parameters or "script" not in parameters or "video_edit" not in parameters:
                # For missing parameters, return an error response with success=False
                content = {
                    "success": False,
                    "error": "Missing required parameters for distribution plan"
                }
                return message_bus.create_message(
                    sender=self.agent_type,
                    receiver=message.sender,
                    content=content,
                    message_type=MessageType.RESPONSE,
                    parent_id=message.id
                )
                
            try:
                # 从参数中提取脚本和视频编辑对象
                from models.video import Script, VideoEdit
                script = Script(**parameters["script"])
                video_edit = VideoEdit(**parameters["video_edit"])
                
                # 生成分发计划
                distribution = await self._generate_distribution_plan(script, video_edit, parameters, session_id)
                
                # 保存分发计划
                file_path = await self.file_manager.save_json_file(
                    distribution.model_dump(), 
                    f"temp/{session_id}/distribution/distribution_plan.json"
                )
                
                return self.create_success_response(message, {
                    "distribution": distribution.model_dump(),
                    "file_path": file_path
                })
            except Exception as e:
                self.logger.error(f"Error creating distribution plan: {str(e)}")
                return self.create_error_response(message, f"Error creating distribution plan: {str(e)}")
                
        elif action == "revise_distribution_plan":
            # 修改分发计划
            parameters = message.content.get("parameters", {})
            session_id = message.content.get("session_id")
            
            if not parameters or "distribution" not in parameters or "feedback" not in parameters:
                # For missing parameters, return an error response with success=False
                content = {
                    "success": False,
                    "error": "Missing required parameters for revising distribution plan"
                }
                return message_bus.create_message(
                    sender=self.agent_type,
                    receiver=message.sender,
                    content=content,
                    message_type=MessageType.RESPONSE,
                    parent_id=message.id
                )
                
            try:
                # 从参数中提取分发计划和反馈
                from models.video import Distribution
                distribution = Distribution(**parameters["distribution"])
                feedback = parameters["feedback"]
                
                # 修改分发计划
                revised_distribution = await self._revise_distribution_plan(distribution, feedback, session_id)
                
                # 保存修改后的分发计划
                file_path = await self.file_manager.save_json_file(
                    revised_distribution.model_dump(), 
                    f"temp/{session_id}/distribution/revised_plan.json"
                )
                
                return self.create_success_response(message, {
                    "distribution": revised_distribution.model_dump(),
                    "file_path": file_path
                })
            except Exception as e:
                self.logger.error(f"Error revising distribution plan: {str(e)}")
                return self.create_error_response(message, f"Error revising distribution plan: {str(e)}")
        else:
            # For invalid actions, return an error response with success=False
            content = {
                "success": False,
                "error": f"Unsupported action: {action}"
            }
            return message_bus.create_message(
                sender=self.agent_type,
                receiver=message.sender,
                content=content,
                message_type=MessageType.RESPONSE,
                parent_id=message.id
            )
    
    async def _distribute_video(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        分发视频
        
        Args:
            parameters: 分发参数
            session_id: 会话ID
            
        Returns:
            分发结果
        """
        video_id = parameters.get("video_id")
        video_path = parameters.get("video_path")
        title = parameters.get("title", "AI生成的TikTok视频")
        description = parameters.get("description", "这是一个由AI生成的TikTok风格短视频")
        tags = parameters.get("tags", [])
        
        if not video_path:
            raise ValueError("Missing video_path")
            
        # 检查TikTok API是否可用
        if not self.tiktok_api:
            self.logger.warning("TikTok API not available, using mock distribution")
            
            # 模拟分发结果
            distribution_result = {
                "video_id": video_id,
                "platform": "tiktok",
                "url": f"https://www.tiktok.com/@ai_video_maker/video/mock_{uuid.uuid4().hex[:8]}",
                "status": "published",
                "publish_time": datetime.now().isoformat(),
                "metadata": {
                    "title": title,
                    "description": description,
                    "tags": tags
                }
            }
            
            self.logger.info(f"Mock distributed video {video_id} to TikTok")
            return distribution_result
            
        # 1. 优化元数据
        optimized_metadata = await self._optimize_metadata({
            "title": title,
            "description": description,
            "tags": tags
        })
        
        # 2. 上传视频到TikTok
        self.logger.info(f"Uploading video {video_id} to TikTok")
        
        upload_result = await self.tiktok_api.upload_video(
            video_path=video_path,
            title=optimized_metadata["title"],
            description=optimized_metadata["description"],
            tags=optimized_metadata["tags"]
        )
        
        # 3. 创建分发结果
        distribution_result = {
            "video_id": video_id,
            "platform": "tiktok",
            "tiktok_id": upload_result["id"],
            "url": upload_result["url"],
            "status": upload_result["status"],
            "publish_time": upload_result["upload_time"],
            "metadata": optimized_metadata,
            "session_id": session_id
        }
        
        self.logger.info(f"Distributed video {video_id} to TikTok: {upload_result['url']}")
        return distribution_result
    
    async def _get_analytics(self, video_id: str) -> Dict[str, Any]:
        """
        获取视频分析数据
        
        Args:
            video_id: TikTok视频ID
            
        Returns:
            分析数据
        """
        # 检查TikTok API是否可用
        if not self.tiktok_api:
            self.logger.warning("TikTok API not available, using mock analytics")
            
            # 模拟分析数据
            return {
                "video_id": video_id,
                "views": random.randint(1000, 100000),
                "likes": random.randint(100, 10000),
                "comments": random.randint(10, 1000),
                "shares": random.randint(5, 500),
                "completion_rate": random.uniform(0.4, 0.9),
                "timestamp": datetime.now().isoformat()
            }
            
        # 获取分析数据
        self.logger.info(f"Getting analytics for video {video_id}")
        analytics = await self.tiktok_api.get_analytics(video_id)
        
        return analytics
    
    async def _get_trending_topics(self) -> List[Dict[str, Any]]:
        """
        获取当前热门话题
        
        Returns:
            热门话题列表
        """
        # 检查TikTok API是否可用
        if not self.tiktok_api:
            self.logger.warning("TikTok API not available, using mock trending topics")
            
            # 模拟热门话题
            return [
                {"name": "挑战自我", "popularity": 0.95},
                {"name": "美食探店", "popularity": 0.92},
                {"name": "旅行日记", "popularity": 0.88},
                {"name": "生活小技巧", "popularity": 0.85},
                {"name": "搞笑瞬间", "popularity": 0.82}
            ]
            
        # 获取热门话题
        self.logger.info("Getting trending topics from TikTok")
        trending_topics = await self.tiktok_api.get_trending_topics()
        
        # 处理结果
        processed_topics = []
        for topic in trending_topics:
            processed_topics.append({
                "name": topic["name"],
                "popularity": topic["views"] / 10000000  # 归一化为0-1的分数
            })
            
        return processed_topics
    
    async def _generate_distribution_plan(self, script, video_edit, parameters, session_id) -> 'Distribution':
        """
        生成分发计划
        
        Args:
            script: 视频脚本对象
            video_edit: 视频编辑对象
            parameters: 附加参数
            session_id: 会话ID
            
        Returns:
            分发计划对象
        """
        from models.video import Distribution, Platform, PublishSchedule, DistributionMetadata
        import openai
        import datetime
        import json
        
        # 使用LLM为视频内容生成最佳分发计划
        system_role = self.prompt_manager.get_system_role("distribution")
        
        # 准备提示文本
        prompt = self.prompt_manager.render_template(
            "generate_distribution_plan",
            {
                "title": video_edit.title,
                "description": video_edit.description,
                "duration": video_edit.duration,
                "script_content": "\n".join([section.content for section in script.sections]),
                "script_type": script.type.value,
                "locale": parameters.get("locale", "zh-CN")
            }
        )
        
        # 使用 OpenAI API 生成分发计划
        try:
            # 如果有配置OpenAI客户端则使用，否则模拟响应
            if hasattr(self, 'openai_client') and self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": system_role},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                # 解析响应
                result = json.loads(response.choices[0].message.content)
            else:
                # 模拟OpenAI响应
                result = {
                    "platforms": [
                        {
                            "name": "douyin",
                            "title": f"【{video_edit.title}】热门创意",
                            "description": f"{video_edit.description}\n\n#短视频创作 #AI视频",
                            "tags": ["AI视频", "创意", "短视频"],
                            "schedule": {
                                "publish_time": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
                                "timezone": "Asia/Shanghai"
                            },
                            "metadata": {
                                "cover_image": "default_cover.jpg",
                                "category": "科技",
                                "visibility": "public",
                                "allow_comments": True
                            }
                        },
                        {
                            "name": "bilibili",
                            "title": f"{video_edit.title} - B站专享版",
                            "description": f"{video_edit.description}\n\n欢迎点赞关注！",
                            "tags": ["AI", "科技", "创意视频"],
                            "schedule": {
                                "publish_time": (datetime.datetime.now() + datetime.timedelta(days=2)).isoformat(),
                                "timezone": "Asia/Shanghai"
                            },
                            "metadata": {
                                "cover_image": "bilibili_cover.jpg",
                                "category": "科技",
                                "visibility": "public",
                                "allow_comments": True
                            }
                        }
                    ]
                }
        except Exception as e:
            self.logger.error(f"Error generating distribution plan with OpenAI: {str(e)}")
            # 使用备用方案
            result = {
                "platforms": [
                    {
                        "name": "douyin",
                        "title": video_edit.title,
                        "description": video_edit.description,
                        "tags": ["AI视频"],
                        "schedule": {
                            "publish_time": datetime.datetime.now().isoformat(),
                            "timezone": "Asia/Shanghai"
                        },
                        "metadata": {
                            "cover_image": "default_cover.jpg",
                            "category": "科技",
                            "visibility": "public",
                            "allow_comments": True
                        }
                    }
                ]
            }
            
        # 创建Platform对象列表
        platforms = []
        for platform_data in result["platforms"]:
            # 创建PublishSchedule对象
            schedule = PublishSchedule(
                publish_time=platform_data.get("schedule", {}).get("publish_time", datetime.datetime.now().isoformat()),
                timezone=platform_data.get("schedule", {}).get("timezone", "Asia/Shanghai")
            )
            
            # 创建DistributionMetadata对象
            metadata = DistributionMetadata(
                cover_image=platform_data.get("metadata", {}).get("cover_image", "default_cover.jpg"),
                category=platform_data.get("metadata", {}).get("category", "科技"),
                visibility=platform_data.get("metadata", {}).get("visibility", "public"),
                allow_comments=platform_data.get("metadata", {}).get("allow_comments", True)
            )
            
            # 创建Platform对象
            platform = Platform(
                name=platform_data.get("name", ""),
                title=platform_data.get("title", ""),
                description=platform_data.get("description", ""),
                tags=platform_data.get("tags", []),
                schedule=schedule,
                metadata=metadata
            )
            
            platforms.append(platform)
            
        # 创建并返回Distribution对象
        distribution_id = f"dist_{uuid.uuid4().hex[:8]}"
        distribution = Distribution(
            id=distribution_id,
            final_video_id=parameters.get("final_video_id"),
            platforms=platforms
        )
        
        return distribution
    
    async def _revise_distribution_plan(self, distribution, feedback, session_id) -> 'Distribution':
        """
        根据反馈修改分发计划
        
        Args:
            distribution: 原分发计划对象
            feedback: 用户反馈
            session_id: 会话ID
            
        Returns:
            修改后的分发计划对象
        """
        from models.video import Distribution, Platform, PublishSchedule, DistributionMetadata
        import openai
        import json
        
        # 使用LLM根据反馈修改分发计划
        system_role = self.prompt_manager.get_system_role("distribution_revision")
        
        # 准备提示文本
        prompt = self.prompt_manager.render_template(
            "revise_distribution_plan", 
            {
                "distribution": distribution.dict(),
                "feedback": feedback
            }
        )
        
        # 根据反馈修改（示例实现）
        # 在实际项目中，这里会调用OpenAI API
        # 出于演示目的，我们直接进行一些简单的修改
        
        # 创建修改后的platforms列表
        revised_platforms = []
        
        for platform in distribution.platforms:
            # 根据反馈修改标题和描述
            if "标题" in feedback and "更吸引人" in feedback:
                if platform.name == "douyin":
                    platform.title = "记录温暖日常 | 生活中的小确幸"
                elif platform.name == "bilibili":
                    platform.title = "【温馨治愈】生活的日常记录与感悟"
                    
            if "描述" in feedback and "更吸引人" in feedback:
                if platform.name == "douyin":
                    platform.description = "一起来看看我的日常生活吧！\n\n#日常生活 #生活记录 #温暖日常"
                elif platform.name == "bilibili":
                    platform.description = "记录生活中的美好瞬间，分享温暖日常。喜欢的话请点赞关注哦！\n\n#生活记录 #日常vlog #治愈系"
                    
            if "标签" in feedback and "增加" in feedback:
                if platform.name == "douyin":
                    platform.tags = ["日常生活", "生活记录", "温暖日常", "vlog", "生活方式", "治愈系"]
                elif platform.name == "bilibili":
                    platform.tags = ["日常", "vlog", "生活记录", "治愈系", "日常生活", "生活方式"]
            
            # 创建修改后的platform对象
            revised_platforms.append(platform)
            
        # 创建并返回修改后的Distribution对象
        revised_distribution = Distribution(
            id=distribution.id,
            final_video_id=distribution.final_video_id,
            platforms=revised_platforms
        )
        
        return revised_distribution
        
    async def _optimize_metadata(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化视频元数据
        
        Args:
            parameters: 元数据参数
            
        Returns:
            优化后的元数据
        """
        title = parameters.get("title", "")
        description = parameters.get("description", "")
        tags = parameters.get("tags", [])
        
        # 实际项目中，这里应该使用NLP模型或TikTok API分析热门关键词
        # 目前使用简单的优化规则
        
        # 1. 优化标题（确保长度适中，包含关键词）
        if len(title) > 80:
            # 标题太长，截断
            title = title[:77] + "..."
        elif len(title) < 20:
            # 标题太短，添加热门词
            title = f"{title} #热门短视频"
            
        # 2. 优化描述（添加表情符号，确保包含关键词）
        if not any(emoji in description for emoji in ["😊", "👍", "🔥", "✨", "❤️"]):
            # 添加表情符号
            description = f"✨ {description} 🔥"
            
        # 3. 优化标签（确保包含热门标签）
        popular_tags = ["热门", "推荐", "TikTok", "短视频"]
        for tag in popular_tags:
            if tag not in tags:
                tags.append(tag)
                
        # 限制标签数量
        if len(tags) > 10:
            tags = tags[:10]
            
        # 返回优化后的元数据
        optimized_metadata = {
            "title": title,
            "description": description,
            "tags": tags
        }
        
        self.logger.info(f"Optimized metadata: {optimized_metadata}")
        return optimized_metadata 