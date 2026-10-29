"""An INI-style config parser."""
from .parser import Config, ConfigError, parse

__all__ = ["parse", "Config", "ConfigError"]
