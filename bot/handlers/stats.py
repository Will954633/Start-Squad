"""Stats, today, and history command handlers."""

import io
from datetime import date, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from logger import log
from db.connection import async_session
from db.queries.users import get_user_by_telegram_id
from db.queries.stats import (
    get_weekly_stats, get_monthly_stats, get_current_streak,
    get_or_create_daily_stat,
)


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /today — show today's progress and yesterday's recap."""
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if not user:
            await update.message.reply_text("Use /start to set up first!")
            return

        today = date.today()
        yesterday = today - timedelta(days=1)

        today_stat = await get_or_create_daily_stat(session, user.id, today)
        yesterday_stat = await get_or_create_daily_stat(session, user.id, yesterday)
        streak = await get_current_streak(session, user.id)

    # Exercise labels based on user preferences
    pushup_label = "Push-ups (knees)" if user.pushup_variant == "knees" else "Push-ups"
    situp_label = "Crunches" if user.situp_variant == "crunches" else "Sit-ups"

    # Today section
    if today_stat.completed:
        today_text = (
            f"TODAY ✅\n"
            f"  🦵 Squats: {today_stat.total_squats}\n"
            f"  💪 {pushup_label}: {today_stat.total_pushups}\n"
            f"  🫡 {situp_label}: {today_stat.total_situps}\n"
            f"  📝 {today_stat.workout_count} workout{'s' if today_stat.workout_count != 1 else ''} logged"
        )
    else:
        today_text = (
            "TODAY — No workout yet\n"
            "  Your squad is waiting for you! 💪\n"
            "  Log with /workout (e.g. /workout squats 30)"
        )

    # Yesterday section
    if yesterday_stat.completed:
        yesterday_text = (
            f"YESTERDAY ✅\n"
            f"  🦵 Squats: {yesterday_stat.total_squats}\n"
            f"  💪 {pushup_label}: {yesterday_stat.total_pushups}\n"
            f"  🫡 {situp_label}: {yesterday_stat.total_situps}"
        )
    else:
        yesterday_text = "YESTERDAY — Rest day"

    text = (
        f"📍 {user.first_name}'s Status\n"
        f"🔥 Streak: {streak} day{'s' if streak != 1 else ''}\n\n"
        f"{today_text}\n\n"
        f"{yesterday_text}"
    )

    await update.message.reply_text(text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command — show workout summary."""
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if not user:
            await update.message.reply_text("Use /start to set up first!")
            return

        # Determine period
        period = "week"
        if context.args and context.args[0].lower() in ("week", "month"):
            period = context.args[0].lower()

        if period == "month":
            stats = await get_monthly_stats(session, user.id)
            period_label = "Last 30 days"
        else:
            stats = await get_weekly_stats(session, user.id)
            period_label = "Last 7 days"

        streak = await get_current_streak(session, user.id)

    if not stats:
        await update.message.reply_text(
            f"No workout data for {period_label.lower()} yet.\n"
            "Log your first workout with /workout!"
        )
        return

    total_squats = sum(s.total_squats for s in stats)
    total_pushups = sum(s.total_pushups for s in stats)
    total_situps = sum(s.total_situps for s in stats)
    active_days = sum(1 for s in stats if s.completed)

    text = (
        f"📊 {period_label} — {user.first_name}\n\n"
        f"🔥 Current streak: {streak} day{'s' if streak != 1 else ''}\n"
        f"📅 Active days: {active_days}/{len(stats)}\n\n"
        f"🦵 Squats: {total_squats}\n"
        f"💪 Push-ups: {total_pushups}\n"
        f"🫡 Sit-ups: {total_situps}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Total reps: {total_squats + total_pushups + total_situps}"
    )

    await update.message.reply_text(text)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history command — show chart of workout trends."""
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if not user:
            await update.message.reply_text("Use /start to set up first!")
            return

        stats = await get_monthly_stats(session, user.id)

    if not stats:
        await update.message.reply_text("No workout history yet! Start with /workout.")
        return

    try:
        chart = _generate_chart(stats, user.first_name)
        await update.message.reply_photo(
            photo=chart,
            caption=f"📈 {user.first_name}'s workout history (last 30 days)"
        )
    except Exception as e:
        log.error(f"Chart generation failed: {e}")
        await update.message.reply_text("Couldn't generate chart. Try /stats instead.")


def _generate_chart(stats: list, name: str) -> io.BytesIO:
    """Generate a workout history bar chart."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dates = [s.stat_date.strftime("%d/%m") for s in stats]
    squats = [s.total_squats for s in stats]
    pushups = [s.total_pushups for s in stats]
    situps = [s.total_situps for s in stats]

    fig, ax = plt.subplots(figsize=(10, 5))

    x = range(len(dates))
    width = 0.25

    ax.bar([i - width for i in x], squats, width, label="Squats", color="#FF6B6B")
    ax.bar(x, pushups, width, label="Push-ups", color="#4ECDC4")
    ax.bar([i + width for i in x], situps, width, label="Sit-ups", color="#45B7D1")

    ax.set_xlabel("Date")
    ax.set_ylabel("Reps")
    ax.set_title(f"{name}'s Workout History")
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right")
    ax.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return buf
