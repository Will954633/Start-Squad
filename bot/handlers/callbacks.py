"""Generic callback query handlers (not covered by conversation handlers)."""

from telegram import Update
from telegram.ext import ContextTypes


async def unknown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unexpected callback queries gracefully."""
    query = update.callback_query
    await query.answer("That button has expired. Try again!")
