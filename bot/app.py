"""
Creates all Telegram bot Application instances.
1 main bot (human interaction) + 5 persona bots (post to groups).
"""

from telegram import Bot, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import Config
from logger import log


# Persona bot instances (used for sending messages only, no handlers)
persona_bots: dict[str, Bot] = {}

# Bot menu commands visible in Telegram
BOT_COMMANDS = [
    BotCommand("start", "Set up your squad"),
    BotCommand("workout", "Log a workout (e.g. /workout squats 30)"),
    BotCommand("today", "See where you're at today"),
    BotCommand("stats", "Your workout stats this week"),
    BotCommand("history", "Progress chart (last 30 days)"),
    BotCommand("coach", "Chat with your squad coach"),
    BotCommand("help", "How to use Start Squad"),
]


def create_main_app() -> Application:
    """Create the main bot application with all handlers."""
    from bot.handlers.onboarding import get_onboarding_handler
    from bot.handlers.workout import workout_command, workout_message
    from bot.handlers.stats import stats_command, history_command, today_command
    from bot.handlers.coach import coach_command, coach_message, get_coach_handler
    from bot.handlers.admin import admin_command
    from bot.handlers.help import help_command

    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Set bot menu commands on startup
    app.post_init = _set_bot_commands

    # Onboarding conversation handler (must be added first)
    app.add_handler(get_onboarding_handler())

    # Coach conversation handler (second priority)
    app.add_handler(get_coach_handler())

    # Workout commands
    app.add_handler(CommandHandler("workout", workout_command))
    app.add_handler(CommandHandler("log", workout_command))

    # Status commands
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("history", history_command))

    # Coach (standalone, outside conversation)
    app.add_handler(CommandHandler("coach", coach_command))

    # Help
    app.add_handler(CommandHandler("help", help_command))

    # Admin commands
    app.add_handler(CommandHandler("admin", admin_command))

    # Natural language workout messages in groups
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        workout_message,
    ))

    # General chat — any DM text that isn't a command or caught by conversation handlers
    # Triggers persona reactions so the chat feels alive
    from bot.handlers.chat import general_chat_message
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        general_chat_message,
    ))

    log.info("Main bot application created with all handlers")
    return app


async def _set_bot_commands(app: Application):
    """Set the bot menu commands visible in Telegram."""
    await app.bot.set_my_commands(BOT_COMMANDS)
    log.info(f"Bot menu commands set ({len(BOT_COMMANDS)} commands)")


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
