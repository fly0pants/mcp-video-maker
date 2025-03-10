import time
import asyncio
import logging
from typing import Dict, Any, Optional


class TokenBucket:
    """令牌桶限流器实现"""
    
    def __init__(self, rate: float, capacity: float):
        """
        初始化令牌桶
        
        Args:
            rate: 令牌生成速率（每秒）
            capacity: 桶容量
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: float = 1.0) -> bool:
        """
        尝试获取指定数量的令牌
        
        Args:
            tokens: 需要的令牌数量
            
        Returns:
            是否成功获取令牌
        """
        async with self.lock:
            self._refill()
            
            if tokens <= self.tokens:
                self.tokens -= tokens
                return True
            else:
                return False
    
    async def wait_for_tokens(self, tokens: float = 1.0, timeout: Optional[float] = None) -> bool:
        """
        等待直到有足够的令牌可用
        
        Args:
            tokens: 需要的令牌数量
            timeout: 超时时间（秒），None表示无限等待
            
        Returns:
            是否成功获取令牌（超时返回False）
        """
        start_time = time.time()
        
        while True:
            # 检查是否超时
            if timeout is not None and time.time() - start_time > timeout:
                return False
            
            # 尝试获取令牌
            if await self.acquire(tokens):
                return True
            
            # 计算需要等待的时间
            async with self.lock:
                self._refill()
                missing_tokens = tokens - self.tokens
                wait_time = missing_tokens / self.rate
                
                # 添加一点随机抖动，避免所有请求同时醒来
                wait_time = max(0.01, wait_time * (0.9 + 0.2 * (time.time() % 1)))
            
            # 等待一段时间再重试
            await asyncio.sleep(wait_time)
    
    def _refill(self):
        """重新填充令牌桶"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # 计算新增令牌数量
        new_tokens = elapsed * self.rate
        
        # 更新令牌数量，不超过容量
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now


class RateLimiter:
    """速率限制器，管理多个令牌桶"""
    
    def __init__(self):
        self.logger = logging.getLogger("RateLimiter")
        self.buckets: Dict[str, TokenBucket] = {}
        self.default_rate = 50.0  # 默认每秒50个请求
        self.default_capacity = 100.0  # 默认桶容量100
    
    def get_bucket(self, key: str, rate: Optional[float] = None, capacity: Optional[float] = None) -> TokenBucket:
        """
        获取指定键的令牌桶，如果不存在则创建
        
        Args:
            key: 桶标识符
            rate: 令牌生成速率（每秒）
            capacity: 桶容量
            
        Returns:
            令牌桶实例
        """
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(
                rate=rate or self.default_rate,
                capacity=capacity or self.default_capacity
            )
        return self.buckets[key]
    
    async def acquire(self, key: str, tokens: float = 1.0) -> bool:
        """
        尝试从指定桶获取令牌
        
        Args:
            key: 桶标识符
            tokens: 需要的令牌数量
            
        Returns:
            是否成功获取令牌
        """
        bucket = self.get_bucket(key)
        return await bucket.acquire(tokens)
    
    async def wait_for_tokens(self, key: str, tokens: float = 1.0, timeout: Optional[float] = None) -> bool:
        """
        等待直到指定桶有足够的令牌可用
        
        Args:
            key: 桶标识符
            tokens: 需要的令牌数量
            timeout: 超时时间（秒），None表示无限等待
            
        Returns:
            是否成功获取令牌
        """
        bucket = self.get_bucket(key)
        return await bucket.wait_for_tokens(tokens, timeout)
    
    def update_rate(self, key: str, rate: float, capacity: Optional[float] = None):
        """
        更新指定桶的速率和容量
        
        Args:
            key: 桶标识符
            rate: 新的令牌生成速率
            capacity: 新的桶容量（可选）
        """
        if key in self.buckets:
            bucket = self.buckets[key]
            bucket.rate = rate
            if capacity is not None:
                bucket.capacity = capacity
        else:
            self.get_bucket(key, rate, capacity)
    
    def remove_bucket(self, key: str):
        """
        移除指定的令牌桶
        
        Args:
            key: 桶标识符
        """
        if key in self.buckets:
            del self.buckets[key]


# 创建全局限流器实例
global_rate_limiter = RateLimiter() 