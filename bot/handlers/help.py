"""Help command — shows all available commands and how to use them."""

from telegram import Update
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏋️ Start Squad — Commands\n\n"
        "/start — Set up your squad (first time only)\n"
        "/workout — Log a workout\n"
        "   e.g. /workout squats 30\n"
        "   e.g. /workout pushups 20 3  (20 reps, 3 sets)\n"
        "   Or just type: \"did 30 squats and 15 pushups\"\n\n"
        "/today — Where you're at today + yesterday's recap\n"
        "/stats — This week's summary\n"
        "/stats month — Last 30 days\n"
        "/history — Progress chart\n\n"
        "/coach — Chat with your squad coach\n"
        "   Ask about form, motivation, or anything fitness\n\n"
        "Questions? Just use /coach and ask!"
    )
