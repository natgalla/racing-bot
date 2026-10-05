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
from classifier_jev import classify_score, THRESHOLD as _RELEVANCE_THRESHOLD

_log_fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
_file_handler = logging.handlers.RotatingFileHandler("bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
_file_handler.setFormatter(_log_fmt)
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_log_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _stream_handler])
logger = logging.getLogger(__name__)

load_dotenv()

OWNER_ID = int(os.environ.get("OWNER_ID", 0))
HANDICAP_CHANNEL_ID = os.environ.get("HANDICAP_CHANNEL_ID", "")
_pending_approvals: dict[int, dict] = {}
_agent_semaphore = asyncio.Semaphore(2)
_retry_tasks: set[asyncio.Task] = set()


def _thread_name(text: str) -> str:
    """Build a Discord-safe thread name: strip mentions/emoji tags and whitespace, truncate to 100 chars.

    Discord rejects empty or whitespace-only names, so fall back to a default. Truncate after
    sanitizing so a trailing multi-byte sequence is not split mid-character.
    """
    cleaned = re.sub(r"<a?:[^:]+:\d+>|<@!?\d+>|<#\d+>|<@&\d+>", "", text).strip()
    return cleaned[:100] if cleaned else "Question"


def _is_mention(message, user) -> bool:
    """True if the bot is @mentioned in the message.

    Checks the parsed mentions list and falls back to raw content for the plain
    (<@id>) and nickname (<@!id>) mention forms, since the parsed list can miss
    mentions in some message states.
    """
    if user is None:
        return False
    if user in message.mentions:
        return True
    return f"<@{user.id}>" in message.content or f"<@!{user.id}>" in message.content

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def _cleanup_on_start():
    if client.user is None:
        return
    cutoff = discord.utils.utcnow() - datetime.timedelta(hours=1)
    for guild in client.guilds:
        for channel in guild.text_channels:
            try:
                # channel.threads is discord.py's in-memory cache of active threads — a plain
                # attribute read, not a REST call, so this loop does not hit the network.
                for thread in channel.threads:
                    if (thread.owner_id == client.user.id
                            and thread.created_at >= cutoff
                            and thread.message_count == 0):
                        await thread.delete()
                        logger.info("startup cleanup: deleted empty thread id=%s", thread.id)
            except discord.HTTPException:
                pass


@client.event
async def on_ready():
    logger.info("Logged in as %s", client.user)
    await _cleanup_on_start()


