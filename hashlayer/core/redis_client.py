"""
Redis Configuration and Client

Redis client setup and configuration for session storage.
"""

import json
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import redis

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis configuration settings."""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.session_prefix = "session:"
        self.nonce_prefix = "nonce:"
        self.hotkeys_prefix = "hotkeys:"  # coldkey -> hotkeys 缓存
        self.default_ttl = 86400  # 24 hours for sessions
        self.nonce_ttl = 300  # 5 minutes for nonces

        # Log configuration for debugging
        logger.info("🔧 Redis configuration:")
        logger.info(f"   Redis URL: {self.redis_url}")
        logger.info(f"   Session prefix: {self.session_prefix}")
        logger.info(f"   Default TTL: {self.default_ttl}s")
        logger.info(f"   Nonce TTL: {self.nonce_ttl}s")


class RedisClient:
    """Redis client wrapper for session management."""

    def __init__(self, config: Optional[RedisConfig] = None):
        self.config = config or RedisConfig()
        self._client = None
        self._setup_client()

    def _setup_client(self):
        """Setup Redis client connection."""
        try:
            # Parse Redis URL
            parsed = urlparse(self.config.redis_url)

            logger.info("🔗 Attempting Redis connection:")
            logger.info(f"   Parsed URL: {self.config.redis_url}")
            logger.info(f"   Host: {parsed.hostname or 'localhost'}")
            logger.info(f"   Port: {parsed.port or 6379}")
            logger.info(f"   DB: {int(parsed.path.lstrip('/')) if parsed.path else 0}")

            # Create Redis client
            self._client = redis.Redis(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                db=int(parsed.path.lstrip("/")) if parsed.path else 0,
                password=parsed.password,
                decode_responses=True,  # Automatically decode bytes to strings
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test connection
            self._client.ping()
            logger.info(f"✅ Redis connected successfully: {self.config.redis_url}")

        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.error(f"   URL attempted: {self.config.redis_url}")
            logger.error(
                f"   Host: {
                    parsed.hostname or 'localhost'
                    if 'parsed' in locals()
                    else 'unknown'
                }"
            )
            logger.error(
                f"   Port: {parsed.port or 6379 if 'parsed' in locals() else 'unknown'}"
            )
            logger.warning("🔄 Falling back to memory storage")
            self._client = None

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self._client:
            return False
        try:
            result = self._client.ping()
            if not result:
                logger.warning(
                    "🔄 Redis ping returned False, attempting reconnection..."
                )
                self._setup_client()
                return self._client is not None
            return True
        except Exception as e:
            logger.warning(f"🔄 Redis ping failed ({e}), attempting reconnection...")
            self._setup_client()
            return self._client is not None

    def set_session(
        self, token: str, session_data: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """
        Store session data in Redis.

        Args:
            token: Session token
            session_data: Session data dictionary
            ttl: Time to live in seconds (default: 24 hours)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            return False

        try:
            key = f"{self.config.session_prefix}{token}"
            ttl = ttl or self.config.default_ttl

            # Store as JSON
            self._client.setex(key, ttl, json.dumps(session_data, default=str))

            logger.info(f"📝 Session stored in Redis: {token[:10]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to store session in Redis: {e}")
            return False

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data from Redis.

        Args:
            token: Session token

        Returns:
            Session data if found, None otherwise
        """
        if not self.is_available:
            return None

        try:
            key = f"{self.config.session_prefix}{token}"
            data = self._client.get(key)

            if data:
                session_data = json.loads(data)
                remaining_ttl = self._client.ttl(key)

                logger.info(
                    (
                        f"🔍 Session retrieved from Redis:"
                        f"{token[:10]}... (TTL: {remaining_ttl}s)"
                    )
                )
                return session_data
            else:
                logger.info(f"🔍 Session not found in Redis: {token[:10]}...")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to retrieve session from Redis: {e}")
            return None

    def delete_session(self, token: str) -> bool:
        """
        Delete session from Redis.

        Args:
            token: Session token

        Returns:
            True if deleted, False otherwise
        """
        if not self.is_available:
            return False

        try:
            key = f"{self.config.session_prefix}{token}"
            result = self._client.delete(key)

            if result:
                logger.info(f"🗑️ Session deleted from Redis: {token[:10]}...")
            else:
                logger.info(f"🔍 Session not found for deletion: {token[:10]}...")

            return bool(result)

        except Exception as e:
            logger.error(f"❌ Failed to delete session from Redis: {e}")
            return False

    def refresh_session(self, token: str, ttl: Optional[int] = None) -> bool:
        """
        Slide a session's expiry forward (sliding-window renewal).

        Resets the key's TTL without rewriting the stored value, so an active
        user's session keeps getting extended on each request.

        Args:
            token: Session token
            ttl: New time to live in seconds (default: configured default_ttl)

        Returns:
            True if the TTL was refreshed, False if the session is missing/expired
            or Redis is unavailable.
        """
        if not self.is_available:
            return False

        try:
            key = f"{self.config.session_prefix}{token}"
            ttl = ttl or self.config.default_ttl

            # expire() returns False when the key does not exist.
            renewed = bool(self._client.expire(key, ttl))
            if renewed:
                logger.debug(
                    f"🔄 Session TTL refreshed in Redis: {token[:10]}... (TTL: {ttl}s)"
                )
            return renewed

        except Exception as e:
            logger.error(f"❌ Failed to refresh session TTL in Redis: {e}")
            return False

    def delete_user_sessions(self, user_address: str) -> int:
        """
        Delete all sessions for a user.

        Args:
            user_address: User's wallet address

        Returns:
            Number of sessions deleted
        """
        if not self.is_available:
            return 0

        try:
            # Find all session keys
            pattern = f"{self.config.session_prefix}*"
            keys = self._client.keys(pattern)

            deleted_count = 0
            for key in keys:
                try:
                    session_data = json.loads(self._client.get(key))
                    if session_data.get("address") == user_address:
                        self._client.delete(key)
                        deleted_count += 1
                except Exception:
                    continue

            if deleted_count > 0:
                logger.info(
                    (
                        f"🗑️ Deleted {deleted_count} sessions"
                        f"for user {user_address[:10]}..."
                    )
                )

            return deleted_count

        except Exception as e:
            logger.error(f"❌ Failed to delete user sessions: {e}")
            return 0

    def set_nonce(self, address: str, nonce_data: Dict[str, Any]) -> bool:
        """
        Store nonce data in Redis.

        Args:
            address: Wallet address
            nonce_data: Nonce data dictionary

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            return False

        try:
            key = f"{self.config.nonce_prefix}{address}"

            # Store with nonce TTL (5 minutes)
            self._client.setex(
                key, self.config.nonce_ttl, json.dumps(nonce_data, default=str)
            )

            logger.info(
                (
                    f"📝 Nonce stored in Redis: {address[:10]}..."
                    f"(TTL: {self.config.nonce_ttl}s)"
                )
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to store nonce in Redis: {e}")
            return False

    def get_nonce(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve nonce data from Redis.

        Args:
            address: Wallet address

        Returns:
            Nonce data if found, None otherwise
        """
        if not self.is_available:
            return None

        try:
            key = f"{self.config.nonce_prefix}{address}"
            data = self._client.get(key)

            if data:
                nonce_data = json.loads(data)
                remaining_ttl = self._client.ttl(key)

                logger.info(
                    (
                        f"🔍 Nonce retrieved from Redis:"
                        f"{address[:10]}... (TTL: {remaining_ttl}s)"
                    )
                )
                return nonce_data
            else:
                logger.info(f"🔍 Nonce not found in Redis: {address[:10]}...")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to retrieve nonce from Redis: {e}")
            return None

    def delete_nonce(self, address: str) -> bool:
        """
        Delete nonce from Redis.

        Args:
            address: Wallet address

        Returns:
            True if deleted, False otherwise
        """
        if not self.is_available:
            return False

        try:
            key = f"{self.config.nonce_prefix}{address}"
            result = self._client.delete(key)

            if result:
                logger.info(f"🗑️ Nonce deleted from Redis: {address[:10]}...")

            return bool(result)

        except Exception as e:
            logger.error(f"❌ Failed to delete nonce from Redis: {e}")
            return False

    # ============================
    # Hotkeys 缓存方法 (coldkey -> hotkeys)
    # ============================

    def set_hotkeys(self, coldkey: str, hotkeys: list) -> bool:
        """
        缓存 coldkey 对应的 hotkeys 列表（永久缓存，由定时任务管理更新）

        Args:
            coldkey: 冷钱包地址
            hotkeys: hotkey 列表

        Returns:
            True if successful
        """
        if not self.is_available:
            return False

        try:
            key = f"{self.config.hotkeys_prefix}{coldkey}"
            self._client.set(key, json.dumps(hotkeys))

            logger.debug(
                (
                    f"📝 Hotkeys cached for coldkey"
                    f"{coldkey[:10]}...: {len(hotkeys)} hotkeys"
                )
            )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cache hotkeys: {e}")
            return False

    def get_hotkeys(self, coldkey: str) -> Optional[list]:
        """
        获取缓存的 hotkeys 列表

        Args:
            coldkey: 冷钱包地址

        Returns:
            hotkeys 列表，未找到返回 None
        """
        if not self.is_available:
            return None

        try:
            key = f"{self.config.hotkeys_prefix}{coldkey}"
            data = self._client.get(key)

            if data:
                hotkeys = json.loads(data)
                logger.debug(
                    (
                        f"📦 Hotkeys retrieved for coldkey"
                        f"{coldkey[:10]}...: {len(hotkeys)} hotkeys"
                    )
                )
                return hotkeys
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get hotkeys: {e}")
            return None

    def get_all_coldkeys(self) -> list:
        """
        获取所有已缓存的 coldkey 列表（用于定时任务更新）

        Returns:
            coldkey 列表
        """
        if not self.is_available:
            return []

        try:
            pattern = f"{self.config.hotkeys_prefix}*"
            keys = self._client.keys(pattern)

            # 提取 coldkey（去掉前缀）
            prefix_len = len(self.config.hotkeys_prefix)
            coldkeys = [key[prefix_len:] for key in keys]

            return coldkeys
        except Exception as e:
            logger.error(f"❌ Failed to get all coldkeys: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics.

        Returns:
            Statistics dictionary
        """
        if not self.is_available:
            return {"status": "unavailable", "sessions": 0, "nonces": 0}

        try:
            session_keys = self._client.keys(f"{self.config.session_prefix}*")
            nonce_keys = self._client.keys(f"{self.config.nonce_prefix}*")

            return {
                "status": "connected",
                "sessions": len(session_keys),
                "nonces": len(nonce_keys),
                "total_keys": len(session_keys) + len(nonce_keys),
                "redis_info": {
                    "used_memory": self._client.info().get("used_memory_human", "N/A"),
                    "connected_clients": self._client.info().get(
                        "connected_clients", 0
                    ),
                },
            }

        except Exception as e:
            logger.error(f"❌ Failed to get Redis stats: {e}")
            return {"status": "error", "error": str(e)}


# Global Redis client instance
_redis_client = None


def get_redis_client() -> RedisClient:
    """Get or create Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
