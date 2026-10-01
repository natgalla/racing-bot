"""
Standalone script to delete specific bot messages (and their parent threads) by message ID.
Run with: python delete_messages.py

Add message IDs to MESSAGES_TO_DELETE before running.
"""
import asyncio
import os
import discord
from dotenv import load_dotenv

load_dotenv()

MESSAGES_TO_DELETE = {
    # 1554992537935159510,  # hallucinated Thunderhill event — already deleted 2026-09-30
    # 1555022130876391486,  # failed to find standings/detune — content_type bug, fixed 2026-09-30
}

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    for guild in client.guilds:
        for channel in guild.text_channels:
            search_spaces = [channel] + list(channel.threads)
            for space in search_spaces:
                for msg_id in MESSAGES_TO_DELETE:
                    try:
                        msg = await space.fetch_message(msg_id)
                        if msg.author.id == client.user.id:
                            await msg.delete()
                            print(f"Deleted message {msg_id}")
                            if isinstance(space, discord.Thread):
                                await space.delete()
                                print(f"Deleted parent thread {space.id}")
                    except (discord.NotFound, discord.HTTPException):
                        pass
    await client.close()


client.run(os.environ["DISCORD_TOKEN"])
