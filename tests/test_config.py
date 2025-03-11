"""
测试配置文件
包含测试环境中使用的配置参数和API密钥
"""

import os
from typing import Dict, Any

# 测试环境配置
TEST_CONFIG = {
    # 基础设置
    "test_mode": True,
    "mock_api_calls": True,  # 设置为True时使用模拟API调用
    "timeout": 30,           # API调用超时时间（秒）
    
    # 目录设置
    "output_dir": "output/test",
    "temp_dir": "temp/test",
    "assets_dir": "assets/test",
    
    # OpenAI配置
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY", "test_openai_key"),
        "model": "gpt-4",
        "use_mock": True,  # 测试时使用模拟响应
    },
    
    # Replicate配置（用于图像生成）
    "replicate": {
        "api_key": os.getenv("REPLICATE_API_KEY", "test_replicate_key"),
        "use_mock": True,
    },
    
    # 视频生成API配置
    "video_api": {
        "wan_ying": {
            "api_key": os.getenv("WANYING_API_KEY", "test_wanying_key"),
            "base_url": "https://api.example.com/wanying/",
            "use_mock": True,
        },
        "runway": {
            "api_key": os.getenv("RUNWAY_API_KEY", "test_runway_key"),
            "base_url": "https://api.example.com/runway/",
            "use_mock": True,
        },
        "pika": {
            "api_key": os.getenv("PIKA_API_KEY", "test_pika_key"),
            "base_url": "https://api.example.com/pika/",
            "use_mock": True,
        },
        "keling": {
            "api_key": os.getenv("KELING_API_KEY", "test_keling_key"),
            "base_url": "https://api.example.com/keling/",
            "use_mock": True,
        }
    }
}

