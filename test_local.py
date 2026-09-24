import argparse
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from smolagents import tool

from agent import ask
from classifier import classify_score, _THRESHOLD
from tools.gtdb_cache import force_refresh_list
from tools.handicap_tools import calculate_handicap_settings
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

MOCK_HANDICAP_PIN = """[Spec handicap package: detunes + up-tunes]
[Image attachment: https://cdn.discordapp.com/attachments/mock/detunes.png]
[Image attachment: https://cdn.discordapp.com/attachments/mock/uptunes.png]"""

MOCK_DETUNE_TEXT = """\
Downgrades (positive points — car becomes slower)
+/-   Weight Added %    Weight      Power %    HP
+4    4%                3,120 lbs   —          450 hp
+5    5%                3,150 lbs   —          450 hp
+6    6%                3,180 lbs   —          450 hp
+7    7%                3,210 lbs   —          450 hp
+8    8%                3,240 lbs   —          450 hp
+9    9%                3,270 lbs   —          450 hp
+10   10%               3,300 lbs   —          450 hp
+11   10%               3,300 lbs   -2%        441 hp
+12   10%               3,300 lbs   -4%        432 hp
+13+  10% (capped)      3,300 lbs   -6%+       continues dropping"""

MOCK_UPTUNE_TEXT = """\
Upgrades (negative points — car becomes faster)
+/-   Weight Removed %   Weight      Power %    HP
-4    4%                 2,880 lbs   —          450 hp
-5    5%                 2,850 lbs   —          450 hp
-6    6%                 2,820 lbs   —          450 hp
-7    7%                 2,790 lbs   —          450 hp
-8    8%                 2,760 lbs   —          450 hp
-9    9%                 2,730 lbs   —          450 hp
-10   10%                2,700 lbs   —          450 hp
-11   10%                2,700 lbs   +2%        459 hp
-12   10%                2,700 lbs   +4%        468 hp
-13+  10% (capped)       2,700 lbs   +6%+       continues climbing"""

MOCK_STANDINGS_TEXT = """\
Drivers          +/-
Driver_A           13
Driver_B   3
Driver_C         -2
Driver_D       -1
Driver_E      -8
Driver_F            4
Driver_G     1
Driver_H     5
Driver_I        2
Driver_J  -11
Driver_K           -2"""

_next_friday = (datetime.now(tz=timezone.utc) + timedelta(days=7)).replace(
    hour=1, minute=0, second=0, microsecond=0
)
MOCK_EVENT_UNIX = int(_next_friday.timestamp())

MOCK_EVENTS = f"Friday Night Lights — <t:{MOCK_EVENT_UNIX}:F> (SCHEDULED): Weekly sim racing event. Spec 01: Toyota Mark II/Chaser 450HP Sports Medium. Spec 02: Production Supertrucks on Sports Soft."

MOCK_MESSAGES = """[20:00] Organizer: #standings [Image attachment: https://cdn.discordapp.com/attachments/mock/standings.png]
[22:12] Organizer: Alright folksies.
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
[00:15] Organizer: F-150 SVT Raptor '11 🌶️🌶️🌶️
This car needs to be swapped to the Windsor-351-Maverick unit for 250,000 Credits.
In GT Auto, you may add custom parts. But you may not change the body or wheelbase:
NO Widebody
NO Wide Offset Wheels
NO Increase to Body Rigidity
Be very sure you get all the settings correct. While not necessary, I suggest you practice a little bit. These are not easy to drive; there will be carnage!
[00:22] Organizer: Tundra TRD Pro '19 🌶️🌶️
This car needs to be swapped to the Demon-Challenger unit for 200,000 Credits.
In GT Auto, you may add custom parts. But you may not change the body or wheelbase:
NO Widebody
NO Wide Offset Wheels
NO Increase to Body Rigidity
Be very sure you get all the settings correct. While not necessary, I suggest you practice a little bit. These are not easy to drive; there will be carnage!
Update found in testing: Set transmission to "270".
[03:04] Organizer: The Lobby will open September 4, 2026 at 8:30 PM
[11:46] Driver1: @Organizer nearly rwd, soft as puppy shit suspension, you really love us hey?
[12:06] Driver2: I'm kind of here for some out-of-the-box, unhinged nonsense
[12:06] Driver1: It'll be fun
[12:18] Organizer: How about you take a practice lap? You might love me back.
[12:23] Driver1: I'm doing that right now. I think this is the first thing that's made me feel sick in VR. FYI the Raptor will roll at Alsace Test track
[15:00] Driver3: Just got mine set up and im taking it into some public lobbies to test it lmfao
[15:25] Driver3: Jesus
[15:26] Driver1: Can't save you in these trucks
[15:27] Driver3: Also FYI the tundra will probably do a front flip if you brake too hard coming to flugplatz. Did a hard brake and I did an endo
[15:59] Driver1: Sophy cannot drive these trucks lol. I did a 5 lapper at brands Hatch. I started in 20th and ended up lapping half of the field. So much carnage
[16:24] Driver3: Lmao I tried it out to see what it was like and im not disappointed. Pretty much just cruised my way to 1st
[16:28] Driver1: Yeah, that was my experience"""


MOCK_GTDB_CAR = """Nissan 180SX Type X '96
PP: 465.26 | Group: Gr.N | Drivetrain: FR | Aspiration: T
Power: 203 BHP / 6000 rpm | Torque: 27.9 kgfm / 4000 rpm
Weight: 1,220 kg | Displacement: 1,998 cc
Tags: #Road Car
Acquisition: Used Cars — Cr. 49,500
Note: Available from the Used Cars dealer."""

