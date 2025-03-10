import json
import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiofiles
from abc import ABC, abstractmethod

from models.mcp import MCPMessage, MCPPriority


class MCPMessagePersistence(ABC):
    """MCP消息持久化抽象接口"""
    
    @abstractmethod
    async def save_message(self, message: MCPMessage) -> bool:
        """保存消息到持久化存储"""
        pass
    
    @abstractmethod
    async def load_message(self, message_id: str) -> Optional[MCPMessage]:
        """从持久化存储加载消息"""
        pass
    
    @abstractmethod
    async def delete_message(self, message_id: str) -> bool:
        """从持久化存储删除消息"""
        pass
    
    @abstractmethod
    async def list_messages(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[str]:
        """列出符合条件的消息ID"""
        pass
    
    @abstractmethod
    async def mark_as_processed(self, message_id: str) -> bool:
        """标记消息为已处理"""
        pass


class FileSystemMessagePersistence(MCPMessagePersistence):
    """基于文件系统的消息持久化实现"""
    
    def __init__(self, storage_dir: str = "data/messages"):
        self.storage_dir = storage_dir
        self.logger = logging.getLogger("FileSystemMessagePersistence")
        
        # 确保存储目录存在
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(f"{storage_dir}/pending", exist_ok=True)
        os.makedirs(f"{storage_dir}/processed", exist_ok=True)
        
        # 写入锁，防止并发写入冲突
        self._write_locks: Dict[str, asyncio.Lock] = {}
    
    def _get_write_lock(self, message_id: str) -> asyncio.Lock:
        """获取消息的写入锁"""
        if message_id not in self._write_locks:
            self._write_locks[message_id] = asyncio.Lock()
        return self._write_locks[message_id]
    
    def _get_message_path(self, message_id: str, is_processed: bool = False) -> str:
        """获取消息文件路径"""
        subdir = "processed" if is_processed else "pending"
        return f"{self.storage_dir}/{subdir}/{message_id}.json"
    
    async def save_message(self, message: MCPMessage) -> bool:
        """保存消息到文件系统"""
        message_id = message.header.message_id
        
        # 获取写入锁
        async with self._get_write_lock(message_id):
            try:
                # 将消息转换为JSON
                message_json = message.json()
                
                # 写入文件
                async with aiofiles.open(self._get_message_path(message_id), 'w') as f:
                    await f.write(message_json)
                
                self.logger.debug(f"Message {message_id} saved to persistent storage")
                return True
            except Exception as e:
                self.logger.error(f"Failed to save message {message_id}: {str(e)}")
                return False
    
    async def load_message(self, message_id: str) -> Optional[MCPMessage]:
        """从文件系统加载消息"""
        # 首先检查pending目录
        message_path = self._get_message_path(message_id)
        
        if not os.path.exists(message_path):
            # 如果不在pending目录，检查processed目录
            message_path = self._get_message_path(message_id, is_processed=True)
            
            if not os.path.exists(message_path):
                self.logger.warning(f"Message {message_id} not found in persistent storage")
                return None
        
        try:
            async with aiofiles.open(message_path, 'r') as f:
                message_json = await f.read()
            
            # 将JSON转换回消息对象
            message = MCPMessage.parse_raw(message_json)
            return message
        except Exception as e:
            self.logger.error(f"Failed to load message {message_id}: {str(e)}")
            return None
    
    async def delete_message(self, message_id: str) -> bool:
        """从文件系统删除消息"""
        # 获取写入锁
        async with self._get_write_lock(message_id):
            try:
                # 检查两个可能的位置
                pending_path = self._get_message_path(message_id)
                processed_path = self._get_message_path(message_id, is_processed=True)
                
                deleted = False
                
                if os.path.exists(pending_path):
                    os.remove(pending_path)
                    deleted = True
                
                if os.path.exists(processed_path):
                    os.remove(processed_path)
                    deleted = True
                
                if deleted:
                    self.logger.debug(f"Message {message_id} deleted from persistent storage")
                    # 清理锁
                    if message_id in self._write_locks:
                        del self._write_locks[message_id]
                    return True
                else:
                    self.logger.warning(f"Message {message_id} not found for deletion")
                    return False
            except Exception as e:
                self.logger.error(f"Failed to delete message {message_id}: {str(e)}")
                return False
    
    async def list_messages(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[str]:
        """列出符合条件的消息ID"""
        message_ids = []
        
        # 扫描pending目录
        for filename in os.listdir(f"{self.storage_dir}/pending"):
            if filename.endswith(".json"):
                message_id = filename[:-5]  # 去掉.json后缀
                
                # 如果有过滤条件，需要加载消息并检查
                if filter_criteria:
                    message = await self.load_message(message_id)
                    if message and self._matches_criteria(message, filter_criteria):
                        message_ids.append(message_id)
                else:
                    message_ids.append(message_id)
        
        # 如果需要，也扫描processed目录
        if filter_criteria and filter_criteria.get("include_processed", False):
            for filename in os.listdir(f"{self.storage_dir}/processed"):
                if filename.endswith(".json"):
                    message_id = filename[:-5]
                    message = await self.load_message(message_id)
                    if message and self._matches_criteria(message, filter_criteria):
                        message_ids.append(message_id)
        
        return message_ids
    
    def _matches_criteria(self, message: MCPMessage, criteria: Dict[str, Any]) -> bool:
        """检查消息是否符合过滤条件"""
        for key, value in criteria.items():
            if key == "include_processed":
                continue  # 这是一个特殊的控制标志，不是实际的过滤条件
                
            if key == "priority":
                if message.header.priority != value:
                    return False
            elif key == "message_type":
                if message.header.message_type != value:
                    return False
            elif key == "source":
                if message.header.source != value:
                    return False
            elif key == "target":
                if message.header.target != value:
                    return False
            elif key == "session_id":
                if message.header.session_id != value:
                    return False
            elif key == "before_timestamp":
                if message.header.timestamp >= value:
                    return False
            elif key == "after_timestamp":
                if message.header.timestamp <= value:
                    return False
        
        return True
    
    async def mark_as_processed(self, message_id: str) -> bool:
        """标记消息为已处理"""
        # 获取写入锁
        async with self._get_write_lock(message_id):
            try:
                # 加载消息
                message = await self.load_message(message_id)
                if not message:
                    return False
                
                # 源文件路径和目标文件路径
                source_path = self._get_message_path(message_id)
                target_path = self._get_message_path(message_id, is_processed=True)
                
                # 如果消息在pending目录中，移动到processed目录
                if os.path.exists(source_path):
                    # 读取消息内容
                    async with aiofiles.open(source_path, 'r') as f:
                        message_json = await f.read()
                    
                    # 写入到processed目录
                    async with aiofiles.open(target_path, 'w') as f:
                        await f.write(message_json)
                    
                    # 删除原文件
                    os.remove(source_path)
                    
                    self.logger.debug(f"Message {message_id} marked as processed")
                    return True
                else:
                    # 消息可能已经在processed目录或不存在
                    return os.path.exists(target_path)
            except Exception as e:
                self.logger.error(f"Failed to mark message {message_id} as processed: {str(e)}")
                return False


# 创建默认的持久化实例
default_persistence = FileSystemMessagePersistence() 