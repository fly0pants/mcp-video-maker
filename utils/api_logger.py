import time
import functools
import traceback
from typing import Any, Dict, Optional, Callable, TypeVar, cast
from .logger import system_logger

# 类型变量定义
F = TypeVar('F', bound=Callable[..., Any])

def log_api_call(service: str, endpoint: str) -> Callable[[F], F]:
    """
    装饰器：记录API调用的性能和结果
    
    Args:
        service: 服务名称（如 'openai', 'stability_ai'等）
        endpoint: 端点名称
        
    用法:
        @log_api_call('openai', 'chat_completions')
        async def call_openai_api(prompt, **kwargs):
            # API调用代码
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            trace_id = kwargs.pop('trace_id', None)
            start_time = time.time()
            
            # 提取可能存在的参数数据
            params = {}
            if kwargs:
                # 复制并简化参数以便记录
                for k, v in kwargs.items():
                    if isinstance(v, dict):
                        params[k] = f"[dict with {len(v)} keys]"
                    elif isinstance(v, (list, tuple)):
                        params[k] = f"[{type(v).__name__} with {len(v)} items]"
                    elif isinstance(v, str) and len(v) > 100:
                        params[k] = f"{v[:50]}...{v[-50:]}"
                    else:
                        params[k] = str(v)
            
            # 对于非关键字参数，尝试提取一些有意义的信息
            if args and len(args) > 0:
                params['args'] = f"[{len(args)} positional args]"
            
            try:
                # 调用原始函数
                result = await func(*args, **kwargs)
                
                # 计算耗时
                end_time = time.time()
                duration = end_time - start_time
                
                # 记录成功结果
                system_logger.log_api_call(
                    service=service,
                    endpoint=endpoint,
                    params=params,
                    status_code=getattr(result, 'status_code', 200),
                    response=result,
                    trace_id=trace_id,
                    duration=duration
                )
                
                # 记录性能指标
                system_logger.log_performance_metric(
                    metric_name="api_latency",
                    value=round(duration, 3),
                    unit="seconds",
                    component=f"{service}.{endpoint}",
                    trace_id=trace_id
                )
                
                return result
            except Exception as e:
                # 计算耗时
                end_time = time.time()
                duration = end_time - start_time
                
                # 获取异常详情
                error_message = str(e)
                tb = traceback.format_exc()
                
                # 记录失败结果
                system_logger.log_api_call(
                    service=service,
                    endpoint=endpoint,
                    params=params,
                    error=f"{error_message}\n{tb}",
                    trace_id=trace_id,
                    duration=duration
                )
                
                # 重新抛出异常
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            trace_id = kwargs.pop('trace_id', None)
            start_time = time.time()
            
            # 提取可能存在的参数数据
            params = {}
            if kwargs:
                # 复制并简化参数以便记录
                for k, v in kwargs.items():
                    if isinstance(v, dict):
                        params[k] = f"[dict with {len(v)} keys]"
                    elif isinstance(v, (list, tuple)):
                        params[k] = f"[{type(v).__name__} with {len(v)} items]"
                    elif isinstance(v, str) and len(v) > 100:
                        params[k] = f"{v[:50]}...{v[-50:]}"
                    else:
                        params[k] = str(v)
            
            # 对于非关键字参数，尝试提取一些有意义的信息
            if args and len(args) > 0:
                params['args'] = f"[{len(args)} positional args]"
            
            try:
                # 调用原始函数
                result = func(*args, **kwargs)
                
                # 计算耗时
                end_time = time.time()
                duration = end_time - start_time
                
                # 记录成功结果
                system_logger.log_api_call(
                    service=service,
                    endpoint=endpoint,
                    params=params,
                    status_code=getattr(result, 'status_code', 200),
                    response=result,
                    trace_id=trace_id,
                    duration=duration
                )
                
                # 记录性能指标
                system_logger.log_performance_metric(
                    metric_name="api_latency",
                    value=round(duration, 3),
                    unit="seconds",
                    component=f"{service}.{endpoint}",
                    trace_id=trace_id
                )
                
                return result
            except Exception as e:
                # 计算耗时
                end_time = time.time()
                duration = end_time - start_time
                
                # 获取异常详情
                error_message = str(e)
                tb = traceback.format_exc()
                
                # 记录失败结果
                system_logger.log_api_call(
                    service=service,
                    endpoint=endpoint,
                    params=params,
                    error=f"{error_message}\n{tb}",
                    trace_id=trace_id,
                    duration=duration
                )
                
                # 重新抛出异常
                raise
        
        # 根据原始函数是否为协程函数选择包装器
        import inspect
        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
            
    return decorator


# 辅助函数用于添加到utils包导出
def get_api_logger():
    """返回API日志装饰器工具"""
    return log_api_call 