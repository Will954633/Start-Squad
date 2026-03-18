"""
Onboarding ConversationHandler.
Flow: /start → name → city → fitness level → goals → group creation → persona intros
"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)

from config import Config
from logger import log
from db.connection import async_session
from db.queries.users import get_user_by_telegram_id, create_user, mark_onboarding_complete
from db.queries.personas import get_all_personas, set_calibration
from db.models import TeamGroup
from personas.calibration import calculate_adjusted_baseline
from personas.definitions import PERSONAS

# Conversation states
NAME, CITY, FITNESS_LEVEL, GOALS, CONFIRM = range(5)

# Common Australian cities
CITIES = [
    "Gold Coast", "Brisbane", "Sydney", "Melbourne",
    "Perth", "Adelaide", "Hobart", "Canberra",
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command — begin onboarding."""
    async with async_session() as session:
        existing = await get_user_by_telegram_id(session, update.effective_user.id)
        if existing and existing.onboarding_complete:
            await update.message.reply_text(
                f"Welcome back, {existing.first_name}! You're already set up. "
                "Use /workout to log your exercises or /stats to see your progress."
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "Hey! Welcome to Start Squad 💪\n\n"
        "I'm about to set you up with a fitness team that will train "
        "alongside you every single day.\n\n"
        "Let's get to know you first. What's your name?"
    )
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store name, ask for city."""
    context.user_data["name"] = update.message.text.strip()

    keyboard = [
        [InlineKeyboardButton(city, callback_data=f"city_{city}")]
        for city in CITIES
    ]
    keyboard.append([InlineKeyboardButton("Other", callback_data="city_other")])

    await update.message.reply_text(
        f"Nice to meet you, {context.user_data['name']}! Where are you based?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CITY


async def receive_city_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle city selection via inline keyboard."""
    query = update.callback_query
    await query.answer()

    city = query.data.replace("city_", "")
    if city == "other":
        await query.edit_message_text("No worries! Just type your city:")
        return CITY

    context.user_data["city"] = city
    return await _ask_fitness_level(query.message, context)


async def receive_city_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle city typed manually."""
    context.user_data["city"] = update.message.text.strip()
    return await _ask_fitness_level(update.message, context)


async def _ask_fitness_level(message, context) -> int:
    keyboard = [
        [InlineKeyboardButton("Beginner (just starting)", callback_data="level_beginner")],
        [InlineKeyboardButton("Intermediate (somewhat active)", callback_data="level_intermediate")],
        [InlineKeyboardButton("Advanced (regular training)", callback_data="level_advanced")],
    ]
    await message.reply_text(
        "How would you describe your current fitness level?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FITNESS_LEVEL


async def receive_fitness_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle fitness level selection."""
    query = update.callback_query
    await query.answer()

    level = query.data.replace("level_", "")
    context.user_data["fitness_level"] = level

    await query.edit_message_text(
        "Last question — what's your main fitness goal?\n"
        "(e.g., get stronger, lose weight, build a habit, feel better)"
    )
    return GOALS


