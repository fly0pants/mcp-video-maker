"""
日志工具模块
提供统一的日志配置和管理
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger


class InterceptHandler(logging.Handler):
    """拦截标准库日志并转发到loguru"""
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    enable_json: bool = False
):
    """
    配置日志系统
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径（可选）
        rotation: 日志轮转大小
        retention: 日志保留时间
        enable_json: 是否启用JSON格式日志
    """
    # 移除默认处理器
    logger.remove()
    
    # 自定义格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 控制台输出
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # 文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        if enable_json:
            logger.add(
                str(log_path),
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
                level=log_level,
                rotation=rotation,
                retention=retention,
                compression="gz",
                serialize=True,
            )
        else:
            logger.add(
                str(log_path),
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
                level=log_level,
                rotation=rotation,
                retention=retention,
                compression="gz",
            )
    
    # 拦截标准库日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # 设置特定日志记录器的级别
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
    
    logger.info(f"日志系统初始化完成，级别: {log_level}")


def get_logger(name: str = None):
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        logger实例
    """
    if name:
        return logger.bind(name=name)
    return logger


class AgentLogger:
    """代理专用日志记录器"""
    
    def __init__(self, agent_id: str, agent_name: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self._logger = logger.bind(
            agent_id=agent_id,
            agent_name=agent_name
        )
    
    def debug(self, message: str, **kwargs):
        self._logger.debug(f"[{self.agent_id}] {message}", **kwargs)
    
    def info(self, message: str, **kwargs):
        self._logger.info(f"[{self.agent_id}] {message}", **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._logger.warning(f"[{self.agent_id}] {message}", **kwargs)
    
    def error(self, message: str, **kwargs):
        self._logger.error(f"[{self.agent_id}] {message}", **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._logger.critical(f"[{self.agent_id}] {message}", **kwargs)
    
    def log_command(self, action: str, target: str, parameters: dict):
        """记录命令日志"""
        self._logger.info(
            f"[{self.agent_id}] 发送命令: {action} -> {target}",
            extra={"parameters": parameters}
        )
    
    def log_event(self, event_type: str, data: dict):
        """记录事件日志"""
        self._logger.info(
            f"[{self.agent_id}] 事件: {event_type}",
            extra={"data": data}
        )
    
    def log_error(self, error_code: str, error_message: str, details: dict = None):
        """记录错误日志"""
        self._logger.error(
            f"[{self.agent_id}] 错误 [{error_code}]: {error_message}",
            extra={"details": details}
        )


class WorkflowLogger:
    """工作流专用日志记录器"""
    
    def __init__(self, workflow_id: str, session_id: str):
        self.workflow_id = workflow_id
        self.session_id = session_id
        self._logger = logger.bind(
            workflow_id=workflow_id,
            session_id=session_id
        )
    
    def log_stage_start(self, stage: str):
        """记录阶段开始"""
        self._logger.info(f"[{self.workflow_id}] 阶段开始: {stage}")
    
    def log_stage_complete(self, stage: str, duration_ms: int = None):
        """记录阶段完成"""
        msg = f"[{self.workflow_id}] 阶段完成: {stage}"
        if duration_ms:
            msg += f" (耗时: {duration_ms}ms)"
        self._logger.info(msg)
    
    def log_stage_error(self, stage: str, error: str):
        """记录阶段错误"""
        self._logger.error(f"[{self.workflow_id}] 阶段错误: {stage} - {error}")
    
    def log_workflow_complete(self, total_duration_ms: int):
        """记录工作流完成"""
        self._logger.info(
            f"[{self.workflow_id}] 工作流完成，总耗时: {total_duration_ms}ms"
        )
    
    def log_workflow_failed(self, reason: str):
        """记录工作流失败"""
        self._logger.error(f"[{self.workflow_id}] 工作流失败: {reason}")
