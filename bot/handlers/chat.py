"""
General chat handler — when the user sends a message that isn't a command
or workout, personas respond naturally.

Logic:
- Message mentions a persona by name → that persona responds + maybe 1 other
- General message (hi, hey team, etc.) → 3-5 personas respond over time
- Other messages → 1-2 personas respond
- First response is always fast (30s-2min), rest staggered naturally
"""

import random
import asyncio
import re

from telegram import Update, Bot
from telegram.ext import ContextTypes

from logger import log
from config import Config
from db.connection import async_session
from db.queries.users import get_user_by_telegram_id
from db.queries.personas import get_all_personas
from llm.client import generate_message
from llm.prompts import SYSTEM_PROMPT


CHAT_RESPONSE_PROMPT = """You are {persona_name}, a member of a fitness accountability \
group chat on Telegram. Someone on your team just sent a message.

YOUR IDENTITY:
- Personality: {persona_personality}
- Emoji style: {persona_emoji_style}
- Speech patterns: {persona_slang_notes}
- Motivation style: {persona_motivation_style}

THE MESSAGE FROM {human_name}:
"{message_text}"

RECENT CHAT:
{recent_chat}

TASK: Write a short, natural reply (1-2 sentences). React like a real friend would \
in a group chat. If they said hi, say hi back warmly. If they shared something, \
respond to it. Match your persona's voice and style.

Keep it under 200 characters. Write ONLY the message text."""

# Patterns that suggest the user is greeting the whole team
GENERAL_GREETINGS = re.compile(
    r"\b(hi|hey|hello|helo|sup|yo|g'?day|morning|evening|afternoon|"
    r"everyone|team|squad|legends|guys|all)\b",
    re.IGNORECASE,
)

# Map persona names/nicknames to slugs for mention detection
PERSONA_NAMES = {
    "tash": "tash", "natasha": "tash", "tash murray": "tash",
    "damo": "damo", "damien": "damo", "damo reilly": "damo",
    "sam": "sam", "samuel": "sam", "sam taufa": "sam",
    "jake": "jake", "jacob": "jake", "jake henderson": "jake",
    "mel": "mel", "melissa": "mel", "mel kovac": "mel",
}


def _detect_mentioned_persona(text: str) -> str | None:
    """Check if the message mentions a specific persona by name."""
    lower = text.lower()
    for name, slug in PERSONA_NAMES.items():
        if name in lower:
            return slug
    return None


def _is_general_greeting(text: str) -> bool:
    """Check if this is a broad greeting to the team."""
    return bool(GENERAL_GREETINGS.search(text))


async def general_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle general text messages — trigger persona responses."""
    text = update.message.text.strip()
    if not text or len(text) < 2:
        return

    # Check if user exists
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.onboarding_complete:
            await update.message.reply_text(
                "Hey! Use /start to set up your squad first 💪"
            )
            return

    # Schedule persona responses
    asyncio.create_task(_respond_to_chat(
        update.effective_chat.id,
        update.effective_user.id,
        text,
    ))


async def _respond_to_chat(chat_id: int, user_telegram_id: int, message_text: str):
    """Route message to appropriate response strategy."""
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, user_telegram_id)
        if not user:
            return

        personas = await get_all_personas(session)
        if not personas:
            return

        persona_map = {p.slug: p for p in personas}

    mentioned = _detect_mentioned_persona(message_text)
    is_greeting = _is_general_greeting(message_text)

    main_bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)

    if mentioned and mentioned in persona_map:
        # Mentioned a specific persona → they respond fast, maybe +1 other
        primary = persona_map[mentioned]
        others = [p for p in personas if p.slug != mentioned]
        responders = [(primary, (30, 120))]  # 30s-2min
        if random.random() < 0.5 and others:
            extra = random.choice(others)
            responders.append((extra, (180, 600)))  # 3-10min
        log.info(f"Mentioned {mentioned} — {len(responders)} will respond")

    elif is_greeting:
        # General greeting → 3-5 personas respond over time
        random.shuffle(personas)
        num = random.randint(3, min(5, len(personas)))
        delay_ranges = [
            (30, 120),       # 30s-2min
            (120, 420),      # 2-7min
            (300, 900),      # 5-15min
            (600, 1800),     # 10-30min
            (1200, 3600),    # 20-60min
        ]
        responders = [
            (personas[i], delay_ranges[i])
            for i in range(num)
        ]
        log.info(f"General greeting — {num} personas will respond")

    else:
        # Other message → 1-2 personas respond
        random.shuffle(personas)
        num = random.choices([1, 2], weights=[0.5, 0.5], k=1)[0]
        delay_ranges = [
            (30, 180),     # 30s-3min
            (180, 600),    # 3-10min
        ]
        responders = [
            (personas[i], delay_ranges[i])
            for i in range(num)
        ]
        log.info(f"General message — {num} personas will respond")

    # Build recent chat context (simple for now)
    recent_chat = f"{user.first_name}: {message_text}"

    for persona, (min_delay, max_delay) in responders:
        delay = random.randint(min_delay, max_delay)
        log.info(f"[{persona.slug}] Will respond in {delay}s ({delay // 60}m {delay % 60}s)")

        await asyncio.sleep(delay)

        prompt = CHAT_RESPONSE_PROMPT.format(
            persona_name=persona.display_name,
            persona_personality=persona.personality,
            persona_emoji_style=persona.emoji_style,
            persona_slang_notes=persona.slang_notes,
            persona_motivation_style=persona.motivation_style,
            human_name=user.first_name,
            message_text=message_text,
            recent_chat=recent_chat,
        )

        response = await generate_message(SYSTEM_PROMPT, prompt, max_tokens=100)
        if not response:
            continue

        try:
            await main_bot.send_message(
                chat_id=chat_id,
                text=f"*{persona.display_name}*\n{response}",
                parse_mode="Markdown",
            )
            # Add to context for next responders
            recent_chat += f"\n{persona.display_name}: {response}"
            log.info(f"[{persona.slug}] Responded: {response[:60]}...")
        except Exception as e:
            log.error(f"[{persona.slug}] Failed to respond: {e}")
