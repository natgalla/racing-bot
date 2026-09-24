import logging
import os
from smolagents import ToolCallingAgent, InferenceClientModel
from tools.discord_tools import get_channel_pins, get_recent_messages, get_guild_events, read_image_content
from tools.search_tools import web_search

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful sim racing Discord bot assistant. Answer questions about:
- The current race spec (car list, tuning rules)
- The race schedule and upcoming events
- Gran Turismo 7 or Forza Motorsport cars, tunes, and game data — use web_search

## Passive messages (no @mention)
When the message is marked as passive, your default is SKIP. Only respond if you are confident the message is a genuine question directed at the bot that you can actually answer.

Always SKIP when:
- The message is directed at another person, even if it mentions a racing topic (e.g. "hence me asking how to add oversteer every single week" — that's a complaint to a human, not a question for you)
- The message is meta-commentary about the bot itself (e.g. "let's see how many ways we can trigger this")
- The message is a joke, rhetorical aside, or frustrated remark
- The message is banter, a race incident reaction, or general chat
- You are not confident it's a genuine question for you

When in doubt, SKIP. A missed question is better than an unwanted reply.
Call final_answer with the single word SKIP — do not call any other tools first.

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

## Passive message source priority
For passive messages that pass the SKIP check, exhaust local sources first — pins, events, and channel history. Only call web_search if the answer cannot be found there. Do not search speculatively."""


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

HANDICAP_CHANNEL = "le-club-des-petits-gâteaux"

HANDICAP_SYSTEM = """## Handicap points formula

Points earned per race determine car upgrades or downgrades for the next race.
Middle finishers earn 0 points. Points outside ±3 mean no car adjustment.

≤6 finishers:  1st = +1 | Last = -1
7–9 finishers: 1st = +2, 2nd = +1 | Next-to-last = -1, Last = -2
10–13 finishers: 1st = +3, 2nd = +2, 3rd = +1 | Third-from-last = -1, Next-to-last = -2, Last = -3
14+ finishers: 1st = +4, 2nd = +3, 3rd = +2, 4th = +1 | Fourth-from-last = -1, Third-from-last = -2, Next-to-last = -3, Last = -4

Positive points (+) = downgrade (weight added or power reduced — car becomes slower)
Negative points (-) = upgrade (weight removed or power added — car becomes faster)

The specific weight/power adjustment for each point level (+1, +2, +3, +4, -1, -2, -3, -4) is posted as a screenshot in the channel pins. Call read_image_content on any [Image attachment: ...] URL returned by get_channel_pins to get the actual values."""

HANDICAP_INSTRUCTIONS = """## Answering handicap questions
1. Call get_channel_pins to find two things: (a) the race spec pin, which contains the canonical base weight and power for the current car; (b) the handicap pin containing the upgrade/downgrade adjustment table. Both may be image attachments — call read_image_content on any [Image attachment: <url>] lines to extract them.
2. Call get_recent_messages to find the weekly standings screenshot. Look for the most recent message within the past week that contains "#standings" and an [Image attachment: <url>]. Call read_image_content on that URL to extract each driver's current +/- total. If no #standings message is found, tell the user the current standings haven't been posted yet and ask them to have the organizer post the screenshot with #standings in the caption.
   - The asking user's Discord username is provided above. Use it to find their entry automatically via partial/fuzzy match (e.g. "Driver_B" matches "Driver_B") — do not ask them to provide their name. Only ask for clarification if multiple entries are a plausible match.
3. Calculate the driver's exact target settings:
   - Look up their +/- total in the adjustment table to get the weight change % and power change %.
   - Apply those percentages to the canonical base weight and power from the spec.
   - Present the final weight in both lbs and kg (divide lbs by 2.205), and final power in both hp and kW (multiply hp by 0.7457).
   - Be explicit: "Set your ballast/weight to X lbs (Y kg) and your power to Z hp (W kW).\""""


def build_agent(tools=None):
    if tools is None:
        tools = [get_channel_pins, get_recent_messages, get_guild_events, web_search, read_image_content]
    model = InferenceClientModel("Qwen/Qwen2.5-72B-Instruct")
    return ToolCallingAgent(tools=tools, model=model, max_steps=10)


def _glossary_for_category(category_name: str | None) -> str:
    if not category_name:
        return ""
    cat = category_name.upper()
    if "GRAN TURISMO" in cat or "GT7" in cat:
        return "\n\n" + GT7_GLOSSARY
    if "FORZA" in cat:
        return "\n\n" + FORZA_GLOSSARY
    return ""


def ask(agent, question: str, channel_id: str, guild_id: str, category_name: str | None = None, thread_history: str | None = None, is_mention: bool = True, author_username: str | None = None, channel_name: str | None = None) -> str:
    category_line = f"Channel Category: {category_name}\n" if category_name else ""
    glossary = _glossary_for_category(category_name)
    history_section = f"\nConversation so far:\n{thread_history}\n" if thread_history else ""
    passive_line = "Message type: passive (no @mention — apply SKIP gate)\n" if not is_mention else ""
    author_line = f"Asking user's Discord username: {author_username}\n" if author_username else ""
    is_handicap_channel = channel_name == HANDICAP_CHANNEL
    handicap_section = f"\n\n{HANDICAP_INSTRUCTIONS}\n\n{HANDICAP_SYSTEM}" if is_handicap_channel else ""
    prompt = (
        f"{SYSTEM_PROMPT}{glossary}"
        f"{handicap_section}\n\n"
        f"Channel ID: {channel_id}\n"
        f"Guild ID: {guild_id}\n"
        f"{category_line}"
        f"{passive_line}"
        f"{author_line}"
        f"{history_section}"
        f"\nQuestion: {question}"
    )
    try:
        return agent.run(prompt)
    except Exception as exc:
        logger.error("agent.run failed: %s", exc, exc_info=True)
        return "I'm having trouble reaching my reasoning engine right now. Please try again in a moment."
