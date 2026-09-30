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

    loop = asyncio.get_running_loop()

    if message.guild is None:
        # DM channel — skip classifier, category checks, and thread creation
        question = message.content.strip()
        if not question:
            return
        thread_history = await fetch_thread_history(message.channel, client.user.id)
        logger.info("agent invoked dm=True")
        response = await loop.run_in_executor(
            None, functools.partial(ask, question, str(message.channel.id), None, None, thread_history, True, message.author.name, None)
        )
        if response.strip().upper() == "SKIP":
            logger.info("response=SKIP dm=True")
            return
        response = response.strip() + " 🤖"
        sent = await message.reply(response)
        logger.info("response=sent dm=True message_id=%s content=%s", sent.id, response)
        return

    is_mention = client.user in message.mentions

    _ch_name = message.channel.parent.name if isinstance(message.channel, discord.Thread) else message.channel.name
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
        try:
            thread = await message.create_thread(name=question[:100])
            sent = await thread.send(response)
        except discord.HTTPException:
            sent = await message.reply(response)
        logger.info("response=sent score=%.3f message_id=%s channel=%s content=%s", score, sent.id, channel_name, response)
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
        sent = await send(response)
        logger.info("response=sent message_id=%s channel=%s content=%s", sent.id, channel_name, response)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == client.user.id:
        return
    channel = client.get_channel(payload.channel_id)
    if isinstance(channel, discord.DMChannel):
        return
    if channel is None:
        return
    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.HTTPException:
        return
    if message.author.id != client.user.id:
        return
    logger.info(
        "reaction emoji=%s message_id=%s channel=%s user_id=%s",
        str(payload.emoji),
        payload.message_id,
        getattr(channel, "name", "dm"),
        payload.user_id,
    )


client.run(os.environ["DISCORD_TOKEN"])
