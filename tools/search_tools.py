from smolagents import DuckDuckGoSearchTool, tool

_ddg = DuckDuckGoSearchTool()


@tool
def web_search(query: str) -> str:
    """Search the web for information about Gran Turismo 7 or Forza Motorsport — car lists, performance points, tuning limits, track availability, etc. Prefer official sources first: gran-turismo.com for GT7, forzamotorsport.net for Forza Motorsport. Fall back to community sources when official pages lack detail: gtplanet.net, gt7.fandom.com, forza.fandom.com.

    Args:
        query: The search query string.
    """
    result = _ddg(query)
    return result + "\n\n[Citation instruction: If you use any of the above in your answer, append a new line: `via web search: <URL>` — use the most relevant source URL, with angle brackets to suppress Discord link previews.]"
