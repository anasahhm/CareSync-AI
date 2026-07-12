"""
Redis Cache

Thin async wrapper around redis.asyncio used as the backing store for
short-term / shared memory. Falls back to an in-process dict automatically
if Redis is unreachable, so nothing in the agent pipeline breaks when Redis
isn't running (e.g. local dev without docker compose up).
"""
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False


class RedisCache:
    def __init__(self, redis_url: str, namespace: str = "caresyncai"):
        self.redis_url = redis_url
        self.namespace = namespace
        self._client = None
        self._connected = False
        self._local_fallback: dict = {}

    def _key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def connect(self) -> bool:
        if not REDIS_AVAILABLE:
            logger.warning("redis package not installed - using in-process memory fallback")
            return False
        try:
            self._client = aioredis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=2)
            await self._client.ping()
            self._connected = True
            logger.info("RedisCache connected")
            return True
        except Exception as e:
            logger.warning(f"RedisCache: could not connect to Redis ({e}); using in-process fallback")
            self._connected = False
            return False

    async def get(self, key: str) -> Optional[Any]:
        if self._connected:
            try:
                raw = await self._client.get(self._key(key))
                return json.loads(raw) if raw is not None else None
            except Exception as e:
                logger.warning(f"RedisCache.get fallback for {key}: {e}")
        return self._local_fallback.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        if self._connected:
            try:
                payload = json.dumps(value, default=str)
                if ttl_seconds:
                    await self._client.set(self._key(key), payload, ex=ttl_seconds)
                else:
                    await self._client.set(self._key(key), payload)
                return True
            except Exception as e:
                logger.warning(f"RedisCache.set fallback for {key}: {e}")
        self._local_fallback[key] = value
        return True

    async def delete(self, key: str) -> bool:
        if self._connected:
            try:
                await self._client.delete(self._key(key))
            except Exception as e:
                logger.warning(f"RedisCache.delete fallback for {key}: {e}")
        self._local_fallback.pop(key, None)
        return True

    async def health_check(self) -> bool:
        if not self._connected:
            return False
        try:
            await self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False

    async def close(self):
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
