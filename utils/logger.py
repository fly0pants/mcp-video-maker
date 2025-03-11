import logging
import os
import sys
import json
import time
import uuid
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable
from logging.handlers import RotatingFileHandler
from functools import wraps

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
            '%(asctime)s [%(name)s] [%(levelname)s] [%(trace_id)s] %(message)s',
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
    
    def debug(self, msg: str, trace_id: str = None, **kwargs):
        """记录调试级别日志"""
        self._log(logging.DEBUG, msg, trace_id, **kwargs)
    
    def info(self, msg: str, trace_id: str = None, **kwargs):
        """记录信息级别日志"""
        self._log(logging.INFO, msg, trace_id, **kwargs)
    
    def warning(self, msg: str, trace_id: str = None, **kwargs):
        """记录警告级别日志"""
        self._log(logging.WARNING, msg, trace_id, **kwargs)
    
    def error(self, msg: str, trace_id: str = None, **kwargs):
        """记录错误级别日志"""
        self._log(logging.ERROR, msg, trace_id, **kwargs)
    
    def critical(self, msg: str, trace_id: str = None, **kwargs):
        """记录严重错误级别日志"""
        self._log(logging.CRITICAL, msg, trace_id, **kwargs)
    
    def exception(self, msg: str, trace_id: str = None, **kwargs):
        """记录异常堆栈信息"""
        exc_info = sys.exc_info()
        if exc_info[0] is not None:
            if 'exc_info' not in kwargs:
                kwargs['exc_info'] = True
            tb_str = ''.join(traceback.format_exception(*exc_info))
            kwargs['traceback'] = tb_str
        self._log(logging.ERROR, msg, trace_id, **kwargs)
    
    def _log(self, level: int, msg: str, trace_id: str = None, **kwargs):
        """实际记录日志的方法"""
        # 生成跟踪ID
        if trace_id is None:
            trace_id = str(uuid.uuid4())[:8]
        
        # 添加时间和代理名称
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name,
            "trace_id": trace_id,
            "message": msg
        }
        
        # 添加额外的参数
        if kwargs:
            log_data.update(kwargs)
        
        # 如果有extra参数，则提取
        extra = log_data.pop("extra", {}) if "extra" in log_data else {}
        extra["trace_id"] = trace_id
        
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
                if k not in ["extra", "exc_info", "trace_id"]:
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

    def timed(self, message: str = None):
        """
        装饰器: 记录函数执行时间
        用法:
            @logger.timed("执行XX任务")
            async def my_function():
                pass
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                trace_id = kwargs.pop('trace_id', str(uuid.uuid4())[:8])
                start_time = time.time()
                func_name = func.__name__
                log_msg = message or f"开始执行函数 {func_name}"
                self.debug(f"{log_msg} - 开始", trace_id=trace_id)
                
                try:
                    result = await func(*args, **kwargs)
                    end_time = time.time()
                    duration = end_time - start_time
                    self.debug(
                        f"{log_msg} - 完成",
                        trace_id=trace_id,
                        duration=f"{duration:.3f}s"
                    )
                    return result
                except Exception as e:
                    end_time = time.time()
                    duration = end_time - start_time
                    self.exception(
                        f"{log_msg} - 失败: {str(e)}",
                        trace_id=trace_id,
                        duration=f"{duration:.3f}s",
                    )
                    raise
                    
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                trace_id = kwargs.pop('trace_id', str(uuid.uuid4())[:8])
                start_time = time.time()
                func_name = func.__name__
                log_msg = message or f"开始执行函数 {func_name}"
                self.debug(f"{log_msg} - 开始", trace_id=trace_id)
                
                try:
                    result = func(*args, **kwargs)
                    end_time = time.time()
                    duration = end_time - start_time
                    self.debug(
                        f"{log_msg} - 完成",
                        trace_id=trace_id,
                        duration=f"{duration:.3f}s"
                    )
                    return result
                except Exception as e:
                    end_time = time.time()
                    duration = end_time - start_time
                    self.exception(
                        f"{log_msg} - 失败: {str(e)}",
                        trace_id=trace_id,
                        duration=f"{duration:.3f}s",
                    )
                    raise
            
            return async_wrapper if asyncio_is_available and asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator


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
                     error: Optional[str] = None,
                     trace_id: Optional[str] = None,
                     duration: Optional[float] = None):
        """记录API调用日志"""
        # 基本数据
        log_data = {
            "service": service,
            "endpoint": endpoint,
            "params": params,
            "status_code": status_code
        }
        
        if duration is not None:
            log_data["duration"] = f"{duration:.3f}s"
        
        # 成功or失败
        if error:
            log_data["error"] = error
            self.error(f"API call to {service}/{endpoint} failed", trace_id=trace_id, **log_data)
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
            
            self.info(f"API call to {service}/{endpoint} succeeded", trace_id=trace_id, **log_data)
    
    def log_workflow_event(self, 
                           event_type: str, 
                           session_id: str, 
                           stage: str, 
                           details: Optional[Dict[str, Any]] = None,
                           trace_id: Optional[str] = None):
        """记录工作流事件"""
        log_data = {
            "event_type": event_type,
            "session_id": session_id,
            "stage": stage
        }
        
        if details:
            log_data["details"] = details
            
        self.info(f"Workflow event: {event_type} in stage {stage}", trace_id=trace_id, **log_data)
        
    def log_agent_interaction(self,
                             source_agent: str,
                             target_agent: str,
                             interaction_type: str,
                             message_id: str,
                             session_id: str,
                             data: Optional[Dict[str, Any]] = None,
                             status: str = "sent",
                             trace_id: Optional[str] = None):
        """记录代理之间的交互信息"""
        log_data = {
            "source": source_agent,
            "target": target_agent,
            "interaction_type": interaction_type,
            "message_id": message_id,
            "session_id": session_id,
            "status": status
        }
        
        if data:
            log_data["data_summary"] = self._summarize_data(data)
            
        self.info(f"Agent interaction: {source_agent} -> {target_agent} ({interaction_type})", 
                 trace_id=trace_id, **log_data)
    
    def _summarize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """简化数据以便记录"""
        if not isinstance(data, dict):
            return {"value": str(data)[:100] + "..." if isinstance(data, str) and len(str(data)) > 100 else str(data)}
            
        result = {}
        for k, v in data.items():
            if isinstance(v, dict):
                result[k] = f"[dict with {len(v)} keys]"
            elif isinstance(v, list):
                result[k] = f"[list with {len(v)} items]"
            elif isinstance(v, str) and len(v) > 100:
                result[k] = v[:100] + "..."
            else:
                result[k] = v
        return result
    
    def log_performance_metric(self, 
                              metric_name: str, 
                              value: Any,
                              unit: str = "",
                              component: str = "",
                              session_id: Optional[str] = None,
                              trace_id: Optional[str] = None,
                              **extra_dimensions):
        """记录性能指标"""
        log_data = {
            "metric": metric_name,
            "value": value,
            "component": component or "system"
        }
        
        if unit:
            log_data["unit"] = unit
            
        if session_id:
            log_data["session_id"] = session_id
            
        if extra_dimensions:
            for k, v in extra_dimensions.items():
                log_data[k] = v
                
        self.info(f"Performance metric: {metric_name}={value}{unit}", trace_id=trace_id, **log_data)


# 检查是否可用asyncio (用于timed装饰器)
try:
    import asyncio
    asyncio_is_available = True
except ImportError:
    asyncio_is_available = False
    
# 全局系统日志实例
system_logger = SystemLogger() 