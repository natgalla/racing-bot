import asyncio
import functools
import logging
import logging.handlers
import os
import re
import discord
from dotenv import load_dotenv
from agent import ask
from classifier_jev import classify_score, _THRESHOLD as _RELEVANCE_THRESHOLD

_log_fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
_file_handler = logging.handlers.RotatingFileHandler("bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
_file_handler.setFormatter(_log_fmt)
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_log_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _stream_handler])
logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


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

    _ch_name = message.channel.parent.name if isinstance(message.channel, discord.Thread) else message.channel.name
    loop = asyncio.get_running_loop()
    score = None

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
        score = await loop.run_in_executor(None, classify_score, message.content)
        relevant = score >= _RELEVANCE_THRESHOLD
        logger.info("classifier verdict=%s score=%.3f channel=%s", relevant, score, _ch_name)
        if not relevant:
            return

    question = message.content.replace(f"<@{client.user.id}>", "").strip()
    if not question:
        await message.reply("I'm here if you need help with the race spec, schedule, or any GT7 questions. 🤖")
        return

    thread_history = None
    if isinstance(message.channel, discord.Thread):
        thread_history = await fetch_thread_history(message.channel, client.user.id)

    channel = message.channel
    channel_name = channel.parent.name if isinstance(channel, discord.Thread) else channel.name
    category_name = channel.category.name if channel.category else None

    if not is_mention:
        logger.info("agent invoked score=%.3f channel=%s", score, channel_name)
        response = await loop.run_in_executor(
            None, functools.partial(ask, question, str(message.channel.id), str(message.guild.id), category_name, thread_history, False, message.author.name, channel_name)
        )
        if response.strip().upper() == "SKIP":
            logger.info("response=SKIP score=%.3f channel=%s", score, channel_name)
            return
        response = response.strip() + " 🤖"
        logger.info("response=sent score=%.3f length=%d channel=%s", score, len(response), channel_name)
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
            logger.info("agent invoked channel=%s", channel_name)
            response = await loop.run_in_executor(
                None, functools.partial(ask, question, str(message.channel.id), str(message.guild.id), category_name, thread_history, True, message.author.name, channel_name)
            )
        response = response.strip() + " 🤖"
        logger.info("response=sent length=%d channel=%s", len(response), channel_name)
        await send(response)


client.run(os.environ["DISCORD_TOKEN"])
