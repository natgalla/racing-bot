import argparse
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from smolagents import tool

from agent import build_agent, ask

MOCK_PINS = """Friday Night Lights SEP/4th
Spec 01:
Toyota Mark II Tourer (1997)
Toyota Mark V Chaser (1997)
Leave all settings default, except for power, making 450HP. How you reach that power figure (and how you customize the body) is up to you. Sports Medium Tires!

Spec 02:
Ford F-150 SVT Raptor (2011)
swapped! Windsor-351-Maverick (250,000 Cr.)
Toyota Tundra TRD Pro (2019)
swapped! Demon-Challenger (200,000 Cr.)
There are specific tunes for these trucks, what I am calling Production Supertrucks. You have your choice of "the full experience" (🌶️🌶️🌶️) or a more controllable option (🌶️🌶️)— which I recommend for those who aren't very confident on controller. You will need to engine swap these vehicles to make the power required; they are on Sports Soft tires. Trust in the tunes, I spent time on this!"""

_next_friday = (datetime.now(tz=timezone.utc) + timedelta(days=7)).replace(
    hour=1, minute=0, second=0, microsecond=0
)
MOCK_EVENT_TIME = _next_friday.strftime("%A, %B %d at %I:%M %p UTC")

MOCK_EVENTS = f"Friday Night Lights — {MOCK_EVENT_TIME} (SCHEDULED): Weekly sim racing event. Spec 01: Toyota Mark II/Chaser 450HP Sports Medium. Spec 02: Production Supertrucks on Sports Soft."

MOCK_MESSAGES = """[20:01] RaceOrg: Reminder — Friday Night Lights is this week! Get your tunes ready.
[20:03] Drivers: What tires for Spec 01?
[20:04] RaceOrg: Sports Medium for Spec 01, Sports Soft for Spec 02 (Production Supertrucks)."""


@tool
def mock_get_channel_pins(channel_id: str) -> str:
    """Fetch pinned messages from a Discord channel. Use this first for spec questions — the current race spec is typically pinned.

    Args:
        channel_id: The Discord channel ID to fetch pins from.
    """
    return MOCK_PINS


@tool
def mock_get_recent_messages(channel_id: str, limit: int = 20) -> str:
    """Fetch recent messages from a Discord channel. Use this if pinned messages don't have enough context, or if the spec may have been updated in a recent post.

    Args:
        channel_id: The Discord channel ID to fetch messages from.
        limit: Number of recent messages to fetch (default 20, max 100).
    """
    return MOCK_MESSAGES


@tool
def mock_get_guild_events(guild_id: str) -> str:
    """Fetch upcoming scheduled Discord events for this server. Use this for schedule/timing questions.

    Args:
        guild_id: The Discord guild (server) ID to fetch events from.
    """
    return MOCK_EVENTS


@tool
def mock_web_search(query: str) -> str:
    """Search the web for information about Gran Turismo 7 or Forza Motorsport — car lists, performance points, tuning limits, track availability, etc. Reliable sources include gtplanet.net, gran-turismo.com, gt7.fandom.com, forza.fandom.com, and forzamotorsport.net.

    Args:
        query: The search query string.
    """
    return f"[mock] Web search results for: {query}\nNo live results in mock mode."


def main():
    parser = argparse.ArgumentParser(description="Test the sim racing bot locally.")
    parser.add_argument("question", help="Question to ask the bot")
    parser.add_argument("--mock", action="store_true", help="Use mock tools (no Discord token required)")
    parser.add_argument("--channel-id", default="000000000000000000", help="Discord channel ID")
    parser.add_argument("--guild-id", default="000000000000000000", help="Discord guild ID")
    args = parser.parse_args()

    if args.mock:
        print("Mode: MOCK (no Discord token required)\n")
        agent = build_agent(tools=[
            mock_get_channel_pins,
            mock_get_recent_messages,
            mock_get_guild_events,
            mock_web_search,
        ])
    else:
        load_dotenv()
        if not os.environ.get("DISCORD_TOKEN"):
            print("Error: DISCORD_TOKEN not set. Copy .env.example to .env and fill it in, or use --mock.")
            raise SystemExit(1)
        print("Mode: LIVE (using real Discord API)\n")
        agent = build_agent()

    response = ask(agent, args.question, args.channel_id, args.guild_id)
    print(response)


if __name__ == "__main__":
    main()