MOCK_GTDB_SEARCH = """Nissan 180SX Type X '96 | PP: 465.26 | Drivetrain: FR | Weight: 1,220 kg | Tags: #Road Car
Nissan Silvia Spec-R Aero '02 | PP: 471.33 | Drivetrain: FR | Weight: 1,240 kg | Tags: #Road Car"""


@tool
def mock_get_car_specs(car_name: str) -> str:
    """Return full specs and acquisition info for a Gran Turismo 7 car by name. Call this whenever a user asks about a specific car's stats, performance points, drivetrain, power, weight, group class, or how to acquire it in GT7. Prefers this over web_search for GT7 car data.

    Args:
        car_name: The name of the car to look up, e.g. "180SX Type X '96" or "Nissan 180SX".
            Fuzzy matching is applied so partial names and minor typos are tolerated.
    """
    return MOCK_GTDB_CAR


@tool
def mock_search_cars(filters: str) -> str:
    """Search Gran Turismo 7 cars by performance and spec filters. Call this when a user wants to find cars within a PP range, by drivetrain layout, weight, power, group class, or tag category. Returns a list of matching cars with key stats.

    Args:
        filters: A JSON string containing one or more filter keys. All keys are optional.
            Supported keys:
              pp_min (float) — minimum Performance Points, e.g. 450.0
              pp_max (float) — maximum Performance Points, e.g. 500.0
              weight_max (int, kg) — maximum car weight in kilograms, e.g. 1200
              power_min (int, BHP) — minimum power output in BHP, e.g. 300
              drivetrain (str) — layout code: "FR", "MR", "FF", or "4WD"
              tags (list of str) — one or more tag strings the car must have, e.g. ["#Road Car"]
              group (str) — race group: "Gr.1", "Gr.2", "Gr.3", "Gr.4", "Gr.B", "Gr.N", or "Gr.X"

            Example: '{"pp_min": 450, "pp_max": 500, "drivetrain": "FR", "tags": ["#Road Car"]}'
    """
    return MOCK_GTDB_SEARCH


@tool
def mock_get_channel_pins(channel_id: str, max_pins: int = 5) -> str:
    """Fetch pinned messages from a Discord channel. Use this first for spec questions — the current race spec is typically pinned.

    Each pin is preceded by a [Pinned: YYYY-MM-DD] header showing when it was pinned. Use this date
    as the after_date argument to get_recent_messages so only relevant post-pin chatter is fetched.

    Args:
        channel_id: The Discord channel ID to fetch pins from.
    """
    return f"[Pinned: 2026-08-27]\n{MOCK_PINS}\n\n---\n\n[Pinned: 2026-09-17]\n{MOCK_HANDICAP_PIN}"


@tool
def mock_read_image_content(image_url: str) -> str:
    """Extract text and table data from an image URL. Use this when get_channel_pins returns [Image attachment: <url>] lines — call it to read handicap tables or other image-based content from pinned messages.

    Args:
        image_url: The URL of the image to extract text from.
    """
    if "detunes" in image_url:
        return MOCK_DETUNE_TEXT
    if "uptunes" in image_url:
        return MOCK_UPTUNE_TEXT
    if "standings" in image_url:
        return MOCK_STANDINGS_TEXT
    return "Image content not available in mock mode."


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
def mock_get_guild_events(guild_id: str, series_name: str = "") -> str:
    """Fetch upcoming scheduled Discord events for this server. Use this for schedule/timing questions.

    Args:
        guild_id: The Discord guild (server) ID to fetch events from.
        series_name: Optional case-insensitive substring to filter events by name.
    """
    if series_name and series_name.lower() not in MOCK_EVENTS.lower():
        return f"No scheduled events found matching '{series_name}'."
    return MOCK_EVENTS



def main():
    parser = argparse.ArgumentParser(description="Test the sim racing bot locally.")
    parser.add_argument("question", help="Question to ask the bot")
    parser.add_argument("--classify", action="store_true", help="Print classifier score and exit without running the agent")
    parser.add_argument("--mock", action="store_true", help="Use mock Discord tools (real web search still runs)")
    parser.add_argument("--channel-id", default="000000000000000000", help="Discord channel ID")
    parser.add_argument("--guild-id", default="000000000000000000", help="Discord guild ID")
    parser.add_argument("--channel-name", default=None, help="Discord channel name (use 'le-club-des-petits-gâteaux' to test handicap path)")
    parser.add_argument("--author-username", default=None, help="Discord username of the asking user")
    parser.add_argument("--refresh-gtdb", action="store_true", help="Force-refresh the GT7 car list cache before running")
    args = parser.parse_args()

    load_dotenv()

    if args.refresh_gtdb:
        print("Refreshing GT7 car list cache from gtdb.io...")
        force_refresh_list()
        print("Done.\n")

    if args.classify:
        score = classify_score(args.question)
        verdict = "PASS" if score >= _THRESHOLD else "FAIL"
        print(f"Score: {score:.3f}  Threshold: {_THRESHOLD}  [{verdict}]")
        return

    if args.mock:
        print("Mode: MOCK (no Discord token required)\n")
        mock_tools = [
            mock_get_channel_pins,
            mock_get_recent_messages,
            mock_get_guild_events,
            web_search,
            mock_read_image_content,
            calculate_handicap_settings,
            mock_get_car_specs,
            mock_search_cars,
        ]
        response = ask(args.question, args.channel_id, args.guild_id, channel_name=args.channel_name, author_username=args.author_username, tools=mock_tools)
    else:
        if not os.environ.get("DISCORD_TOKEN"):
            print("Error: DISCORD_TOKEN not set. Copy .env.example to .env and fill it in, or use --mock.")
            raise SystemExit(1)
        print("Mode: LIVE (using real Discord API)\n")
        response = ask(args.question, args.channel_id, args.guild_id, channel_name=args.channel_name, author_username=args.author_username)
    print(response)


if __name__ == "__main__":
    main()
