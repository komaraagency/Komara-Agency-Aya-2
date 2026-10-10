"""
Worker principal du bot Telegram.
Point d'entrée pour Railway/Heroku.
"""
import os
import sys
import time
import logging
import threading
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from telegram.error import ApiTelegramException

from config import TELEGRAM_BOT_TOKEN, DEFAULT_LANGUAGE, ADMIN_CHAT_ID
from utils import clean_text, is_single_digit, GENERIC_MESSAGES, GREETED_SESSIONS
from anti_doublon import is_duplicate, mark_processed
from memory_sheets import log_conversation
from language_detector import detect_language, change_language, get_language
from message_router import route_message, handle_greeting
from logical_steps import start_devis_flow
from portfolio_drive import list_portfolio_images, download_image
from pending_question import set_pending, clear_pending

# === Logging ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# === Handlers de commandes ===
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start : accueil et détection de langue."""
    chat_id = update.effective_chat.id
    user = update.effective_user

    # Anti-doublon
    event_key = f"start_{chat_id}_{update.message.message_id}"
    if is_duplicate(event_key):
        return
    mark_processed(event_key)

    # Détection de langue
    lang = detect_language(user.first_name or "", chat_id)

    # Salutation (une seule fois par session)
    if chat_id not in GREETED_SESSIONS:
        GREETED_SESSIONS[chat_id] = True
        await update.message.reply_text(GENERIC_MESSAGES[lang]["greeting"])

    # Log
    log_conversation(chat_id, user.first_name or "", "client", "/start", lang)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /help : aide."""
    chat_id = update.effective_chat.id
    lang = get_language(chat_id)

    help_texts = {
        "fr": "🤖 *Komara Bot*\n\nJe peux vous aider avec :\n• Informations sur nos services\n• Demande de devis\n• Portfolio\n• Questions générales\n\nTapez simplement votre question !",
        "ar": "🤖 *كومارا بوت*\n\nيمكنني مساعدتك في:\n• معلومات عن خدماتنا\n• طلب عرض سعر\n• معرض الأعمال\n• أسئلة عامة\n\nاكتب سؤالك ببساطة!",
        "en": "🤖 *Komara Bot*\n\nI can help you with:\n• Information about our services\n• Quote requests\n• Portfolio\n• General questions\n\nJust type your question!",
    }

    await update.message.reply_text(help_texts.get(lang, help_texts["fr"]), parse_mode="Markdown")


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /lang : changement de langue."""
    chat_id = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Choisissez votre langue / اختر لغتك / Choose your language:", reply_markup=reply_markup)


async def devis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /devis : démarrage du flux de devis."""
    chat_id = update.effective_chat.id
    lang = get_language(chat_id)

    response = start_devis_flow(chat_id, lang)
    await update.message.reply_text(response)


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /portfolio : affichage du portfolio."""
    chat_id = update.effective_chat.id
    lang = get_language(chat_id)

    await update.message.reply_text("⏳ Chargement du portfolio...")

    images = list_portfolio_images()
    if not images:
        messages = {
            "fr": "Le portfolio est temporairement indisponible. Veuillez réessayer plus tard.",
            "ar": "معرض الأعمال غير متاح مؤقتا. يرجى المحاولة لاحقا.",
            "en": "Portfolio is temporarily unavailable. Please try again later.",
        }
        await update.message.reply_text(messages.get(lang, messages["fr"]))
        return

    # Envoyer les 5 premières images
    for img in images[:5]:
        try:
            image_data = download_image(img["id"])
            if image_data:
                import io
                photo = io.BytesIO(image_data)
                photo.name = img["name"]
                await update.message.reply_photo(photo=photo, caption=img["name"])
        except Exception as e:
            logger.error(f"Erreur envoi image: {e}")


# === Handler de messages texte ===
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Traite tous les messages texte."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_text = update.message.text

    # Anti-doublon
    event_key = f"msg_{chat_id}_{update.message.message_id}"
    if is_duplicate(event_key):
        return
    mark_processed(event_key)

    # Nettoyage
    text = clean_text(user_text)
    if not text:
        return

    # Détection de langue
    lang = detect_language(text, chat_id)

    # Log message client
    log_conversation(chat_id, user.first_name or "", "client", text, lang)

    # Fonction d'envoi (pour le routeur)
    async def send_message(chat_id, message):
        await context.bot.send_message(chat_id=chat_id, text=message)
        # Log message bot (asynchrone)
        log_conversation(chat_id, "bot", "bot", message, lang)

    # Router le message
    try:
        # PTB est asynchrone : le routeur est synchrone, on planifie
        # l'envoi avec create_task pour ne pas créer une coroutine
        # jamais attendue (messages jamais envoyés).
        route_message(
            chat_id, text,
            lambda cid, msg: asyncio.create_task(
                context.bot.send_message(chat_id=cid, text=msg)
            ),
        )
    except Exception as e:
        logger.error(f"Erreur routage message: {e}", exc_info=True)
        await update.message.reply_text(GENERIC_MESSAGES[lang]["no_understand"])


# === Handler de callbacks (boutons inline) ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Traite les clics sur les boutons inline."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    # Changement de langue
    if data.startswith("lang_"):
        new_lang = data.replace("lang_", "")
        change_language(chat_id, new_lang)

        messages = {
            "fr": "✅ Langue changée : Français",
            "ar": "✅ تم تغيير اللغة: العربية",
            "en": "✅ Language changed: English",
        }
        await query.message.reply_text(messages.get(new_lang, messages["fr"]))
        return

    # Autres callbacks
    logger.info(f"Callback reçu: {data}")


# === Handler d'erreurs ===
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log les erreurs."""
    logger.error(f"Exception: {context.error}", exc_info=context.error)


# === Fonction principale ===
def main():
    """Démarre le bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN manquant !")
        sys.exit(1)

    logger.info("Démarrage du bot Komara...")

    # Créer l'application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lang", lang_command))
    application.add_handler(CommandHandler("devis", devis_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Erreurs
    application.add_error_handler(error_handler)

    # Démarrage
    logger.info("Bot démarré ! Polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
