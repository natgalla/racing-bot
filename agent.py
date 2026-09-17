import os
from smolagents import CodeAgent, InferenceClientModel
from tools.discord_tools import get_channel_pins, get_recent_messages, get_guild_events
from tools.search_tools import web_search

SYSTEM_PROMPT = """You are a helpful sim racing Discord bot assistant. Answer questions about:
- The current race spec (car list, tuning rules) — use get_channel_pins first, then get_recent_messages if needed
- The race schedule — use get_guild_events first, check get_recent_messages if the channel may have updated info
- Gran Turismo 7 or Forza Motorsport cars, tunes, and game data — use web_search

Be concise and direct. If the answer isn't in the spec or schedule, say so clearly. Do not guess tuning rules."""


def build_agent(tools=None):
    if tools is None:
        tools = [get_channel_pins, get_recent_messages, get_guild_events, web_search]
    model = InferenceClientModel("Qwen/Qwen2.5-72B-Instruct")
    return CodeAgent(tools=tools, model=model, max_steps=5)


def ask(agent, question: str, channel_id: str, guild_id: str) -> str:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Channel ID: {channel_id}\n"
        f"Guild ID: {guild_id}\n\n"
        f"Question: {question}"
    )
    return agent.run(prompt)
