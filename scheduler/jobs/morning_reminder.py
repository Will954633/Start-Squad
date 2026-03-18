"""7am daily morning reminder — summary of yesterday + today's goal."""

from datetime import date, timedelta
from telegram import Bot

from config import Config
from logger import log
from db.connection import async_session
from db.queries.users import get_all_active_users
from db.queries.stats import get_current_streak
from llm.client import generate_message
from llm.prompts import SYSTEM_PROMPT, MORNING_SUMMARY_PROMPT


async def send_morning_reminders():
    """Send morning summary to all active users."""
    log.info("Sending morning reminders")
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)

    async with async_session() as session:
        users = await get_all_active_users(session)

        for user in users:
            try:
                streak = await get_current_streak(session, user.id)

                # Build yesterday's stats block
                yesterday = date.today() - timedelta(days=1)
                from db.queries.stats import get_or_create_daily_stat
                stat = await get_or_create_daily_stat(session, user.id, yesterday)

                stats_block = (
                    f"- {user.first_name}: "
                    f"{stat.total_squats} squats, "
                    f"{stat.total_pushups} push-ups, "
                    f"{stat.total_situps} sit-ups"
                    f"{' ✅' if stat.completed else ' (rest day)'}"
                )

                # Suggest today's focus
                exercises = ["squats", "push-ups", "sit-ups"]
                import random
                focus = random.choice(exercises)
                suggested = f"Focus on {focus} today — aim for a personal best!"

                prompt = MORNING_SUMMARY_PROMPT.format(
                    human_name=user.first_name,
                    yesterday_stats_block=stats_block,
                    streak=streak,
                    suggested_workout=suggested,
                )

                message = await generate_message(SYSTEM_PROMPT, prompt, max_tokens=200)
                if not message:
                    message = (
                        f"Good morning {user.first_name}! 🌅\n"
                        f"Streak: {streak} day{'s' if streak != 1 else ''}\n"
                        f"Let's get after it today — {suggested}"
                    )

                await bot.send_message(chat_id=user.telegram_id, text=message)
                log.info(f"Morning reminder sent to {user.first_name}")

            except Exception as e:
                log.error(f"Failed to send morning reminder to {user.telegram_id}: {e}")
