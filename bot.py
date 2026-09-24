import asyncio
import logging
import os
import re
import discord
from dotenv import load_dotenv
from agent import build_agent, ask
from classifier import classify_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
agent = build_agent()


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


async def fetch_thread_history(channel, bot_user_id, limit=10):
    messages = []
    async for m in channel.history(limit=limit + 1, oldest_first=False):
        messages.append(m)
    prior = list(reversed(messages[1:]))
    if not prior:
        return None
    lines = []
    for m in prior:
        role = "Assistant" if m.author.id == bot_user_id else "User"
        content = m.content.replace(f"<@{bot_user_id}>", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else None


@client.event
async def on_message(message):
    if message.author.bot:
        return

    is_mention = client.user in message.mentions

    if not is_mention:
        if message.channel.category is None or message.channel.category.name != "Gran Turismo 7":
            return
        if not message.content.strip():
            return
        if re.fullmatch(r"https?://\S+", message.content.strip()):
            return
        # strip Discord mentions and custom emoji tags, skip if nothing substantive remains
        stripped = re.sub(r"<a?:[^:]+:\d+>|<@!?\d+>|<#\d+>|<@&\d+>", "", message.content).strip()
        if not stripped:
            return
        if re.fullmatch(r"[\U0001F000-\U0001FFFF\U00002600-\U000027FF︀-️\s]+", stripped):
            return
        loop = asyncio.get_running_loop()
        score = await loop.run_in_executor(None, classify_score, message.content)
        relevant = score >= float(os.environ.get("RELEVANCE_THRESHOLD", "0.75"))
        logger.info("classifier verdict=%s score=%.3f message=%r", relevant, score, message.content[:80])
        if not relevant:
            return

    question = message.content.replace(f"<@{client.user.id}>", "").strip()
    if not question:
        await message.reply("I'm here if you need help with the race spec, schedule, or any GT7 questions. 🤖")
        return

    thread_history = None
    if isinstance(message.channel, discord.Thread):
        thread_history = await fetch_thread_history(message.channel, client.user.id)

    loop = asyncio.get_running_loop()
    category_name = message.channel.category.name if message.channel.category else None

    if not is_mention:
        async with message.channel.typing():
            logger.info("agent invoked channel=%s", message.channel.id)
            response = await loop.run_in_executor(
                None, ask, agent, question, str(message.channel.id), str(message.guild.id), category_name, thread_history, is_mention=False, author_username=message.author.username, channel_name=message.channel.name
            )
        if response.strip().upper() == "SKIP":
            logger.info("response suppressed (SKIP)")
            return
        response = response.strip() + " 🤖"
        logger.info("response sent channel=%s length=%d", message.channel.id, len(response))
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
            logger.info("agent invoked channel=%s", message.channel.id)
            response = await loop.run_in_executor(
                None, ask, agent, question, str(message.channel.id), str(message.guild.id), category_name, thread_history, is_mention=True, author_username=message.author.username, channel_name=message.channel.name
            )
        response = response.strip() + " 🤖"
        logger.info("response sent channel=%s length=%d", message.channel.id, len(response))
        await send(response)


client.run(os.environ["DISCORD_TOKEN"])
