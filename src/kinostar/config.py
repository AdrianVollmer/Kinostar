#!/usr/bin/env python3
"""Configuration management for Kinostar app."""

import os
import re
import tomllib
from pathlib import Path


class Theater:
    """Represents a cinema theater configuration."""

    def __init__(
        self,
        name: str,
        cinema_id: int,
        default: bool = False,
        filter: str | None = None,
    ) -> None:
        self.name = name
        self.cinema_id = cinema_id
        self.default = default
        self.filter = filter
        self.filter_regex = re.compile(filter) if filter else None


class Config:
    """Application configuration."""

    def __init__(self) -> None:
        self.theaters: list[Theater] = []
        self.global_filter: str | None = None
        self.global_filter_regex: re.Pattern[str] | None = None

    @staticmethod
    def get_config_path() -> Path:
        """Get the XDG config file path."""
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            config_dir = Path(xdg_config_home)
        else:
            config_dir = Path.home() / ".config"

        config_file = config_dir / "kinostar" / "config.toml"
        return config_file

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from XDG config file."""
        config = cls()
        config_path = cls.get_config_path()

        if not config_path.exists():
            config._load_defaults()
            config_path.parent.mkdir(exist_ok=True, parents=True)
            open(config_path, "w").write(Config.create_example_config())
            return config

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)

            config.global_filter = data.get("global_filter")
            if config.global_filter:
                config.global_filter_regex = re.compile(config.global_filter)

            theaters_data = data.get("theaters", [])
            for theater_data in theaters_data:
                theater = Theater(
                    name=theater_data["name"],
                    cinema_id=theater_data["cinema_id"],
                    default=theater_data.get("default", False),
                    filter=theater_data.get("filter"),
                )
                config.theaters.append(theater)

            if not config.theaters:
                config._load_defaults()

        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            config._load_defaults()

        return config

    def _load_defaults(self) -> None:
        """Load default configuration."""
        self.theaters = [
            Theater(
                name="Kino",
                cinema_id=3625,
                default=True,
            )
        ]

    def get_default_theater(self) -> Theater:
        """Get the default theater or the first one."""
        for theater in self.theaters:
            if theater.default:
                return theater

        if self.theaters:
            return self.theaters[0]

        self._load_defaults()
        return self.theaters[0]

    def should_filter_movie(self, movie_name: str, theater: Theater) -> bool:
        """Check if a movie should be filtered out based on title."""
        if self.global_filter_regex and self.global_filter_regex.search(movie_name):
            return True

        if theater.filter_regex and theater.filter_regex.search(movie_name):
            return True

        return False

    @staticmethod
    def create_example_config() -> str:
        """Create an example config file content."""
        return """# Kinostar Configuration File
# Location: ~/.config/kinostar/config.toml (or $XDG_CONFIG_HOME/kinostar/config.toml)

# Global filter: regex pattern to exclude movies by title (applied to all theaters)
# global_filter = "(?i)(sneak|preview)"

# Theater configurations
[[theaters]]
name = "Name of the Theater"
cinema_id = 3625
default = true
# Optional: filter specific to this theater
# filter = "(?i)opera"

# Example: Add another theater
# [[theaters]]
# name = "Another Cinema"
# cinema_id = 1234
# default = false
# filter = "(?i)some_pattern"
"""
