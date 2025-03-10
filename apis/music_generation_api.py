from typing import Dict, Any, Optional
import requests
from config.config import AUDIO_CONFIG, API_KEYS

class MusicGenerationAPI:
    """音乐生成API封装类"""
    
    def __init__(self, tool_name: str):
        """
        初始化音乐生成API客户端
        
        Args:
            tool_name: 使用的工具名称
        """
        self.tool_name = tool_name
        self.config = AUDIO_CONFIG.get(tool_name, {})
        self.api_key = API_KEYS.get(tool_name, "")
        
        if not self.config:
            raise ValueError(f"未找到工具 {tool_name} 的配置")
        if not self.api_key:
            raise ValueError(f"未找到工具 {tool_name} 的API密钥")
            
        self.base_url = self.config["base_url"]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def generate_music(self, prompt: str, duration: int,
                      style: Optional[str] = None,
                      tempo: Optional[str] = None,
                      intensity: Optional[float] = None) -> Dict[str, Any]:
        """
        生成音乐
        
        Args:
            prompt: 音乐生成提示词
            duration: 音乐时长（秒）
            style: 音乐风格
            tempo: 节奏
            intensity: 强度
            
        Returns:
            Dict[str, Any]: API响应
        """
        if style and style not in self.config["styles"]:
            raise ValueError(f"不支持的音乐风格: {style}")
            
        data = {
            "prompt": prompt,
            "duration": duration,
            "style": style,
            "tempo": tempo or self.config["tempo"],
            "intensity": intensity or self.config["intensity"]
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
        获取音乐生成任务状态
        
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
        
    def download_music(self, music_url: str, save_path: str) -> None:
        """
        下载生成的音乐
        
        Args:
            music_url: 音乐URL
            save_path: 保存路径
        """
        response = requests.get(
            music_url,
            headers=self.headers,
            stream=True,
            timeout=self.config["timeout"]
        )
        
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk) 