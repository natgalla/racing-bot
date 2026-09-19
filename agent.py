import logging
import os
from smolagents import ToolCallingAgent, InferenceClientModel
from tools.discord_tools import get_channel_pins, get_recent_messages, get_guild_events
from tools.search_tools import web_search

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful sim racing Discord bot assistant. Answer questions about:
- The current race spec (car list, tuning rules)
- The race schedule and upcoming events
- Gran Turismo 7 or Forza Motorsport cars, tunes, and game data — use web_search

## Answering spec questions
1. Call get_channel_pins to read the pinned spec.
2. Call get_guild_events to get the upcoming event list.
3. Compare the series name in the pinned spec against the upcoming events:
   - If an upcoming event matches the same series, the spec is current — even if the pin is weeks old. Specs are often valid for an entire multi-week series.
   - If no upcoming event matches the series, note that the spec may be from a completed series and the next event's spec hasn't been posted yet.
   - If you cannot determine a match, present the pinned spec as-is without speculating.
4. Only call get_recent_messages if the pin does not fully answer the question. Organizers post clarifications and rule updates in chat that don't make it into pins — if something is missing or ambiguous, check messages next.
   - When you do call get_recent_messages, extract the [Pinned: YYYY-MM-DD] date from the most recent matching pin and pass it as after_date. This limits results to post-pin messages and keeps token usage low.

## Answering schedule questions
Call get_guild_events first. Use get_channel_pins or get_recent_messages only to fill in spec details for a listed event.

When reporting event times, reproduce the <t:UNIX:F> timestamp tags exactly as returned — do not paraphrase or convert them to plain text. Discord renders these tags in each user's local timezone.

## Game source priority
When a Channel Category is provided, use it to infer which game is being discussed:
- "Gran Turismo", "GT7", or similar → Gran Turismo 7. Search gran-turismo.com first, then gtplanet.net or gt7.fandom.com as fallback.
- "Forza", "Forza Motorsport", or similar → Forza Motorsport. Search forzamotorsport.net first, then forza.fandom.com as fallback.
- If the category doesn't map to a known game or is absent, ask the user to clarify which game they mean, or search broadly.

Be concise and direct. If the answer isn't in the spec or schedule, say so clearly. Do not guess tuning rules.

## Passive messages
Some messages reach you without a direct @mention — the bot detected them as potentially relevant. If the message turns out to be casual racing chat (a race incident, a reaction, banter) rather than an actual spec or rules question, respond with only: SKIP

For passive messages that are genuine questions, exhaust local sources first — pins, events, and channel history. Only call web_search if the answer cannot be found there. Do not search speculatively."""


GT7_GLOSSARY = """## Shorthand glossary (Gran Turismo 7)
- PP: Performance Points — the in-game performance rating used to gate cars into a race spec.
- BOP: Balance of Performance — fixed power/weight adjustments applied to equalize cars within a class.
- Gr.1: top-tier prototype/LMP class. Gr.2: touring/super GT class. Gr.3: GT3-equivalent class. Gr.4: GT4-equivalent class. Gr.B: rally class. Gr.X: special/concept cars, no fixed class.
- N100/N200/N300/N400/N500/N600/N700: Normalized PP limits — race specs that cap PP at the stated value (e.g. N300 = max 300 PP).
- Tire compounds — Comfort: CH (Hard), CM (Medium), CS (Soft). Sport: SH (Hard), SM (Medium), SS (Soft). Racing: RH (Hard), RM (Medium), RS (Soft), RI (Intermediate), RW (Wet). Dirt: DT."""

FORZA_GLOSSARY = """## Shorthand glossary (Forza Motorsport)
- PI: Performance Index — numeric 0–999 rating used to class cars; classes are D (100–500), C (501–600), B (601–700), A (701–800), S1 (801–900), S2 (901–998), X (999).
- Tire compounds: ST = Street, SP = Sport, SE = Semi-Slick, SL = Slick, VT = Vintage, OF = Off-Road.
- Homologation: restricting a car's upgrades to a defined period-correct parts list, used in some league specs to prevent optimal min-maxing."""


def build_agent(tools=None):
    if tools is None:
        tools = [get_channel_pins, get_recent_messages, get_guild_events, web_search]
    model = InferenceClientModel("Qwen/Qwen2.5-72B-Instruct")
    return ToolCallingAgent(tools=tools, model=model, max_steps=5)


def _glossary_for_category(category_name: str | None) -> str:
    if not category_name:
        return ""
    cat = category_name.upper()
    if "GRAN TURISMO" in cat or "GT7" in cat:
        return "\n\n" + GT7_GLOSSARY
    if "FORZA" in cat:
        return "\n\n" + FORZA_GLOSSARY
    return ""


def ask(agent, question: str, channel_id: str, guild_id: str, category_name: str | None = None, thread_history: str | None = None) -> str:
    category_line = f"Channel Category: {category_name}\n" if category_name else ""
    glossary = _glossary_for_category(category_name)
    history_section = f"\nConversation so far:\n{thread_history}\n" if thread_history else ""
    prompt = (
        f"{SYSTEM_PROMPT}{glossary}\n\n"
        f"Channel ID: {channel_id}\n"
        f"Guild ID: {guild_id}\n"
        f"{category_line}"
        f"{history_section}"
        f"\nQuestion: {question}"
    )
    try:
        return agent.run(prompt)
    except Exception as exc:
        logger.error("agent.run failed: %s", exc, exc_info=True)
        return "I'm having trouble reaching my reasoning engine right now. Please try again in a moment."
