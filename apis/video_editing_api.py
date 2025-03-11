from typing import Dict, Any, List, Optional
import requests
import warnings
from config.config import EDITING_CONFIG, API_KEYS

class VideoEditingAPI:
    """
    视频编辑API封装类
    
    @deprecated: 此API已被弃用，将在未来版本中移除。
    MCP agents现在使用其内部API实现。
    """
    
    def __init__(self, tool_name: str):
        """
        初始化视频编辑API客户端
        
        Args:
            tool_name: 使用的工具名称
        """
        warnings.warn(
            "VideoEditingAPI is deprecated and will be removed in a future version. "
            "MCP agents now use their own internal API implementations.",
            DeprecationWarning,
            stacklevel=2
        )
        self.tool_name = tool_name
        self.config = EDITING_CONFIG.get(tool_name, {})
        self.api_key = API_KEYS.get(f"{tool_name}_edit", "")
        
        if not self.config:
            raise ValueError(f"未找到工具 {tool_name} 的配置")
        if not self.api_key:
            raise ValueError(f"未找到工具 {tool_name} 的API密钥")
            
        self.base_url = self.config["base_url"]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def apply_effects(self, video_path: str, effects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        应用视频效果
        
        Args:
            video_path: 视频文件路径
            effects: 要应用的效果列表
            
        Returns:
            Dict[str, Any]: API响应
        """
        for effect in effects:
            if effect["type"] not in self.config["supported_effects"]:
                raise ValueError(f"不支持的效果类型: {effect['type']}")
                
        with open(video_path, 'rb') as f:
            files = {'video': f}
            data = {'effects': effects}
            
            response = requests.post(
                f"{self.base_url}/effects",
                headers=self.headers,
                files=files,
                data=data,
                timeout=self.config["timeout"]
            )
            
        response.raise_for_status()
        return response.json()
        
    def get_editing_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取视频编辑任务状态
        
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
        下载编辑后的视频
        
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