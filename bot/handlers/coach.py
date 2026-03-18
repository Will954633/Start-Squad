"""
/coach — Chat with your squad coach (GPT-5.4-nano).
Provides personalised form tips, motivation, and fitness advice.
Uses a ConversationHandler so the user can have a back-and-forth.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)

from logger import log
from db.connection import async_session
from db.queries.users import get_user_by_telegram_id
from db.queries.stats import get_weekly_stats, get_current_streak
from llm.client import generate_message


COACHING, = range(1)

COACH_SYSTEM_PROMPT = """You are Sam, the squad coach for Start Squad — a fitness \
accountability group on the Gold Coast, Australia. You're a physio student at Griffith \
Uni with Samoan heritage. You're calm, knowledgeable, and encouraging.

You help with:
- Exercise form (squats, push-ups, sit-ups/crunches)
- Motivation and mindset
- Workout suggestions and progressions
- Injury prevention and recovery
- General fitness questions

Rules:
- Keep responses under 500 characters
- Be conversational — you're a mate, not a textbook
- Reference Gold Coast when natural (local spots, weather)
- You are NOT a doctor — suggest seeing a GP for injuries/pain
- Never break character. You are Sam, a real person.
- Use 'uso' occasionally (Samoan for brother/family)"""


async def coach_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /coach — start coaching conversation."""
    await update.message.reply_text(
        "Hey! Sam here 💚\n\n"
        "I'm your squad coach. Ask me anything about:\n"
        "• Exercise form (squats, push-ups, crunches)\n"
        "• Motivation and getting back on track\n"
        "• Workout tips and progressions\n"
        "• Aches, pains, and recovery\n\n"
        "What's on your mind?",
    )
    return COACHING


async def coach_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages during coaching conversation."""
    user_text = update.message.text.strip()

    # Build context about the user
    user_context = ""
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if user:
            streak = await get_current_streak(session, user.id)
            stats = await get_weekly_stats(session, user.id)
            total_workouts = sum(1 for s in stats if s.completed) if stats else 0

            pushup_type = "from knees" if user.pushup_variant == "knees" else "from toes"
            situp_type = "crunches" if user.situp_variant == "crunches" else "full sit-ups"

            user_context = (
                f"\nUser info: {user.first_name}, {user.city}, {user.fitness_level} level. "
                f"Does push-ups {pushup_type} and {situp_type}. "
                f"Current streak: {streak} days. "
                f"Workouts this week: {total_workouts}. "
                f"Goal: {user.goals or 'not specified'}."
            )

    # Get conversation history from context (last 4 exchanges)
    if "coach_history" not in context.user_data:
        context.user_data["coach_history"] = []

    history = context.user_data["coach_history"]
    history_text = ""
    if history:
        history_text = "\n\nRecent conversation:\n" + "\n".join(
            f"{'User' if h['role'] == 'user' else 'Sam'}: {h['text']}"
            for h in history[-8:]  # Last 4 exchanges
        )

    prompt = (
        f"The user says: \"{user_text}\""
        f"{user_context}"
        f"{history_text}"
        f"\n\nRespond as Sam the coach. Keep it under 500 characters."
    )

    response = await generate_message(
        COACH_SYSTEM_PROMPT,
        prompt,
        max_tokens=250,
        temperature=0.8,
    )

    if not response:
        response = (
            "Sorry uso, my brain just glitched. Try asking again? "
            "If it's about an injury, definitely see your GP though 💚"
        )

    # Store in history
    history.append({"role": "user", "text": user_text[:200]})
    history.append({"role": "coach", "text": response[:200]})
    # Keep history manageable
    if len(history) > 12:
        context.user_data["coach_history"] = history[-8:]

    await update.message.reply_text(response)

    # Offer to continue or exit
    await update.message.reply_text(
        "Anything else? Or type /done to head back.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("That's all, thanks!", callback_data="coach_done")],
        ]),
    )
    return COACHING


async def coach_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("coach_history", None)
    await query.edit_message_text("No worries! I'm here anytime you need me. Use /coach to come back 💚")
    return ConversationHandler.END


async def coach_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done to exit coaching."""
    context.user_data.pop("coach_history", None)
    await update.message.reply_text("Catch you later! Use /coach anytime 💚")
    return ConversationHandler.END


def get_coach_handler() -> ConversationHandler:
    """Build the coach ConversationHandler."""
    return ConversationHandler(
        entry_points=[CommandHandler("coach", coach_command)],
        states={
            COACHING: [
                CallbackQueryHandler(coach_done_callback, pattern="^coach_done"),
                CommandHandler("done", coach_exit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, coach_message),
            ],
        },
        fallbacks=[
            CommandHandler("done", coach_exit),
            CommandHandler("cancel", coach_exit),
        ],
    )
