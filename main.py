"""
Start Squad — Entry Point
Starts the main Telegram bot, initializes persona bots, database, and scheduler.
"""

import asyncio
import signal
from config import Config
from logger import log


async def main():
    # Validate config
    errors = Config.validate()
    if errors:
        for err in errors:
            log.error(f"Config error: {err}")
        log.error("Fix configuration errors before starting. See .env.example")
        return

    log.info(f"Starting Start Squad ({Config.ENVIRONMENT})")

    # Initialize database
    from db.connection import init_db, close_db
    await init_db()
    log.info("Database initialized")

    # Seed personas if needed
    from db.connection import async_session
    from db.queries.personas import get_all_personas
    async with async_session() as session:
        personas = await get_all_personas(session)
        if not personas:
            from bot.handlers.onboarding import _seed_personas
            await _seed_personas(session)
            log.info("Personas seeded")

    # Initialize persona bots
    from bot.app import init_persona_bots, create_main_app
    init_persona_bots()

    # Start scheduler
    from scheduler.engine import start_scheduler, stop_scheduler
    start_scheduler()

    # Create and run the main bot
    app = create_main_app()

    log.info("Bot is running. Press Ctrl+C to stop.")

    # Run the bot with polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Wait for shutdown signal
    stop_event = asyncio.Event()

    def handle_signal():
        log.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    await stop_event.wait()

    # Cleanup
    log.info("Shutting down...")
    stop_scheduler()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    await close_db()
    log.info("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
