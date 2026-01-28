import os
import sys
import logging
import threading
import subprocess
import glob
import asyncio
import shutil
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. KOYEB HEALTH CHECK (Essential for Free Tier) ---
health_app = Flask(__name__)

@health_app.route('/')
def health():
    return "Bot is healthy and running.", 200

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    health_app.run(host='0.0.0.0', port=port, threaded=True)

# --- 2. LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- 3. CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"

# --- 4. HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to /start"""
    await update.message.reply_html(
        "<b>🎵 Hi-Res 24-bit Downloader</b>\n"
        "Send a Qobuz link or just type a song name to search."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes any text (links or search terms) that isn't a command."""
    text = update.message.text
    if not text: return

    # Animation: Show 'Typing' while processing input
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # Create a button to trigger the download process
    keyboard = [[InlineKeyboardButton("📥 Download 24-bit FLAC", callback_data=text)]]
    await update.message.reply_html(
        f"🔍 <b>Ready to process:</b> <code>{text}</code>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The heavy lifting: downloading and sending audio."""
    query = update.callback_query
    await query.answer()
    
    url_or_name = query.data 
    status_msg = await query.edit_message_text("📥 <b>Fetching Hi-Res Audio...</b>", parse_mode='HTML')

    # Ensure clean directory for every task
    if os.path.exists(DOWNLOAD_DIR): shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    try:
        # Animation: Show 'Uploading' for large files
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.UPLOAD_DOCUMENT)

        # Run qobuz-dl asynchronously
        process = await asyncio.create_subprocess_exec(
            "qobuz-dl", "dl", url_or_name, "-q", "27", "-d", DOWNLOAD_DIR, "--embed-art",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        # Find the .flac file (searching subfolders)
        files = glob.glob(f"{DOWNLOAD_DIR}/**/*.flac", recursive=True)

        if files:
            audio_path = files[0]
            with open(audio_path, 'rb') as f:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    caption="✅ <b>24-bit Studio Master</b>",
                    parse_mode='HTML',
                    read_timeout=3000 # Critical for large 24-bit files
                )
            shutil.rmtree(DOWNLOAD_DIR) # Clean space
            await status_msg.delete()
        else:
            await query.edit_message_text("❌ Error: Audio file not found. Check the link/name.")

    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(f"❌ <b>Failed:</b> {str(e)}", parse_mode='HTML')

# --- 5. INITIALIZATION HOOK ---

async def post_init(application):
    """Fixes the 'Conflict' and 'No Response' errors on startup."""
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhooks cleared. Bot connection established.")

# --- 6. MAIN EXECUTION ---

if __name__ == '__main__':
    if not TOKEN:
        logger.error("Missing BOT_TOKEN in environment variables!")
        sys.exit(1)

    # Start Flask (Koyeb Health Check) in a background thread
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Setup Telegram Application
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_dl))
    # This handler catches all text messages (links or search names)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("Bot is polling...")
    app.run_polling(drop_pending_updates=True)
