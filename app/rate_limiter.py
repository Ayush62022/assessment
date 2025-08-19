"""
Redis-based rate limiter
"""

import time
from typing import Optional
import redis
from fastapi import HTTPException

class RateLimiter:
    def __init__(self, redis_client: redis.Redis, max_requests: int = 30, window_minutes: int = 1):
        self.redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
    
    async def check_rate_limit(self, key: str) -> None:
        """
        Check if request is within rate limit
        
        Args:
            key: Unique identifier for rate limiting (e.g., user:ip)
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        current_time = int(time.time())
        window_start = current_time - self.window_seconds
        
        try:
            # Use Redis sorted set to track requests in time window
            pipe = self.redis.pipeline()
            
            # Remove old requests outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration for cleanup
            pipe.expire(key, self.window_seconds)
            
            results = pipe.execute()
            request_count = results[1]
            
            if request_count >= self.max_requests:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds//60} minute(s)"
                )
                
        except redis.RedisError as e:
            # If Redis fails, log but don't block the request
            print(f"Rate limiter Redis error: {e}")
            pass