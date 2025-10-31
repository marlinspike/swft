from __future__ import annotations

from typing import Callable, TypeVar, ParamSpec, Dict, Tuple
import functools
import time

T = TypeVar("T")
P = ParamSpec("P")


class SimpleTTLCache:
    """Minimal TTL cache used to memoize expensive blob queries without extra deps."""
    def __init__(self, max_items: int, ttl_seconds: int):
        self._max = max_items
        self._ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, T]] = {}

    def __contains__(self, key: str) -> bool:
        """Return True when the key exists and has not expired."""
        entry = self._store.get(key)
        if entry is None: return False
        expires_at, _value = entry
        if expires_at < time.time():
            del self._store[key]
            return False
        return True

    def __getitem__(self, key: str) -> T:
        """Retrieve an item, raising KeyError when the key is missing or expired."""
        expires_at, value = self._store[key]
        if expires_at < time.time():
            del self._store[key]
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: T) -> None:
        """Insert an item, evicting the oldest entry when the cache is full."""
        if len(self._store) >= self._max:
            self._evict()
        self._store[key] = (time.time() + self._ttl, value)

    def _evict(self) -> None:
        """Drop the oldest cached value to honour the max size constraint."""
        if not self._store: return
        oldest_key = min(self._store.items(), key=lambda item: item[1][0])[0]
        del self._store[oldest_key]


def create_cache(max_items: int, ttl_seconds: int) -> SimpleTTLCache:
    """Instantiate a SimpleTTLCache with the requested capacity and lifetime."""
    return SimpleTTLCache(max_items, ttl_seconds)


def memoize(cache: SimpleTTLCache) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that memoizes the wrapped callable using the provided TTL cache."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = f"{func.__module__}.{func.__qualname__}:{args}:{kwargs}"
            if key in cache: return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator
