from typing import Dict, Any, Optional
import requests
from config.config import AUDIO_CONFIG, API_KEYS

class VoiceSynthesisAPI:
    """语音合成API封装类"""
    
    def __init__(self, tool_name: str):
        """
        初始化语音合成API客户端
        
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
        
    def synthesize_speech(self, text: str, voice_id: str, language: str = "zh",
                         speed: Optional[float] = None,
                         pitch: Optional[int] = None,
                         volume: Optional[float] = None) -> Dict[str, Any]:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            voice_id: 声音ID
            language: 语言代码
            speed: 语速
            pitch: 音调
            volume: 音量
            
        Returns:
            Dict[str, Any]: API响应
        """
        if voice_id not in self.config["voices"].get(language, []):
            raise ValueError(f"不支持的声音ID: {voice_id}")
            
        data = {
            "text": text,
            "voice_id": voice_id,
            "language": language,
            "speed": speed or self.config["speed"],
            "pitch": pitch or self.config["pitch"],
            "volume": volume or self.config["volume"]
        }
        
        response = requests.post(
            f"{self.base_url}/synthesize",
            headers=self.headers,
            json=data,
            timeout=self.config["timeout"]
        )
        
        response.raise_for_status()
        return response.json()
        
    def get_synthesis_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取语音合成任务状态
        
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
        
    def download_audio(self, audio_url: str, save_path: str) -> None:
        """
        下载合成的音频
        
        Args:
            audio_url: 音频URL
            save_path: 保存路径
        """
        response = requests.get(
            audio_url,
            headers=self.headers,
            stream=True,
            timeout=self.config["timeout"]
        )
        
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk) 