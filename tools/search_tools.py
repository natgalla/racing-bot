from smolagents import DuckDuckGoSearchTool, tool

_ddg = DuckDuckGoSearchTool()


@tool
def web_search(query: str) -> str:
    """Search the web for information about Gran Turismo 7 or Forza Motorsport — car lists, performance points, tuning limits, track availability, etc. Prefer official sources first: gran-turismo.com for GT7, forzamotorsport.net for Forza Motorsport. Fall back to community sources when official pages lack detail: gtplanet.net, gt7.fandom.com, forza.fandom.com.

    Args:
        query: The search query string.
    """
    return _ddg(query)
