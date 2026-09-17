import argparse
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from smolagents import tool

from agent import build_agent, ask
from tools.search_tools import web_search

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

MOCK_MESSAGES = """[22:12] Can'tReachDriver_A: Alright folksies.
Friday Night Lights SEP/4th
Spec 01:
Toyota Mark II Tourer (1997)
Toyota Mark V Chaser (1997)
Leave all settings default, except for power, making 450HP. How you reach that power figure (and how you customize the body) is up to you. Sports Medium Tires!

Spec 02:
Ford F-150 SVT Raptor (2011)
swapped! Windsor-351-Maverick (250,000 Cr.)
Toyota Tundra TRD Pro (2019)
swapped! Demon-Challenger (200,000 Cr.)
There are specific tunes for these trucks, what I am calling Production Supertrucks. You have your choice of "the full experience" (🌶️🌶️🌶️) or a more controllable option (🌶️🌶️)— which I recommend for those who aren't very confident on controller. You will need to engine swap these vehicles to make the power required; they are on Sports Soft tires. Trust in the tunes, I spent time on this!
Image guide forthcoming
[00:15] Can'tReachDriver_A: F-150 SVT Raptor '11 🌶️🌶️🌶️
This car needs to be swapped to the Windsor-351-Maverick unit for 250,000 Credits.
In GT Auto, you may add custom parts. But you may not change the body or wheelbase:
NO Widebody
NO Wide Offset Wheels
NO Increase to Body Rigidity
Be very sure you get all the settings correct. While not necessary, I suggest you practice a little bit. These are not easy to drive; there will be carnage!
[00:22] Can'tReachDriver_A: Tundra TRD Pro '19 🌶️🌶️
This car needs to be swapped to the Demon-Challenger unit for 200,000 Credits.
In GT Auto, you may add custom parts. But you may not change the body or wheelbase:
NO Widebody
NO Wide Offset Wheels
NO Increase to Body Rigidity
Be very sure you get all the settings correct. While not necessary, I suggest you practice a little bit. These are not easy to drive; there will be carnage!
Update found in testing: Set transmission to "270".
[03:04] Can'tReachDriver_A: The Lobby will open September 4, 2026 at 8:30 PM
[11:46] riley: @Can'tReachDriver_A nearly rwd, soft as puppy shit suspension, you really love us hey?
[12:06] Driver_B: I'm kind of here for some out-of-the-box, unhinged nonsense
[12:06] riley: It'll be fun
[12:18] Can'tReachDriver_A: How about you take a practice lap? You might love me back.
[12:23] riley: I'm doing that right now. I think this is the first thing that's made me feel sick in VR. FYI the Raptor will roll at Alsace Test track
[15:00] Spag [FSM]: Just got mine set up and im taking it into some public lobbies to test it lmfao
[15:25] Spag [FSM]: Jesus
[15:26] riley: Can't save you in these trucks
[15:27] Spag [FSM]: Also FYI the tundra will probably do a front flip if you brake too hard coming to flugplatz. Did a hard brake and I did an endo
[15:59] riley: Sophy cannot drive these trucks lol. I did a 5 lapper at brands Hatch. I started in 20th and ended up lapping half of the field. So much carnage
[16:24] Spag [FSM]: Lmao I tried it out to see what it was like and im not disappointed. Pretty much just cruised my way to 1st
[16:28] riley: Yeah, that was my experience"""


@tool
def mock_get_channel_pins(channel_id: str) -> str:
    """Fetch pinned messages from a Discord channel. Use this first for spec questions — the current race spec is typically pinned.

    Each pin is preceded by a [Pinned: YYYY-MM-DD] header showing when it was pinned. Use this date
    as the after_date argument to get_recent_messages so only relevant post-pin chatter is fetched.

    Args:
        channel_id: The Discord channel ID to fetch pins from.
    """
    return f"[Pinned: 2026-08-27]\n{MOCK_PINS}"


@tool
def mock_get_recent_messages(channel_id: str, limit: int = 20, after_date: str = "") -> str:
    """Fetch recent messages from a Discord channel. Use this if pinned messages don't have enough context, or if the spec may have been updated in a recent post.

    Args:
        channel_id: The Discord channel ID to fetch messages from.
        limit: Number of recent messages to fetch (default 20, max 100).
        after_date: Optional ISO date string (e.g. "2026-08-27"). When provided, only messages
            from that date onward are returned (date comparison only — messages on that same day
            are included). Use the [Pinned: YYYY-MM-DD] date from get_channel_pins so that
            pre-event chatter from prior sessions does not pollute the context.
    """
    # Mock messages carry [HH:MM] timestamps without dates — treat them all as 2026-08-27.
    # Include them when after_date is 2026-08-27 or earlier; exclude all if after_date is later.
    if after_date:
        try:
            filter_date = datetime.fromisoformat(after_date).date()
            mock_date = datetime(2026, 8, 27).date()
            if filter_date > mock_date:
                return "No messages found after the specified date."
        except ValueError:
            pass
    return MOCK_MESSAGES


@tool
def mock_get_guild_events(guild_id: str) -> str:
    """Fetch upcoming scheduled Discord events for this server. Use this for schedule/timing questions.

    Args:
        guild_id: The Discord guild (server) ID to fetch events from.
    """
    return MOCK_EVENTS



def main():
    parser = argparse.ArgumentParser(description="Test the sim racing bot locally.")
    parser.add_argument("question", help="Question to ask the bot")
    parser.add_argument("--mock", action="store_true", help="Use mock Discord tools (real web search still runs)")
    parser.add_argument("--channel-id", default="000000000000000000", help="Discord channel ID")
    parser.add_argument("--guild-id", default="000000000000000000", help="Discord guild ID")
    args = parser.parse_args()

    load_dotenv()

    if args.mock:
        print("Mode: MOCK (no Discord token required)\n")
        agent = build_agent(tools=[
            mock_get_channel_pins,
            mock_get_recent_messages,
            mock_get_guild_events,
            web_search,
        ])
    else:
        if not os.environ.get("DISCORD_TOKEN"):
            print("Error: DISCORD_TOKEN not set. Copy .env.example to .env and fill it in, or use --mock.")
            raise SystemExit(1)
        print("Mode: LIVE (using real Discord API)\n")
        agent = build_agent()

    response = ask(agent, args.question, args.channel_id, args.guild_id)
    print(response)


if __name__ == "__main__":
    main()
