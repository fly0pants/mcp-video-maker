import logging
import os
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler

# 创建日志目录
os.makedirs("logs", exist_ok=True)


class AgentLogger:
    """多代理系统的日志工具"""
    
    def __init__(self, 
                 agent_name: str, 
                 log_level: int = logging.INFO,
                 log_to_console: bool = True,
                 log_to_file: bool = True,
                 log_dir: str = "logs"):
        """
        初始化日志工具
        
        Args:
            agent_name: 代理名称
            log_level: 日志级别
            log_to_console: 是否输出到控制台
            log_to_file: 是否输出到文件
            log_dir: 日志文件目录
        """
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")
        self.logger.setLevel(log_level)
        
        # 配置日志格式
        formatter = logging.Formatter(
            '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 清除现有的处理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 添加控制台输出
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 添加文件输出
        if log_to_file:
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{agent_name}.log")
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, msg: str, **kwargs):
        """记录调试级别日志"""
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """记录信息级别日志"""
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """记录警告级别日志"""
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """记录错误级别日志"""
        self._log(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """记录严重错误级别日志"""
        self._log(logging.CRITICAL, msg, **kwargs)
    
    def _log(self, level: int, msg: str, **kwargs):
        """实际记录日志的方法"""
        # 添加时间和代理名称
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name,
            "message": msg
        }
        
        # 添加额外的参数
        if kwargs:
            log_data.update(kwargs)
        
        # 如果有extra参数，则提取
        extra = log_data.pop("extra", None) if "extra" in log_data else None
        
        # 转换为JSON字符串，便于日志解析
        if "data" in log_data and isinstance(log_data["data"], dict):
            try:
                log_data["data"] = json.dumps(log_data["data"], ensure_ascii=False)
            except (TypeError, ValueError):
                log_data["data"] = str(log_data["data"])
        
        # 格式化消息
        formatted_msg = f"{msg}"
        if kwargs:
            context_pairs = []
            for k, v in kwargs.items():
                if k != "extra":
                    if isinstance(v, dict):
                        try:
                            v = json.dumps(v, ensure_ascii=False)
                        except (TypeError, ValueError):
                            v = str(v)
                    context_pairs.append(f"{k}={v}")
            
            if context_pairs:
                context_str = ", ".join(context_pairs)
                formatted_msg = f"{formatted_msg} [{context_str}]"
        
        # 实际记录日志
        self.logger.log(level, formatted_msg, extra=extra)


class SystemLogger(AgentLogger):
    """系统级日志工具，扩展自AgentLogger"""
    
    def __init__(self, log_level: int = logging.INFO):
        """初始化系统日志工具"""
        super().__init__(
            agent_name="system",
            log_level=log_level,
            log_to_console=True,
            log_to_file=True
        )
    
    def log_api_call(self, 
                     service: str, 
                     endpoint: str, 
                     params: Optional[Dict[str, Any]] = None,
                     status_code: Optional[int] = None,
                     response: Optional[Any] = None,
                     error: Optional[str] = None):
        """记录API调用日志"""
        # 基本数据
        log_data = {
            "service": service,
            "endpoint": endpoint,
            "params": params,
            "status_code": status_code
        }
        
        # 成功or失败
        if error:
            log_data["error"] = error
            self.error(f"API call to {service}/{endpoint} failed", **log_data)
        else:
            # 裁剪过长的响应
            if response and isinstance(response, dict):
                # 创建一个简化版的响应，排除过大的字段
                simplified_response = {}
                for k, v in response.items():
                    if isinstance(v, (dict, list)):
                        simplified_response[k] = f"[{type(v).__name__} with {len(v)} items]"
                    elif isinstance(v, str) and len(v) > 100:
                        simplified_response[k] = f"{v[:100]}... (truncated)"
                    else:
                        simplified_response[k] = v
                        
                log_data["response"] = simplified_response
            
            self.info(f"API call to {service}/{endpoint} succeeded", **log_data)
    
    def log_workflow_event(self, 
                           event_type: str, 
                           session_id: str, 
                           stage: str, 
                           details: Optional[Dict[str, Any]] = None):
        """记录工作流事件"""
        log_data = {
            "event_type": event_type,
            "session_id": session_id,
            "stage": stage
        }
        
        if details:
            log_data["details"] = details
            
        self.info(f"Workflow event: {event_type} in stage {stage}", **log_data)


# 全局系统日志实例
system_logger = SystemLogger() 