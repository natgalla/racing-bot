import asyncio
import os
import discord
from dotenv import load_dotenv
from agent import build_agent, ask
from classifier import is_racing_relevant

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

    is_mention = client.user in message.mentions

    if not is_mention:
        if message.channel.category is None:
            return
        loop = asyncio.get_running_loop()
        relevant = await loop.run_in_executor(None, is_racing_relevant, message.content)
        if not relevant:
            return

    question = message.content.replace(f"<@{client.user.id}>", "").strip()
    if not question:
        return

    loop = asyncio.get_running_loop()
    category_name = message.channel.category.name if message.channel.category else None

    if not is_mention:
        async with message.channel.typing():
            response = await loop.run_in_executor(
                None, ask, agent, question, str(message.channel.id), str(message.guild.id), category_name
            )
        if response.strip() == "SKIP":
            return
        try:
            thread = await message.create_thread(name=question[:100])
            await thread.send(response)
        except discord.HTTPException:
            await message.reply(response)
    else:
        try:
            thread = await message.create_thread(name=question[:100])
            send = thread.send
        except discord.HTTPException:
            send = message.reply
            thread = None
        async with (thread or message.channel).typing():
            response = await loop.run_in_executor(
                None, ask, agent, question, str(message.channel.id), str(message.guild.id), category_name
            )
        await send(response)


client.run(os.environ["DISCORD_TOKEN"])
