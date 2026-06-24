import redis.asyncio as aioredis
from app.core.config import settings

_redis = None


def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis
