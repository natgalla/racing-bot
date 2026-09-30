import asyncio
import datetime
import functools
import logging
import logging.handlers
import os
import re
import discord
from dotenv import load_dotenv
from agent import ask, complication_message, failure_message
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


_MESSAGES_TO_DELETE = {1554992537935159510}


async def _cleanup_on_start():
    cutoff = discord.utils.utcnow() - datetime.timedelta(hours=1)
    for guild in client.guilds:
        for channel in guild.text_channels:
            try:
                for thread in channel.threads:
                    if (thread.owner_id == client.user.id
                            and thread.created_at >= cutoff
                            and thread.message_count == 0):
                        await thread.delete()
                        logger.info("startup cleanup: deleted empty thread id=%s", thread.id)
            except discord.HTTPException:
                pass
            search_spaces = [channel] + list(channel.threads)
            for space in search_spaces:
                for msg_id in _MESSAGES_TO_DELETE:
                    try:
                        msg = await space.fetch_message(msg_id)
                        if msg.author.id == client.user.id:
                            await msg.delete()
                            logger.info("startup cleanup: deleted message id=%s", msg_id)
                    except (discord.NotFound, discord.HTTPException):
                        pass


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await _cleanup_on_start()


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


async def _retry_ask(send, question, channel_id, guild_id, category_name, thread_history, is_mention, author_username, channel_name):
    await asyncio.sleep(240)
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None, functools.partial(ask, question, channel_id, guild_id, category_name, thread_history, is_mention, author_username, channel_name)
        )
        if response.strip().upper() != "SKIP":
            await send(response.strip() + " 🤖")
    except Exception as exc:
        logger.error("retry failed: %s", exc, exc_info=True)
        await send(failure_message())


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
        try:
            response = await loop.run_in_executor(
                None, functools.partial(ask, question, str(message.channel.id), None, None, thread_history, True, message.author.name, None)
            )
        except Exception as exc:
            logger.error("agent invoked dm=True failed: %s", exc, exc_info=True)
            await message.reply(complication_message())
            asyncio.create_task(_retry_ask(message.reply, question, str(message.channel.id), None, None, thread_history, True, message.author.name, None))
            return
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
        _passive_thread = []

        async def send(content):
            if not _passive_thread:
                try:
                    _passive_thread.append(await message.create_thread(name=question[:100]))
                except discord.HTTPException:
                    _passive_thread.append(None)
            t = _passive_thread[0]
            return await (t.send(content) if t else message.reply(content))

        logger.info("agent invoked score=%.3f channel=%s", score, channel_name)
        try:
            response = await loop.run_in_executor(
                None, functools.partial(ask, question, str(message.channel.id), str(message.guild.id), category_name, thread_history, False, message.author.name, channel_name)
            )
        except Exception as exc:
            logger.error("agent invoked score=%.3f channel=%s failed: %s", score, channel_name, exc, exc_info=True)
            await send(complication_message())
            asyncio.create_task(_retry_ask(send, question, str(message.channel.id), str(message.guild.id), category_name, thread_history, False, message.author.name, channel_name))
            return
        if response.strip().upper() == "SKIP":
            logger.info("response=SKIP score=%.3f channel=%s", score, channel_name)
            return
        response = response.strip() + " 🤖"
        sent = await send(response)
        logger.info("response=sent score=%.3f message_id=%s channel=%s content=%s", score, sent.id, channel_name, response)
    else:
        try:
            thread = await message.create_thread(name=question[:100])
            send = thread.send
        except discord.HTTPException:
            send = message.reply
            thread = None
        try:
            async with (thread or message.channel).typing():
                logger.info("agent invoked channel=%s", channel_name)
                response = await loop.run_in_executor(
                    None, functools.partial(ask, question, str(message.channel.id), str(message.guild.id), category_name, thread_history, True, message.author.name, channel_name)
                )
        except Exception as exc:
            logger.error("agent invoked channel=%s failed: %s", channel_name, exc, exc_info=True)
            await send(complication_message())
            asyncio.create_task(_retry_ask(send, question, str(message.channel.id), str(message.guild.id), category_name, thread_history, True, message.author.name, channel_name))
            return
        response = response.strip() + " 🤖"
        sent = await send(response)
        logger.info("response=sent message_id=%s channel=%s content=%s", sent.id, channel_name, response)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == client.user.id:
        return
    channel = client.get_channel(payload.channel_id)
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
