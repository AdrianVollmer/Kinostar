#!/usr/bin/env python3
"""Cache management for API requests."""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


class Cache:
    """File-based cache with expiration."""

    CACHE_DURATION = 3600  # 1 hour in seconds

    def __init__(self) -> None:
        self.cache_dir = self._get_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_cache_dir() -> Path:
        """Get the XDG cache directory for kinostar."""
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            cache_dir = Path(xdg_cache_home)
        else:
            cache_dir = Path.home() / ".cache"

        return cache_dir / "kinostar"

    def _get_cache_key(self, prefix: str, *args: Any) -> str:
        """Generate a cache key from prefix and arguments."""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, prefix: str, *args: Any) -> dict[str, Any] | None:
        """Get cached data if it exists and is not expired."""
        cache_key = self._get_cache_key(prefix, *args)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cached_data = json.load(f)

            timestamp = cached_data.get("timestamp", 0)
            current_time = time.time()

            if current_time - timestamp > self.CACHE_DURATION:
                cache_path.unlink()
                return None

            return cached_data.get("data")

        except (json.JSONDecodeError, OSError):
            if cache_path.exists():
                cache_path.unlink()
            return None

    def set(self, prefix: str, data: dict[str, Any], *args: Any) -> None:
        """Store data in cache with current timestamp."""
        cache_key = self._get_cache_key(prefix, *args)
        cache_path = self._get_cache_path(cache_key)

        cached_data = {"timestamp": time.time(), "data": data}

        try:
            with open(cache_path, "w") as f:
                json.dump(cached_data, f)
        except OSError:
            pass