async def receive_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store goals, show confirmation."""
    context.user_data["goals"] = update.message.text.strip()
    data = context.user_data

    await update.message.reply_text(
        f"Here's what I've got:\n\n"
        f"Name: {data['name']}\n"
        f"City: {data['city']}\n"
        f"Fitness Level: {data['fitness_level'].title()}\n"
        f"Goal: {data['goals']}\n\n"
        "Sound right? Your squad is ready to meet you!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Let's go!", callback_data="confirm_yes")],
            [InlineKeyboardButton("Start over", callback_data="confirm_no")],
        ]),
    )
    return CONFIRM


async def confirm_and_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create user, group, and trigger persona introductions."""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("No worries! Let's start over. What's your name?")
        return NAME

    await query.edit_message_text("Setting up your squad now... 🏋️")

    data = context.user_data
    tg_user = update.effective_user

    async with async_session() as session:
        # Create user
        user = await create_user(
            session,
            telegram_id=tg_user.id,
            first_name=data["name"],
            city=data["city"],
            fitness_level=data["fitness_level"],
            goals=data["goals"],
            telegram_username=tg_user.username,
        )

        # Create the team group
        # NOTE: Telegram Bot API cannot programmatically create groups.
        # The bot must be added to a group that the admin creates.
        # For MVP, we'll use a single group and DM approach.
        # For now, store the chat where /start was called.
        # TODO: Implement proper group creation flow

        # Calibrate personas to user's fitness level
        personas = await get_all_personas(session)
        if not personas:
            # Seed personas if not yet in DB
            await _seed_personas(session)
            personas = await get_all_personas(session)

        for persona in personas:
            adjusted = calculate_adjusted_baseline(
                persona.slug, persona.fitness_baseline, data["fitness_level"]
            )
            await set_calibration(session, user.id, persona.id, adjusted)

        await mark_onboarding_complete(session, user.id)

    await query.message.reply_text(
        f"You're all set, {data['name']}! 🎉\n\n"
        f"Your squad is from {data['city']} and they're fired up to train with you.\n\n"
        "Here's how it works:\n"
        "• Your team posts their workouts every day\n"
        "• Log yours with /workout (e.g., /workout squats 30)\n"
        "• Check your progress with /stats\n"
        "• You'll get a morning reminder each day\n\n"
        "Your team will introduce themselves shortly. Welcome to Start Squad! 💪"
    )

    # Schedule staggered persona introductions
    asyncio.create_task(_send_persona_intros(
        update.effective_chat.id, data["name"], data["city"]
    ))

    return ConversationHandler.END


async def _send_persona_intros(chat_id: int, human_name: str, city: str):
    """Send staggered introduction messages from each persona."""
    from bot.app import get_persona_bot
    from llm.client import generate_message
    from llm.prompts import SYSTEM_PROMPT

    intros = {
        "mia": f"YESSS new squad member!! Welcome {human_name}! I'm Mia, I do my workouts before my morning coffee here in {city}. So pumped to have you here! 🔥✨",
        "damo": f"Welcome aboard mate. I'm Damo. Fair warning — I like a bit of friendly competition 💪",
        "priya": f"Hey {human_name}! I'm Priya. If you ever need form tips or have any aches, I'm your person 💚",
        "jake": f"yooo {human_name}! jake here. don't worry i'm also terrible at this. we suffer together 😂💀",
        "lena": f"Welcome {human_name}. I'm Lena. I squeeze workouts in during nap time so if I go quiet, the toddler won. Glad you're here ☕💪",
    }

    delays = {"mia": 5, "damo": 65, "priya": 130, "jake": 200, "lena": 260}

    for slug, delay in delays.items():
        await asyncio.sleep(delay)
        bot = get_persona_bot(slug)
        if bot:
            try:
                await bot.send_message(chat_id=chat_id, text=intros[slug])
                log.info(f"[{slug}] Sent intro to chat {chat_id}")
            except Exception as e:
                log.error(f"[{slug}] Failed to send intro: {e}")


async def _seed_personas(session):
    """Seed persona records into database."""
    from db.models import Persona
    for p_data in PERSONAS:
        persona = Persona(
            slug=p_data["slug"],
            display_name=p_data["display_name"],
            bot_token=Config.PERSONA_TOKENS.get(p_data["slug"], ""),
            bio=p_data["bio"],
            personality=p_data["personality"],
            fitness_baseline=p_data["fitness_baseline"],
            posting_window=p_data["posting_window"],
            emoji_style=p_data["emoji_style"],
            slang_notes=p_data["slang_notes"],
            motivation_style=p_data["motivation_style"],
            profile_photo_path=p_data["profile_photo_path"],
        )
        session.add(persona)
    await session.commit()
    log.info("Seeded 5 personas into database")


def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the onboarding conversation."""
    return ConversationHandler.END


def get_onboarding_handler() -> ConversationHandler:
    """Build and return the onboarding ConversationHandler."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            CITY: [
                CallbackQueryHandler(receive_city_button, pattern="^city_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_city_text),
            ],
            FITNESS_LEVEL: [
                CallbackQueryHandler(receive_fitness_level, pattern="^level_"),
            ],
            GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_goals)],
            CONFIRM: [
                CallbackQueryHandler(confirm_and_create, pattern="^confirm_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
