import os
from smolagents import tool

_SOURCES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SOURCES.md")


@tool
def get_sources() -> str:
    """Returns the list of data sources this bot uses. Call this when a user asks where the bot gets its information."""
    try:
        with open(_SOURCES_PATH, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Source attribution is currently unavailable."
