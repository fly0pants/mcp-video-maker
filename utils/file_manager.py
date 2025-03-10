import os
import shutil
import uuid
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import aiofiles
import aiohttp
from utils.logger import system_logger as logger


class FileManager:
    """管理系统中的文件资源"""
    
    def __init__(self, 
                 temp_dir: str = "./temp",
                 output_dir: str = "./output",
                 asset_dir: str = "./assets"):
        """
        初始化文件管理器
        
        Args:
            temp_dir: 临时文件目录
            output_dir: 最终输出目录
            asset_dir: 静态资源目录
        """
        self.temp_dir = Path(temp_dir)
        self.output_dir = Path(output_dir)
        self.asset_dir = Path(asset_dir)
        
        # 确保目录存在
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.asset_dir.mkdir(exist_ok=True, parents=True)
        
        # 创建子目录
        for subdir in ["videos", "audios", "scripts", "thumbnails"]:
            (self.temp_dir / subdir).mkdir(exist_ok=True)
            (self.output_dir / subdir).mkdir(exist_ok=True)
            
        logger.info(f"File manager initialized with dirs: temp={temp_dir}, output={output_dir}, asset={asset_dir}")
        
    def get_session_dir(self, session_id: str) -> Tuple[Path, Path]:
        """获取指定会话的临时和输出目录"""
        session_temp_dir = self.temp_dir / session_id
        session_output_dir = self.output_dir / session_id
        
        # 确保目录存在
        session_temp_dir.mkdir(exist_ok=True, parents=True)
        session_output_dir.mkdir(exist_ok=True, parents=True)
        
        return session_temp_dir, session_output_dir
    
    async def save_text_file(self, 
                             content: str, 
                             filename: str, 
                             session_id: Optional[str] = None, 
                             is_temp: bool = True,
                             subdir: Optional[str] = None) -> str:
        """
        保存文本内容到文件
        
        Args:
            content: 文本内容
            filename: 文件名
            session_id: 会话ID
            is_temp: 是否为临时文件
            subdir: 子目录
            
        Returns:
            文件路径
        """
        # 确定基础目录
        base_dir = self.temp_dir if is_temp else self.output_dir
        
        # 添加会话ID和子目录（如果有）
        if session_id:
            base_dir = base_dir / session_id
            base_dir.mkdir(exist_ok=True, parents=True)
        
        if subdir:
            base_dir = base_dir / subdir
            base_dir.mkdir(exist_ok=True, parents=True)
        
        # 确保目录存在
        base_dir.mkdir(exist_ok=True, parents=True)
        
        # 添加时间戳到文件名，确保唯一性
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if "." in filename:
            name, ext = filename.rsplit(".", 1)
            full_filename = f"{name}_{timestamp}.{ext}"
        else:
            full_filename = f"{filename}_{timestamp}"
        
        # 完整路径
        file_path = base_dir / full_filename
        
        # 写入文件
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)
            
        logger.info(f"Saved text file: {file_path}")
        return str(file_path)
    
    async def save_json_file(self, 
                             data: Dict[str, Any], 
                             filename: str, 
                             session_id: Optional[str] = None,
                             is_temp: bool = True,
                             subdir: Optional[str] = None) -> str:
        """
        保存JSON数据到文件
        
        Args:
            data: JSON数据
            filename: 文件名
            session_id: 会话ID
            is_temp: 是否为临时文件
            subdir: 子目录
            
        Returns:
            文件路径
        """
        # 确保文件名有.json后缀
        if not filename.endswith(".json"):
            filename = f"{filename}.json"
            
        # 转换为JSON文本
        content = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 保存为文件
        return await self.save_text_file(
            content=content,
            filename=filename,
            session_id=session_id,
            is_temp=is_temp,
            subdir=subdir
        )
    
    async def download_file(self, 
                           url: str, 
                           filename: Optional[str] = None,
                           session_id: Optional[str] = None,
                           is_temp: bool = True,
                           subdir: Optional[str] = None) -> str:
        """
        下载文件
        
        Args:
            url: 文件URL
            filename: 指定的文件名（可选）
            session_id: 会话ID
            is_temp: 是否为临时文件
            subdir: 子目录
            
        Returns:
            文件路径
        """
        # 如果未指定文件名，从URL中提取
        if not filename:
            filename = url.split("/")[-1].split("?")[0]
            if not filename:
                filename = f"downloaded_{uuid.uuid4().hex[:8]}"
        
        # 确定基础目录
        base_dir = self.temp_dir if is_temp else self.output_dir
        
        # 添加会话ID和子目录（如果有）
        if session_id:
            base_dir = base_dir / session_id
        
        if subdir:
            base_dir = base_dir / subdir
        
        # 确保目录存在
        base_dir.mkdir(exist_ok=True, parents=True)
        
        # 添加时间戳到文件名，确保唯一性
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if "." in filename:
            name, ext = filename.rsplit(".", 1)
            full_filename = f"{name}_{timestamp}.{ext}"
        else:
            full_filename = f"{filename}_{timestamp}"
        
        # 完整路径
        file_path = base_dir / full_filename
        
        # 下载文件
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(content)
                        logger.info(f"Downloaded file: {url} -> {file_path}")
                        return str(file_path)
                    else:
                        error_msg = f"Failed to download file: {url}, status: {response.status}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error downloading file: {url}, error: {str(e)}")
            raise
    
    def get_file_list(self, 
                     session_id: Optional[str] = None,
                     is_temp: bool = True,
                     subdir: Optional[str] = None,
                     file_extensions: Optional[List[str]] = None) -> List[str]:
        """
        获取文件列表
        
        Args:
            session_id: 会话ID
            is_temp: 是否为临时文件
            subdir: 子目录
            file_extensions: 文件扩展名过滤列表
            
        Returns:
            文件路径列表
        """
        # 确定基础目录
        base_dir = self.temp_dir if is_temp else self.output_dir
        
        # 添加会话ID和子目录（如果有）
        if session_id:
            base_dir = base_dir / session_id
        
        if subdir:
            base_dir = base_dir / subdir
        
        # 确保目录存在
        if not base_dir.exists():
            return []
        
        # 获取文件列表
        files = []
        for item in base_dir.iterdir():
            if item.is_file():
                if file_extensions:
                    if any(str(item).lower().endswith(ext.lower()) for ext in file_extensions):
                        files.append(str(item))
                else:
                    files.append(str(item))
        
        return files
    
    def clean_temp_files(self, session_id: Optional[str] = None):
        """
        清理临时文件
        
        Args:
            session_id: 如果指定，只清理特定会话的临时文件
        """
        if session_id:
            session_temp_dir = self.temp_dir / session_id
            if session_temp_dir.exists():
                shutil.rmtree(str(session_temp_dir))
                logger.info(f"Cleaned temp files for session: {session_id}")
        else:
            # 只删除子目录内容，保留temp目录本身
            for item in self.temp_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(str(item))
            logger.info("Cleaned all temp files")
    
    def move_file(self, 
                 source_path: str, 
                 is_temp_source: bool = True,
                 is_temp_dest: bool = False,
                 dest_filename: Optional[str] = None,
                 session_id: Optional[str] = None,
                 subdir: Optional[str] = None) -> str:
        """
        移动文件
        
        Args:
            source_path: 源文件路径
            is_temp_source: 源文件是否为临时文件
            is_temp_dest: 目标文件是否为临时文件
            dest_filename: 目标文件名
            session_id: 会话ID
            subdir: 子目录
            
        Returns:
            目标文件路径
        """
        # 确定源文件路径
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # 确定目标目录
        base_dir = self.temp_dir if is_temp_dest else self.output_dir
        
        # 添加会话ID和子目录（如果有）
        if session_id:
            base_dir = base_dir / session_id
        
        if subdir:
            base_dir = base_dir / subdir
        
        # 确保目录存在
        base_dir.mkdir(exist_ok=True, parents=True)
        
        # 确定目标文件名
        if not dest_filename:
            dest_filename = source_path.name
        
        # 完整目标路径
        dest_path = base_dir / dest_filename
        
        # 移动文件
        shutil.copy2(str(source_path), str(dest_path))
        
        # 如果源文件是临时文件，则删除
        if is_temp_source and source_path.exists():
            source_path.unlink()
        
        logger.info(f"Moved file: {source_path} -> {dest_path}")
        return str(dest_path)


# 全局文件管理器实例
file_manager = FileManager() 