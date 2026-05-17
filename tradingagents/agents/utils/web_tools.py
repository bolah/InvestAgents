"""Web search tool for the Macro/Secular Analyst.

Uses duckduckgo-search (no API key required). Falls back gracefully to an
empty string if the package is unavailable or the search fails.
"""

from langchain_core.tools import tool
from typing import Annotated
import sys as _sys

# Guard: only run the import block once so that test mocks set before
# ``importlib.reload`` are not overwritten by a real import on reload.
_this_module = _sys.modules.get(__name__)
if _this_module is None or not getattr(_this_module, "_ddgs_initialized", False):
    try:
        from duckduckgo_search import DDGS
        _DDGS_AVAILABLE = True
    except ImportError:
        DDGS = None
        _DDGS_AVAILABLE = False
    _ddgs_initialized = True


@tool
def web_search_tool(
    query: Annotated[str, "Search query for industry and macro research"],
    max_results: Annotated[int, "Maximum number of results to return (default 5)"] = 5,
) -> str:
    """
    Search the web for qualitative industry and macro context.
    Returns title and snippet for each result.
    Use only for qualitative narrative — do not rely on web results for financial figures.
    Falls back to empty string if search is unavailable.
    """
    # Resolve DDGS at call time from the module's own namespace so that
    # a patched value set before reload is respected.
    _mod = _sys.modules.get(__name__)
    ddgs_cls = getattr(_mod, "DDGS", None) if _mod is not None else None
    ddgs_available = getattr(_mod, "_DDGS_AVAILABLE", False) if _mod is not None else False

    if not ddgs_available or ddgs_cls is None:
        return "Web search unavailable (duckduckgo-search not installed)."
    try:
        with ddgs_cls() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"No web search results found for: {query}"
        lines = [f"## Web Search Results: {query}", ""]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", r.get("snippet", "No snippet"))
            lines.append(f"**{i}. {title}**")
            lines.append(body)
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Web search failed for '{query}': {e}"
