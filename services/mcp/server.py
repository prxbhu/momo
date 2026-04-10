"""
MOMO Tool Server — FastMCP over SSE
Registers all MOMO tools and serves them via Server-Sent Events.
"""

from fastmcp import FastMCP
from tools.web import search_web, fetch_url, get_news
from tools.system import get_current_time, get_system_info
from tools.weather import get_weather
from tools.calendar_tool import get_calendar_events, create_calendar_event
from tools.smart_home import control_device, list_devices
from tools.memory_tool import remember_fact, recall_facts
import os

mcp = FastMCP("MOMO Tool Server")

# ── Web tools ──────────────────────────────
mcp.tool(search_web)
mcp.tool(fetch_url)
mcp.tool(get_news)

# ── System tools ───────────────────────────
mcp.tool(get_current_time)
mcp.tool(get_system_info)

# ── Weather ────────────────────────────────
mcp.tool(get_weather)

# ── Calendar ───────────────────────────────
mcp.tool(get_calendar_events)
mcp.tool(create_calendar_event)

# ── Smart home ─────────────────────────────
mcp.tool(control_device)
mcp.tool(list_devices)

# ── Memory ─────────────────────────────────
mcp.tool(remember_fact)
mcp.tool(recall_facts)

if __name__ == "__main__":
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
    )
