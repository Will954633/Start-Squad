"""
Creates all Telegram bot Application instances.
1 main bot (human interaction) + 5 persona bots (post to groups).
"""

from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler

from config import Config
from logger import log


# Persona bot instances (used for sending messages only, no handlers)
persona_bots: dict[str, Bot] = {}


def create_main_app() -> Application:
    """Create the main bot application with all handlers."""
    from bot.handlers.onboarding import get_onboarding_handler
    from bot.handlers.workout import workout_command, workout_message
    from bot.handlers.stats import stats_command, history_command
    from bot.handlers.admin import admin_command

    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Onboarding conversation handler (must be added first)
    app.add_handler(get_onboarding_handler())

    # Workout commands
    app.add_handler(CommandHandler("workout", workout_command))
    app.add_handler(CommandHandler("log", workout_command))

    # Stats commands
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("history", history_command))

    # Admin commands
    app.add_handler(CommandHandler("admin", admin_command))

    # Natural language workout messages in groups
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        workout_message,
    ))

    log.info("Main bot application created with all handlers")
    return app


def init_persona_bots():
    """Initialize Bot instances for all personas."""
    global persona_bots
    for slug, token in Config.PERSONA_TOKENS.items():
        if token:
            persona_bots[slug] = Bot(token=token)
            log.info(f"Persona bot initialized: {slug}")
        else:
            log.warning(f"No token for persona: {slug}")


def get_persona_bot(slug: str) -> Bot | None:
    """Get a persona's Bot instance by slug."""
    return persona_bots.get(slug)
