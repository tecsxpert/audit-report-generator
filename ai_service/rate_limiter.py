"""
Rate Limiting Configuration for Flask AI Service
AI Developer 3 Responsibility
Prevents abuse and DoS attacks by limiting requests per IP
"""

import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.strategies import MovingWindowRateLimiter
from flask import jsonify
import redis
from datetime import datetime

logger = logging.getLogger(__name__)


class RateLimiterConfig:
    """Configuration for Flask-Limiter"""
    
    # Default limits
    DEFAULT_LIMIT = "30 per minute"  # 30 requests per minute
    GENERATE_REPORT_LIMIT = "10 per minute"  # Expensive operation
    BATCH_PROCESS_LIMIT = "5 per minute"  # Very expensive
    DESCRIBE_LIMIT = "60 per minute"
    RECOMMEND_LIMIT = "60 per minute"
    CATEGORISE_LIMIT = "60 per minute"
    QUERY_LIMIT = "60 per minute"
    ANALYSE_DOCUMENT_LIMIT = "20 per minute"
    HEALTH_LIMIT = "100 per minute"
    
    @staticmethod
    def get_limiter(app=None):
        """
        Initialize rate limiter with Redis backend
        
        Args:
            app: Flask application instance
            
        Returns:
            Limiter instance
        """
        try:
            # Try to use Redis for distributed rate limiting
            redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            # Test connection
            redis_client.ping()
            
            limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                default_limits=[RateLimiterConfig.DEFAULT_LIMIT],
                storage_uri="redis://localhost:6379",
                strategy=MovingWindowRateLimiter,
            )
            logger.info("Rate limiter initialized with Redis backend")
            
        except Exception as e:
            logger.warning(f"Redis connection failed ({str(e)}), using in-memory storage")
            # Fallback to in-memory storage
            limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                default_limits=[RateLimiterConfig.DEFAULT_LIMIT],
                strategy=MovingWindowRateLimiter,
            )
        
        return limiter


def rate_limit_exceeded_handler(e):
    """
    Handle rate limit exceeded errors
    
    Args:
        e: RateLimitExceeded exception
        
    Returns:
        JSON response with 429 status code
    """
    logger.warning(f"Rate limit exceeded for IP: {get_remote_address()}")
    
    return jsonify({
        "error": "Too Many Requests",
        "message": "You have exceeded the rate limit. Please try again later.",
        "status": 429,
        "retry_after": 60
    }), 429


# Rate limit decorator shortcuts
def limit_default(f):
    """Apply default rate limit (30 req/min)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    decorated_function.rate_limit = RateLimiterConfig.DEFAULT_LIMIT
    return decorated_function


def limit_generate_report(f):
    """Apply rate limit for expensive generate-report endpoint (10 req/min)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    decorated_function.rate_limit = RateLimiterConfig.GENERATE_REPORT_LIMIT
    return decorated_function


def limit_batch_process(f):
    """Apply rate limit for batch-process endpoint (5 req/min)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    decorated_function.rate_limit = RateLimiterConfig.BATCH_PROCESS_LIMIT
    return decorated_function


def limit_health_check(f):
    """Apply rate limit for health endpoint (100 req/min)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    decorated_function.rate_limit = RateLimiterConfig.HEALTH_LIMIT
    return decorated_function


class RateLimitMonitor:
    """Monitor and log rate limiting metrics"""
    
    def __init__(self, redis_client=None):
        """Initialize monitor"""
        self.redis_client = redis_client
    
    def log_request(self, ip_address: str, endpoint: str):
        """Log request for monitoring"""
        if self.redis_client:
            try:
                key = f"request_log:{ip_address}:{endpoint}:{datetime.now().strftime('%Y%m%d%H%M')}"
                self.redis_client.incr(key)
                self.redis_client.expire(key, 3600)  # Expire after 1 hour
            except Exception as e:
                logger.error(f"Error logging request: {str(e)}")
    
    def get_request_count(self, ip_address: str, endpoint: str, minutes: int = 1) -> int:
        """Get number of requests from IP in the last N minutes"""
        if not self.redis_client:
            return 0
        
        try:
            count = 0
            now = datetime.now()
            
            for i in range(minutes):
                key = f"request_log:{ip_address}:{endpoint}:{(now.shift(minutes=-i)).strftime('%Y%m%d%H%M')}"
                count += int(self.redis_client.get(key) or 0)
            
            return count
        except Exception as e:
            logger.error(f"Error getting request count: {str(e)}")
            return 0
    
    def get_top_ips(self, limit: int = 10) -> list:
        """Get top IPs by request count"""
        if not self.redis_client:
            return []
        
        try:
            # Scan for keys matching pattern
            keys = self.redis_client.keys("request_log:*")
            ip_counts = {}
            
            for key in keys:
                ip = key.split(":")[1]
                count = int(self.redis_client.get(key) or 0)
                ip_counts[ip] = ip_counts.get(ip, 0) + count
            
            # Sort and return top IPs
            sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_ips[:limit]
        
        except Exception as e:
            logger.error(f"Error getting top IPs: {str(e)}")
            return []
