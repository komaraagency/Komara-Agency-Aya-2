"""
Point d'entrée principal du bot Komara Agency Aya 2.
I/O Telegram uniquement : toute la logique est dans message_router.
"""
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters,
)
from config import TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID
import anti_doublon
import message_router
import memory_sheets

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("worker")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reply, lang = message_router.route(chat_id, "/start")
    await update.message.reply_text(reply)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Réception d'un message texte : anti-doublon -> logique -> réponse."""
    event_key = f"msg-{update.update_id}"
    if anti_doublon.is_duplicate(event_key):
        logger.info("Doublon ignoré: %s", event_key)
        return

    text = update.message.text
    if not text:
        return
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name or "Client"

    reply, lang = message_router.route(chat_id, text, user_name)

    await update.message.reply_text(reply)

    # Logging asynchrone (ne bloque jamais)
    memory_sheets.log_conversation(chat_id, user_name, "user", text, lang)
    memory_sheets.log_conversation(chat_id, "Aya", "bot", reply, lang)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN manquant (voir .env.example)")
    logger.info("Démarrage Komara Agency Aya 2...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
