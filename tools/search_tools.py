from smolagents import DuckDuckGoSearchTool, tool

_ddg = DuckDuckGoSearchTool()


@tool
def web_search(query: str) -> str:
    """Search the web for information about Gran Turismo 7 or Forza Motorsport — car lists, performance points, tuning limits, track availability, etc. Reliable sources include gtplanet.net, gran-turismo.com, gt7.fandom.com, forza.fandom.com, and forzamotorsport.net.

    Args:
        query: The search query string.
    """
    return _ddg(query)
