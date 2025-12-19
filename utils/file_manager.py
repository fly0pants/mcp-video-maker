"""
文件管理器
负责管理系统中的所有文件操作
"""

import asyncio
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles
import aiofiles.os


class FileManager:
    """文件管理器，负责管理系统中的所有文件操作"""
    
    def __init__(self, base_path: str = "./storage"):
        """初始化文件管理器"""
        self.base_path = Path(base_path)
        self.temp_path = self.base_path / "temp"
        self.output_path = self.base_path / "output"
        self.scripts_path = self.base_path / "scripts"
        self.assets_path = self.base_path / "assets"
        self.videos_path = self.base_path / "videos"
        self.audio_path = self.base_path / "audio"
        
        # 文件元数据存储
        self._metadata_file = self.base_path / "metadata.json"
        self._metadata: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """初始化文件管理器，创建必要的目录"""
        directories = [
            self.base_path,
            self.temp_path,
            self.output_path,
            self.scripts_path,
            self.assets_path,
            self.videos_path,
            self.audio_path,
        ]
        
        for directory in directories:
            await self._ensure_directory(directory)
        
        # 加载元数据
        await self._load_metadata()
    
    async def _ensure_directory(self, path: Path):
        """确保目录存在"""
        if not await aiofiles.os.path.exists(path):
            await asyncio.to_thread(os.makedirs, path, exist_ok=True)
    
    async def _load_metadata(self):
        """加载文件元数据"""
        if await aiofiles.os.path.exists(self._metadata_file):
            async with aiofiles.open(self._metadata_file, "r", encoding="utf-8") as f:
                content = await f.read()
                self._metadata = json.loads(content) if content else {}
        else:
            self._metadata = {}
    
    async def _save_metadata(self):
        """保存文件元数据"""
        async with aiofiles.open(self._metadata_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(self._metadata, indent=2, default=str))
    
    def _generate_file_id(self) -> str:
        """生成唯一文件ID"""
        return f"file_{uuid.uuid4().hex[:12]}"
    
    async def save_script(
        self,
        script_data: Dict[str, Any],
        session_id: str,
        script_id: Optional[str] = None
    ) -> str:
        """保存脚本数据"""
        script_id = script_id or self._generate_file_id()
        filename = f"{session_id}_{script_id}.json"
        filepath = self.scripts_path / filename
        
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(json.dumps(script_data, indent=2, ensure_ascii=False))
        
        # 更新元数据
        self._metadata[script_id] = {
            "type": "script",
            "session_id": session_id,
            "filepath": str(filepath),
            "created_at": datetime.now().isoformat(),
            "size": os.path.getsize(filepath)
        }
        await self._save_metadata()
        
        return script_id
    
    async def load_script(self, script_id: str) -> Optional[Dict[str, Any]]:
        """加载脚本数据"""
        if script_id in self._metadata:
            filepath = Path(self._metadata[script_id]["filepath"])
            if await aiofiles.os.path.exists(filepath):
                async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                    content = await f.read()
                    return json.loads(content)
        return None
    
    async def save_video(
        self,
        video_data: bytes,
        session_id: str,
        video_id: Optional[str] = None,
        format: str = "mp4"
    ) -> str:
        """保存视频文件"""
        video_id = video_id or self._generate_file_id()
        filename = f"{session_id}_{video_id}.{format}"
        filepath = self.videos_path / filename
        
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(video_data)
        
        # 更新元数据
        self._metadata[video_id] = {
            "type": "video",
            "session_id": session_id,
            "filepath": str(filepath),
            "format": format,
            "created_at": datetime.now().isoformat(),
            "size": len(video_data)
        }
        await self._save_metadata()
        
        return video_id
    
    async def save_audio(
        self,
        audio_data: bytes,
        session_id: str,
        audio_id: Optional[str] = None,
        format: str = "mp3"
    ) -> str:
        """保存音频文件"""
        audio_id = audio_id or self._generate_file_id()
        filename = f"{session_id}_{audio_id}.{format}"
        filepath = self.audio_path / filename
        
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(audio_data)
        
        # 更新元数据
        self._metadata[audio_id] = {
            "type": "audio",
            "session_id": session_id,
            "filepath": str(filepath),
            "format": format,
            "created_at": datetime.now().isoformat(),
            "size": len(audio_data)
        }
        await self._save_metadata()
        
        return audio_id
    
    async def save_temp_file(
        self,
        data: Union[bytes, str],
        filename: str,
        session_id: str
    ) -> str:
        """保存临时文件"""
        file_id = self._generate_file_id()
        temp_dir = self.temp_path / session_id
        await self._ensure_directory(temp_dir)
        
        filepath = temp_dir / f"{file_id}_{filename}"
        
        if isinstance(data, str):
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(data)
        else:
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(data)
        
        # 更新元数据
        self._metadata[file_id] = {
            "type": "temp",
            "session_id": session_id,
            "filepath": str(filepath),
            "filename": filename,
            "created_at": datetime.now().isoformat(),
            "size": os.path.getsize(filepath)
        }
        await self._save_metadata()
        
        return file_id
    
    async def get_file_path(self, file_id: str) -> Optional[str]:
        """获取文件路径"""
        if file_id in self._metadata:
            return self._metadata[file_id]["filepath"]
        return None
    
    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """获取文件元数据"""
        return self._metadata.get(file_id)
    
    async def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        if file_id in self._metadata:
            filepath = Path(self._metadata[file_id]["filepath"])
            if await aiofiles.os.path.exists(filepath):
                await aiofiles.os.remove(filepath)
            del self._metadata[file_id]
            await self._save_metadata()
            return True
        return False
    
    async def cleanup_session(self, session_id: str):
        """清理会话相关的所有临时文件"""
        files_to_delete = [
            file_id for file_id, meta in self._metadata.items()
            if meta.get("session_id") == session_id and meta.get("type") == "temp"
        ]
        
        for file_id in files_to_delete:
            await self.delete_file(file_id)
        
        # 清理会话临时目录
        session_temp_dir = self.temp_path / session_id
        if await aiofiles.os.path.exists(session_temp_dir):
            await asyncio.to_thread(shutil.rmtree, session_temp_dir)
    
    async def cleanup_old_files(self, days: int = 7):
        """清理过期的临时文件"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        files_to_delete = []
        for file_id, meta in self._metadata.items():
            if meta.get("type") == "temp":
                created_at = datetime.fromisoformat(meta["created_at"])
                if created_at < cutoff_time:
                    files_to_delete.append(file_id)
        
        for file_id in files_to_delete:
            await self.delete_file(file_id)
        
        return len(files_to_delete)
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        total_size = 0
        type_counts = {}
        
        for file_id, meta in self._metadata.items():
            size = meta.get("size", 0)
            file_type = meta.get("type", "unknown")
            
            total_size += size
            type_counts[file_type] = type_counts.get(file_type, 0) + 1
        
        return {
            "total_files": len(self._metadata),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "type_counts": type_counts
        }
    
    async def export_output(
        self,
        session_id: str,
        output_name: str,
        file_ids: List[str]
    ) -> str:
        """导出输出文件到指定目录"""
        output_dir = self.output_path / session_id / output_name
        await self._ensure_directory(output_dir)
        
        exported_files = []
        for file_id in file_ids:
            if file_id in self._metadata:
                src_path = Path(self._metadata[file_id]["filepath"])
                if await aiofiles.os.path.exists(src_path):
                    dst_path = output_dir / src_path.name
                    await asyncio.to_thread(shutil.copy2, src_path, dst_path)
                    exported_files.append(str(dst_path))
        
        return str(output_dir)


# 全局文件管理器实例
file_manager = FileManager()