# 测试用的OpenAI模拟响应
MOCK_OPENAI_RESPONSES = {
    "script_creation": {
        "success": True,
        "content": """
{
  "title": "人工智能改变生活的5种方式",
  "theme": "科技",
  "type": "短视频",
  "style": "informative",
  "keywords": ["AI", "智能家居", "自动化"],
  "sections": [
    {
      "order": 0,
      "content": "人工智能已经悄然改变了我们的日常生活。从智能手机到家庭助手，AI技术无处不在。",
      "visual_description": "展示一个人使用智能手机，周围悬浮着各种AI应用图标",
      "audio_description": "轻快的背景音乐，narrator清晰讲述AI的普及",
      "duration": 8.0
    },
    {
      "order": 1,
      "content": "智能家居系统让我们的居住环境更加便捷和舒适。可以通过语音控制灯光、温度和安保系统。",
      "visual_description": "展示智能家居场景，灯光自动调节，恒温器自动控制",
      "audio_description": "平静的背景音乐，narrator介绍智能家居功能",
      "duration": 10.0
    },
    {
      "order": 2,
      "content": "AI助手帮助我们管理日程、回答问题和执行任务，极大提高了工作效率。",
      "visual_description": "展示专业人士使用AI助手规划日程和回答问题",
      "audio_description": "轻快的背景音乐，穿插AI助手回应声音",
      "duration": 8.0
    },
    {
      "order": 3,
      "content": "机器学习算法分析我们的喜好，为我们推荐个性化的内容和产品。",
      "visual_description": "展示用户浏览个性化推荐内容，满意地点击和选择",
      "audio_description": "柔和的背景音乐，narrator解释个性化推荐的工作原理",
      "duration": 9.0
    },
    {
      "order": 4,
      "content": "人工智能在医疗领域的应用，帮助医生更快速、准确地诊断疾病。",
      "visual_description": "医生使用AI系统分析医疗图像和数据",
      "audio_description": "严肃而希望的背景音乐，narrator讲述AI在医疗领域的突破",
      "duration": 10.0
    }
  ]
}
"""
    },
    
    "storyboard_content": {
        "success": True,
        "content": """
{
  "raw_content": "# 分镜脚本：人工智能改变生活的5种方式\n\n## 场景1：引言\n**画面描述**：开场是一个年轻人拿着智能手机，周围有各种AI应用图标悬浮在空中，图标包括智能家居、个人助手、内容推荐等。\n**镜头**：中景，随后慢慢拉近至特写\n**时长**：8秒\n**转场**：溶解过渡\n\n## 场景2：智能家居\n**画面描述**：展示一个现代化的家庭环境，主人通过语音命令控制灯光、调节温度，安保系统自动运行。\n**镜头**：广角展示房间全景，随后切换到特写展示各设备的反应\n**时长**：10秒\n**转场**：滑动过渡\n\n## 场景3：AI助手提升效率\n**画面描述**：专业人士在办公环境中使用AI助手规划日程、回答问题、整理文档。\n**镜头**：从俯视角度展示办公桌和屏幕，随后切换到用户与AI交互的特写\n**时长**：8秒\n**转场**：快速切换\n\n## 场景4：个性化推荐\n**画面描述**：用户浏览内容时，屏幕上显示个性化推荐的内容，用户表现出满意和惊喜。\n**镜头**：特写用户脸部表情，随后切换到屏幕内容的特写\n**时长**：9秒\n**转场**：淡入淡出\n\n## 场景5：医疗AI\n**画面描述**：医生使用AI系统分析医疗图像，屏幕上显示AI辅助诊断的过程和结果。\n**镜头**：从侧面拍摄医生与显示屏的互动，随后特写屏幕上的分析结果\n**时长**：10秒\n**转场**：溶解结束",
  "frames": [
    {
      "order": 0,
      "shot_type": "MEDIUM",
      "frame_type": "SCENE",
      "content": "引言：人工智能已经悄然改变了我们的日常生活。从智能手机到家庭助手，AI技术无处不在。",
      "visual_description": "开场是一个年轻人拿着智能手机，周围有各种AI应用图标悬浮在空中，图标包括智能家居、个人助手、内容推荐等。",
      "transition": "DISSOLVE",
      "duration": 8.0
    },
    {
      "order": 1,
      "shot_type": "WIDE",
      "frame_type": "SCENE",
      "content": "智能家居系统让我们的居住环境更加便捷和舒适。可以通过语音控制灯光、温度和安保系统。",
      "visual_description": "展示一个现代化的家庭环境，主人通过语音命令控制灯光、调节温度，安保系统自动运行。",
      "transition": "SLIDE",
      "duration": 10.0
    },
    {
      "order": 2,
      "shot_type": "OVERHEAD",
      "frame_type": "SCENE",
      "content": "AI助手帮助我们管理日程、回答问题和执行任务，极大提高了工作效率。",
      "visual_description": "专业人士在办公环境中使用AI助手规划日程、回答问题、整理文档。",
      "transition": "CUT",
      "duration": 8.0
    },
    {
      "order": 3,
      "shot_type": "CLOSEUP",
      "frame_type": "SCENE",
      "content": "机器学习算法分析我们的喜好，为我们推荐个性化的内容和产品。",
      "visual_description": "用户浏览内容时，屏幕上显示个性化推荐的内容，用户表现出满意和惊喜。",
      "transition": "FADE",
      "duration": 9.0
    },
    {
      "order": 4,
      "shot_type": "SIDE",
      "frame_type": "SCENE",
      "content": "人工智能在医疗领域的应用，帮助医生更快速、准确地诊断疾病。",
      "visual_description": "医生使用AI系统分析医疗图像，屏幕上显示AI辅助诊断的过程和结果。",
      "transition": "DISSOLVE",
      "duration": 10.0
    }
  ]
}
"""
    }
}

# 测试用的视频API模拟响应
MOCK_VIDEO_API_RESPONSES = {
    "generate_video": {
        "success": True,
        "data": {
            "task_id": "mock_task_12345",
            "status": "processing",
            "estimated_time": 60
        }
    },
    "check_status": {
        "success": True,
        "data": {
            "task_id": "mock_task_12345",
            "status": "completed",
            "video_url": "https://example.com/mock_video.mp4"
        }
    }
}

# 测试用的图像API模拟响应
MOCK_IMAGE_API_RESPONSES = {
    "generate_image": {
        "success": True,
        "data": {
            "task_id": "mock_image_task_12345",
            "status": "completed",
            "image_url": "https://example.com/mock_image.jpg",
            "width": 1024,
            "height": 1024
        }
    }
} 