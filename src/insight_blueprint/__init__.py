"""insight-blueprint: MCP server for analysis design management."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("insight-blueprint")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
