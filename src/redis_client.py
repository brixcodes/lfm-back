import redis.asyncio as redis
from src.config import settings


_redis = None


def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            settings.REDIS_CACHE_URL,
            decode_responses=True  # utile pour éviter d'avoir des bytes
        )
    return _redis


async def set_to_redis(key, value, ex: int | None = None):
    redis_client = get_redis()
    return await redis_client.set(
        f"{settings.REDIS_NAMESPACE}:{key}", value, ex=ex
    )


async def get_from_redis(key):
    redis_client = get_redis()
    return await redis_client.get(f"{settings.REDIS_NAMESPACE}:{key}")
