"""
In-Process Cache System

Provides TTL-based async caching with memory-efficient operations:
- LRU eviction policy with configurable size limits
- TTL-based expiration for all cached items
- Thread-safe operations for async FastAPI applications
- Performance metrics collection for monitoring
- Cache invalidation strategies
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set, Union, Callable, Awaitable
from collections import OrderedDict
from threading import RLock
import weakref
import sys
import json

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    value: Any
    created_at: float
    ttl_seconds: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has exceeded its TTL"""
        return time.time() > (self.created_at + self.ttl_seconds)
    
    def touch(self) -> None:
        """Update access metadata"""
        self.access_count += 1
        self.last_accessed = time.time()


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for monitoring"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "total_size_bytes": self.total_size_bytes,
            "entry_count": self.entry_count,
            "hit_rate_percent": round(self.hit_rate, 2)
        }


class InProcessCache:
    """
    Thread-safe in-process cache with TTL and LRU eviction
    
    Features:
    - TTL-based expiration
    - LRU eviction when size limits exceeded
    - Memory usage tracking
    - Performance metrics
    - Async-safe operations
    """
    
    def __init__(
        self,
        name: str,
        max_size_mb: int = 100,
        max_entries: int = 1000,
        default_ttl_seconds: int = 3600,
        cleanup_interval_seconds: int = 300
    ):
        self.name = name
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        
        # Thread-safe storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()
        self._metrics = CacheMetrics()
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        logger.info(
            f"Initialized cache '{name}'",
            extra={
                "cache_name": name,
                "max_size_mb": max_size_mb,
                "max_entries": max_entries,
                "default_ttl_seconds": default_ttl_seconds
            }
        )
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate memory size of cached value"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float, bool)):
                return sys.getsizeof(value)
            elif isinstance(value, (list, tuple, dict)):
                # Approximate size using JSON serialization
                return len(json.dumps(value, default=str).encode('utf-8'))
            else:
                # Fallback to sys.getsizeof
                return sys.getsizeof(value)
        except Exception:
            # Conservative estimate if calculation fails
            return 1024
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries to free space"""
        while (
            len(self._cache) > self.max_entries or 
            self._metrics.total_size_bytes > self.max_size_bytes
        ):
            if not self._cache:
                break
                
            # Remove oldest entry (LRU)
            key, entry = self._cache.popitem(last=False)
            self._metrics.total_size_bytes -= entry.size_bytes
            self._metrics.entry_count -= 1
            self._metrics.evictions += 1
            
            logger.debug(
                f"Evicted LRU entry from cache '{self.name}'",
                extra={
                    "cache_name": self.name,
                    "evicted_key": key,
                    "remaining_entries": len(self._cache),
                    "total_size_mb": round(self._metrics.total_size_bytes / (1024 * 1024), 2)
                }
            )
    
    def _expire_entries(self) -> int:
        """Remove expired entries and return count removed"""
        expired_keys = []
        current_time = time.time()
        
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        expired_count = 0
        for key in expired_keys:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._metrics.total_size_bytes -= entry.size_bytes
                self._metrics.entry_count -= 1
                self._metrics.expirations += 1
                expired_count += 1
        
        if expired_count > 0:
            logger.debug(
                f"Expired {expired_count} entries from cache '{self.name}'",
                extra={
                    "cache_name": self.name,
                    "expired_count": expired_count,
                    "remaining_entries": len(self._cache)
                }
            )
        
        return expired_count
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, returning None if not found or expired"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._metrics.misses += 1
                return None
            
            if entry.is_expired():
                # Remove expired entry
                self._cache.pop(key)
                self._metrics.total_size_bytes -= entry.size_bytes
                self._metrics.entry_count -= 1
                self._metrics.expirations += 1
                self._metrics.misses += 1
                return None
            
            # Move to end (most recently used)
            entry.touch()
            self._cache.move_to_end(key)
            self._metrics.hits += 1
            
            return entry.value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set value in cache with optional TTL override"""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        size_bytes = self._calculate_size(value)
        
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache.pop(key)
                self._metrics.total_size_bytes -= old_entry.size_bytes
                self._metrics.entry_count -= 1
            
            # Create new entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl_seconds=ttl,
                size_bytes=size_bytes
            )
            
            # Add to cache
            self._cache[key] = entry
            self._metrics.total_size_bytes += size_bytes
            self._metrics.entry_count += 1
            
            # Evict if necessary
            self._evict_lru()
    
    async def delete(self, key: str) -> bool:
        """Delete entry from cache, returning True if it existed"""
        with self._lock:
            entry = self._cache.pop(key, None)
            if entry:
                self._metrics.total_size_bytes -= entry.size_bytes
                self._metrics.entry_count -= 1
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all entries from cache"""
        with self._lock:
            self._cache.clear()
            self._metrics = CacheMetrics()
        
        logger.info(f"Cleared all entries from cache '{self.name}'")
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl_seconds: Optional[int] = None
    ) -> Any:
        """Get value from cache or compute and cache it if not found"""
        # Try to get from cache first
        value = await self.get(key)
        if value is not None:
            return value
        
        # Compute value
        value = await factory()
        
        # Cache the computed value
        await self.set(key, value, ttl_seconds)
        
        return value
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current cache metrics"""
        with self._lock:
            return {
                "name": self.name,
                "max_size_mb": self.max_size_bytes // (1024 * 1024),
                "max_entries": self.max_entries,
                "current_size_mb": round(self._metrics.total_size_bytes / (1024 * 1024), 2),
                **self._metrics.to_dict()
            }
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup task for expired entries"""
        while not self._shutdown_event.is_set():
            try:
                with self._lock:
                    expired_count = self._expire_entries()
                
                if expired_count > 0:
                    logger.debug(
                        f"Cache cleanup completed for '{self.name}'",
                        extra={
                            "cache_name": self.name,
                            "expired_count": expired_count,
                            "remaining_entries": len(self._cache)
                        }
                    )
                
                # Wait for next cleanup interval
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.cleanup_interval_seconds
                )
                
            except asyncio.TimeoutError:
                # Normal timeout, continue cleanup loop
                continue
            except Exception as e:
                logger.error(
                    f"Error in cache cleanup loop for '{self.name}': {e}",
                    extra={"cache_name": self.name, "error": str(e)}
                )
                await asyncio.sleep(60)  # Wait before retrying
    
    async def start_cleanup(self) -> None:
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info(f"Started background cleanup for cache '{self.name}'")
    
    async def stop_cleanup(self) -> None:
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._shutdown_event.set()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._cleanup_task.cancel()
            
            self._cleanup_task = None
            logger.info(f"Stopped background cleanup for cache '{self.name}'")


class CacheManager:
    """
    Global cache manager for multiple named caches
    
    Provides centralized management of application caches with
    different configurations per cache type.
    """
    
    def __init__(self):
        self._caches: Dict[str, InProcessCache] = {}
        self._lock = RLock()
    
    def get_cache(
        self,
        name: str,
        max_size_mb: int = 100,
        max_entries: int = 1000,
        default_ttl_seconds: int = 3600,
        cleanup_interval_seconds: int = 300
    ) -> InProcessCache:
        """Get or create a named cache with specified configuration"""
        with self._lock:
            if name not in self._caches:
                self._caches[name] = InProcessCache(
                    name=name,
                    max_size_mb=max_size_mb,
                    max_entries=max_entries,
                    default_ttl_seconds=default_ttl_seconds,
                    cleanup_interval_seconds=cleanup_interval_seconds
                )
            return self._caches[name]
    
    async def start_all_cleanup(self) -> None:
        """Start cleanup tasks for all caches"""
        for cache in self._caches.values():
            await cache.start_cleanup()
    
    async def stop_all_cleanup(self) -> None:
        """Stop cleanup tasks for all caches"""
        for cache in self._caches.values():
            await cache.stop_cleanup()
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all caches"""
        with self._lock:
            return {name: cache.get_metrics() for name, cache in self._caches.items()}
    
    async def clear_all(self) -> None:
        """Clear all caches"""
        for cache in self._caches.values():
            await cache.clear()


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions for common cache operations
async def get_cached(
    cache_name: str,
    key: str,
    factory: Callable[[], Awaitable[Any]],
    ttl_seconds: Optional[int] = None,
    **cache_config
) -> Any:
    """
    Convenience function to get or compute cached value
    
    Args:
        cache_name: Name of the cache to use
        key: Cache key
        factory: Async function to compute value if not cached
        ttl_seconds: TTL override for this entry
        **cache_config: Configuration for cache creation if it doesn't exist
    """
    cache = cache_manager.get_cache(cache_name, **cache_config)
    return await cache.get_or_set(key, factory, ttl_seconds)


async def invalidate_cache_key(cache_name: str, key: str) -> bool:
    """
    Invalidate a specific cache key
    
    Args:
        cache_name: Name of the cache
        key: Cache key to invalidate
        
    Returns:
        True if key existed and was removed
    """
    if cache_name in cache_manager._caches:
        cache = cache_manager._caches[cache_name]
        return await cache.delete(key)
    return False


async def invalidate_cache_pattern(cache_name: str, pattern: str) -> int:
    """
    Invalidate cache keys matching a pattern (simple string contains)
    
    Args:
        cache_name: Name of the cache
        pattern: Pattern to match keys against
        
    Returns:
        Number of keys invalidated
    """
    if cache_name not in cache_manager._caches:
        return 0
    
    cache = cache_manager._caches[cache_name]
    invalidated_count = 0
    
    with cache._lock:
        keys_to_remove = [key for key in cache._cache.keys() if pattern in key]
        
        for key in keys_to_remove:
            if await cache.delete(key):
                invalidated_count += 1
    
    return invalidated_count


def get_cache_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics for all caches"""
    return cache_manager.get_all_metrics()