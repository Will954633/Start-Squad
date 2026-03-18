"""Admin commands for managing Start Squad."""

from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from logger import log
from db.connection import async_session
from db.queries.users import get_all_active_users


def is_admin(telegram_id: int) -> bool:
    return telegram_id in Config.ADMIN_TELEGRAM_IDS


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin commands."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You don't have admin access.")
        return

    if not context.args:
        await update.message.reply_text(
            "Admin commands:\n"
            "/admin status — Active user count\n"
            "/admin broadcast <msg> — Send to all users"
        )
        return

    subcommand = context.args[0].lower()

    if subcommand == "status":
        async with async_session() as session:
            users = await get_all_active_users(session)
        await update.message.reply_text(
            f"Active users: {len(users)}\n"
            f"Environment: {Config.ENVIRONMENT}"
        )

    elif subcommand == "broadcast":
        msg = " ".join(context.args[1:])
        if not msg:
            await update.message.reply_text("Usage: /admin broadcast <message>")
            return
        async with async_session() as session:
            users = await get_all_active_users(session)
        sent = 0
        for user in users:
            try:
                await context.bot.send_message(chat_id=user.telegram_id, text=msg)
                sent += 1
            except Exception as e:
                log.warning(f"Failed to send to {user.telegram_id}: {e}")
        await update.message.reply_text(f"Broadcast sent to {sent}/{len(users)} users.")

    else:
        await update.message.reply_text(f"Unknown admin command: {subcommand}")