async def fetch_thread_history(channel, bot_user_id, limit=10, max_age=None):
    messages = []
    async for m in channel.history(limit=limit + 1, oldest_first=False):
        messages.append(m)
    prior = list(reversed(messages[1:]))
    if max_age is not None:
        cutoff = discord.utils.utcnow() - max_age
        prior = [m for m in prior if m.created_at >= cutoff]
    if not prior:
        return None
    lines = []
    for m in prior:
        role = "Assistant" if m.author.id == bot_user_id else "User"
        content = m.content.replace(f"<@{bot_user_id}>", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else None


async def _retry_ask(send, question, channel_id, guild_id, category_name, thread_history, is_mention, author_username, channel_name, is_dm=False):
    await asyncio.sleep(240)
    loop = asyncio.get_running_loop()
    try:
        async with _agent_semaphore:
            response = await loop.run_in_executor(
                None,
                functools.partial(
                    ask,
                    question,
                    channel_id,
                    guild_id,
                    category_name=category_name,
                    thread_history=thread_history,
                    is_mention=is_mention,
                    author_username=author_username,
                    channel_name=channel_name,
                    is_dm=is_dm,
                ),
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
        thread_history = await fetch_thread_history(message.channel, client.user.id, limit=8, max_age=datetime.timedelta(hours=1))
        dm_channel_id = HANDICAP_CHANNEL_ID or str(message.channel.id)
        logger.info("agent invoked dm=True")
        try:
            async with _agent_semaphore:
                response = await loop.run_in_executor(
                    None,
                    functools.partial(
                        ask,
                        question,
                        dm_channel_id,
                        None,
                        thread_history=thread_history,
                        is_mention=True,
                        author_username=message.author.name,
                        is_dm=True,
                    ),
                )
        except Exception as exc:
            logger.error("agent invoked dm=True failed: %s", exc, exc_info=True)
            await message.reply(complication_message())
            _t = asyncio.create_task(_retry_ask(message.reply, question, dm_channel_id, None, None, thread_history, True, message.author.name, None, is_dm=True))
            _retry_tasks.add(_t)
            _t.add_done_callback(_retry_tasks.discard)
            return
        if response.strip().upper() == "SKIP":
            logger.info("response=SKIP dm=True")
            return
        response = response.strip() + " 🤖"
        sent = await message.reply(response)
        logger.info("response=sent dm=True message_id=%s content=%s", sent.id, response)
        return

    is_mention = _is_mention(message, client.user)

    channel_name = message.channel.parent.name if isinstance(message.channel, discord.Thread) else message.channel.name
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
        # Skip messages that are emoji-only (optionally with variation selectors,
        # ZWJ sequences, and whitespace). Ranges, all escaped so no raw bytes
        # are embedded in the pattern:
        #   \U0001F000-\U0001FFFF  supplemental symbols and pictographs (most emoji)
        #   \U00002600-\U000027BF  misc symbols and dingbats
        #   \U0000FE00-\U0000FE0F  variation selectors (e.g. emoji-style presentation)
        #   \U0000200D             zero-width joiner (binds emoji sequences)
        #   \U000020E3             combining enclosing keycap
        if re.fullmatch(
            r"[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0000FE00-\U0000FE0F\U0000200D\U000020E3\s]+",
            stripped,
        ):
            return
        score = await loop.run_in_executor(None, classify_score, message.content)
        relevant = score >= _RELEVANCE_THRESHOLD
        logger.info("classifier verdict=%s score=%.3f channel=%s", relevant, score, channel_name)
        if not relevant:
            return

    question = message.content.replace(f"<@{client.user.id}>", "").strip()
    question_anchor = message  # message that the thread/reply will attach to
    if not question and message.reference is not None:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            question = re.sub(r"<a?:[^:]+:\d+>|<@!?\d+>|<#\d+>|<@&\d+>", "", ref_msg.content).strip()
            if question:
                question_anchor = ref_msg
        except discord.HTTPException:
            pass
    if not question:
        await message.reply("I'm here if you need help with the race spec, schedule, or any GT7 questions. 🤖")
        return

    thread_history = None
    if isinstance(message.channel, discord.Thread):
        thread_history = await fetch_thread_history(message.channel, client.user.id)

    channel = message.channel
    category_name = channel.category.name if channel.category else None

    if not is_mention:
        _passive_thread = []

        async def send(content):
            if not _passive_thread:
                try:
                    _passive_thread.append(await message.create_thread(name=_thread_name(question)))
                except discord.HTTPException:
                    _passive_thread.append(None)
            t = _passive_thread[0]
            return await (t.send(content) if t else message.reply(content))

        logger.info("agent invoked score=%.3f channel=%s", score, channel_name)
        try:
            async with _agent_semaphore:
                response = await loop.run_in_executor(
                    None,
                    functools.partial(
                        ask,
                        question,
                        str(message.channel.id),
                        str(message.guild.id),
                        category_name=category_name,
                        thread_history=thread_history,
                        is_mention=False,
                        author_username=message.author.name,
                        channel_name=channel_name,
                    ),
                )
        except Exception as exc:
            logger.error("agent invoked score=%.3f channel=%s failed: %s", score, channel_name, exc, exc_info=True)
            return
        if response.strip().upper() == "SKIP":
            logger.info("response=SKIP score=%.3f channel=%s", score, channel_name)
            return
        response = response.strip() + " 🤖"
        if OWNER_ID:
            try:
                owner = await client.fetch_user(OWNER_ID)
                dm_content = f"**Passive response pending** — #{channel_name}\n> {question[:200]}\n\n{response}"
                dm_msg = await owner.send(dm_content)
                await dm_msg.add_reaction("✅")
                await dm_msg.add_reaction("❌")
                _pending_approvals[dm_msg.id] = {"message": message, "response": response, "created_at": discord.utils.utcnow()}
                logger.info("response=pending_approval score=%.3f channel=%s", score, channel_name)
            except discord.HTTPException as exc:
                logger.error("approval DM failed, posting directly: %s", exc)
                sent = await send(response)
                logger.info("response=sent score=%.3f message_id=%s channel=%s content=%s", score, sent.id, channel_name, response)
        else:
            sent = await send(response)
            logger.info("response=sent score=%.3f message_id=%s channel=%s content=%s", score, sent.id, channel_name, response)
    else:
        try:
            thread = await question_anchor.create_thread(name=_thread_name(question))
            send = thread.send
        except discord.HTTPException:
            send = question_anchor.reply
            thread = None
        try:
            async with (thread or question_anchor.channel).typing():
                logger.info("agent invoked channel=%s", channel_name)
                async with _agent_semaphore:
                    response = await loop.run_in_executor(
                        None,
                        functools.partial(
                            ask,
                            question,
                            str(message.channel.id),
                            str(message.guild.id),
                            category_name=category_name,
                            thread_history=thread_history,
                            is_mention=True,
                            author_username=message.author.name,
                            channel_name=channel_name,
                        ),
                    )
        except Exception as exc:
            logger.error("agent invoked channel=%s failed: %s", channel_name, exc, exc_info=True)
            await send(complication_message())
            _t = asyncio.create_task(_retry_ask(send, question, str(message.channel.id), str(message.guild.id), category_name, thread_history, True, message.author.name, channel_name))
            _retry_tasks.add(_t)
            _t.add_done_callback(_retry_tasks.discard)
            return
        response = response.strip() + " 🤖"
        sent = await send(response)
        logger.info("response=sent message_id=%s channel=%s content=%s", sent.id, channel_name, response)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if client.user is None:
        return
    if payload.user_id == client.user.id:
        return

    # Evict stale pending approvals so the dict does not grow unbounded when the owner
    # never reacts — approvals older than 1 hour are no longer actionable.
    _approval_cutoff = discord.utils.utcnow() - datetime.timedelta(hours=1)
    for _mid in [mid for mid, e in _pending_approvals.items() if e["created_at"] < _approval_cutoff]:
        del _pending_approvals[_mid]

    if OWNER_ID and payload.user_id == OWNER_ID and payload.message_id in _pending_approvals:
        entry = _pending_approvals.pop(payload.message_id)
        orig_message = entry["message"]
        response = entry["response"]
        if str(payload.emoji) == "✅":
            try:
                thread = await orig_message.create_thread(name=_thread_name(orig_message.content))
                sent = await thread.send(response)
            except discord.HTTPException:
                try:
                    sent = await orig_message.reply(response)
                except discord.HTTPException as exc:
                    logger.error("approval post failed: %s", exc)
                    return
            logger.info("approval=accepted message_id=%s channel=%s", sent.id, getattr(orig_message.channel, "name", "unknown"))
        else:
            logger.info("approval=rejected channel=%s", getattr(orig_message.channel, "name", "unknown"))
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
