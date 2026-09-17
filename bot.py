import asyncio
import os
import discord
from dotenv import load_dotenv
from agent import build_agent, ask

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
agent = build_agent()


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author.bot:
        return
    if client.user not in message.mentions:
        return

    question = message.content.replace(f"<@{client.user.id}>", "").strip()
    if not question:
        return

    thread = await message.create_thread(name=question[:100])
    async with thread.typing():
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, ask, agent, question, str(message.channel.id), str(message.guild.id)
        )
    await thread.send(response)


client.run(os.environ["DISCORD_TOKEN"])
