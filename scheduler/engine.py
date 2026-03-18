"""APScheduler setup — manages all timed persona posts, reminders, and nudges."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Config
from logger import log


scheduler = AsyncIOScheduler(timezone=Config.DEFAULT_TIMEZONE)


def start_scheduler():
    """Register all recurring jobs and start the scheduler."""
    from scheduler.jobs.daily_planning import plan_next_day
    from scheduler.jobs.morning_reminder import send_morning_reminders
    from scheduler.jobs.evening_nudge import check_evening_nudge
    from scheduler.jobs.persona_posts import execute_pending_posts

    # Midnight: plan the next day's schedule for all personas
    scheduler.add_job(
        plan_next_day,
        CronTrigger(hour=0, minute=5),
        id="daily_planning",
        replace_existing=True,
    )

    # Every morning at 7am: send daily reminder to all users
    scheduler.add_job(
        send_morning_reminders,
        CronTrigger(hour=7, minute=0),
        id="morning_reminders",
        replace_existing=True,
    )

    # 6pm: first evening nudge check
    scheduler.add_job(
        check_evening_nudge,
        CronTrigger(hour=18, minute=0),
        id="evening_nudge_first",
        replace_existing=True,
    )

    # 8pm: second evening nudge (more insistent)
    scheduler.add_job(
        lambda: check_evening_nudge(is_second_check=True),
        CronTrigger(hour=20, minute=0),
        id="evening_nudge_second",
        replace_existing=True,
    )

    # Every 5 minutes: execute any pending scheduled posts
    scheduler.add_job(
        execute_pending_posts,
        "interval",
        minutes=5,
        id="execute_posts",
        replace_existing=True,
    )

    scheduler.start()
    log.info("Scheduler started with all jobs registered")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("Scheduler stopped")
