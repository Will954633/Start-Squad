"""
General chat handler — when the user sends a message that isn't a command
or workout, have 1-2 personas respond naturally within a few minutes.
This makes the chat feel alive.
"""

import random
import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from logger import log
from db.connection import async_session
from db.queries.users import get_user_by_telegram_id
from db.queries.personas import get_all_personas
from db.queries.posts import get_channel_history
from bot.app import get_persona_bot
from llm.client import generate_message
from llm.prompts import SYSTEM_PROMPT
from llm.context import build_chat_history


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


async def general_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle general text messages — trigger persona responses."""
    text = update.message.text.strip()
    if not text or len(text) < 2:
        return

    # Check if user exists
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.onboarding_complete:
            # Not onboarded — prompt them
            await update.message.reply_text(
                "Hey! Use /start to set up your squad first 💪"
            )
            return

    # Schedule 1-2 persona responses with natural delays
    asyncio.create_task(_respond_to_chat(
        update.effective_chat.id,
        update.effective_user.id,
        text,
    ))


async def _respond_to_chat(chat_id: int, user_telegram_id: int, message_text: str):
    """Have 1-2 personas respond to a general chat message."""
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, user_telegram_id)
        if not user:
            return

        personas = await get_all_personas(session)
        if not personas:
            return

        # Pick 1-2 personas to respond
        num_responders = random.choices([1, 2], weights=[0.6, 0.4], k=1)[0]
        responders = random.sample(personas, min(num_responders, len(personas)))

        # Build recent chat context
        persona_names = {p.id: p.display_name for p in personas}

    for i, persona in enumerate(responders):
        # First responder: 1-5 min, second: 3-10 min
        if i == 0:
            delay = random.randint(60, 300)
        else:
            delay = random.randint(180, 600)

        log.info(f"[{persona.slug}] Will respond to chat in {delay}s")
        await asyncio.sleep(delay)

        prompt = CHAT_RESPONSE_PROMPT.format(
            persona_name=persona.display_name,
            persona_personality=persona.personality,
            persona_emoji_style=persona.emoji_style,
            persona_slang_notes=persona.slang_notes,
            persona_motivation_style=persona.motivation_style,
            human_name=user.first_name,
            message_text=message_text,
            recent_chat="(start of conversation)",
        )

        response = await generate_message(SYSTEM_PROMPT, prompt, max_tokens=100)
        if not response:
            continue

        bot = get_persona_bot(persona.slug)
        if not bot:
            continue

        try:
            await bot.send_message(chat_id=chat_id, text=response)
            log.info(f"[{persona.slug}] Responded to chat: {response[:60]}...")
        except Exception as e:
            log.error(f"[{persona.slug}] Failed to respond: {e}")
