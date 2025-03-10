from typing import Dict, Any, Optional
import requests
from config.config import MODEL_CONFIG, API_KEYS

class VideoGenerationAPI:
    """视频生成API封装类"""
    
    def __init__(self, model_name: str):
        """
        初始化视频生成API客户端
        
        Args:
            model_name: 使用的模型名称
        """
        self.model_name = model_name
        self.config = MODEL_CONFIG.get(model_name, {})
        self.api_key = API_KEYS.get(model_name, "")
        
        if not self.config:
            raise ValueError(f"未找到模型 {model_name} 的配置")
        if not self.api_key:
            raise ValueError(f"未找到模型 {model_name} 的API密钥")
            
        self.base_url = self.config["base_url"]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def generate_video(self, prompt: str, duration: int, resolution: str,
                      style: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        生成视频
        
        Args:
            prompt: 视频生成提示词
            duration: 视频时长（秒）
            resolution: 视频分辨率
            style: 视频风格
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: API响应
        """
        if duration > self.config["max_duration"]:
            raise ValueError(f"视频时长超过限制 ({self.config['max_duration']}秒)")
            
        if resolution not in self.config["supported_resolutions"]:
            raise ValueError(f"不支持的分辨率: {resolution}")
            
        if style and style not in self.config["supported_styles"]:
            raise ValueError(f"不支持的风格: {style}")
            
        data = {
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "style": style or self.config["default_style"],
            "fps": self.config["fps"],
            "temperature": kwargs.get("temperature", self.config["temperature"]),
            "top_p": kwargs.get("top_p", self.config["top_p"])
        }
        
        response = requests.post(
            f"{self.base_url}/generate",
            headers=self.headers,
            json=data,
            timeout=self.config["timeout"]
        )
        
        response.raise_for_status()
        return response.json()
        
    def get_generation_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取视频生成任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict[str, Any]: API响应
        """
        response = requests.get(
            f"{self.base_url}/status/{task_id}",
            headers=self.headers,
            timeout=self.config["timeout"]
        )
        
        response.raise_for_status()
        return response.json()
        
    def download_video(self, video_url: str, save_path: str) -> None:
        """
        下载生成的视频
        
        Args:
            video_url: 视频URL
            save_path: 保存路径
        """
        response = requests.get(
            video_url,
            headers=self.headers,
            stream=True,
            timeout=self.config["timeout"]
        )
        
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk) 