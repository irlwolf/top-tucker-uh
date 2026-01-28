import os
import sys
import logging
import threading
import subprocess
import glob
import asyncio
import shutil
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- 1. KOYEB HEALTH CHECK ---
health_app = Flask(__name__)

@health_app.route('/')
def health():
    return "Bot is healthy and running.", 200

def run_health_server():
    # Koyeb passes the PORT via environment variable
    port = int(os.environ.get("PORT", 8000))
    health_app.run(host='0.0.0.0', port=port, threaded=True)

# --- 2. LOGGING ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- 3. CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"

# --- 4. HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "<b>🎵 Hi-Res 24-bit Downloader</b>\n"
        "Send a Qobuz link to begin. Use /help for more."
    )

async def handle_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = query.data 
    status_msg = await query.edit_message_text("📥 <b>Downloading...</b>", parse_mode='HTML')

    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    try:
        process = await asyncio.create_subprocess_exec(
            "qobuz-dl", "dl", url, "-q", "27", "-d", DOWNLOAD_DIR, "--embed-art",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        files = glob.glob(f"{DOWNLOAD_DIR}/**/*.flac", recursive=True)

        if files:
            audio_path = files[0]
            with open(audio_path, 'rb') as f:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    caption="✨ <i>Source: Qobuz 24-bit</i>",
                    parse_mode='HTML',
                    read_timeout=3000 
                )
            shutil.rmtree(DOWNLOAD_DIR)
            await status_msg.delete()
        else:
            await query.edit_message_text("❌ Error: File not found.")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}", parse_mode='HTML')

# --- 5. CLEANUP & STARTUP ---
async def post_init(application):
    """
    Ensures any old Webhooks are deleted before Polling starts.
    This fixes the 'Conflict' error.
    """
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Stale webhooks deleted. Conflict resolved.")

if __name__ == '__main__':
    if not TOKEN:
        logger.error("Missing BOT_TOKEN environment variable!")
        sys.exit(1)

    # Start Flask Health Server in background thread
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Initialize the Application
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)  # Runs the cleanup logic automatically
        .build()
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_dl))
    
    logger.info("Bot is running and updates are cleared...")
    
    # run_polling handles the event loop and signals automatically
    application.run_polling(drop_pending_updates=True)
