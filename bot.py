import os
import sys
import logging
import threading
import subprocess
import glob
import asyncio
import shutil
import json
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. KOYEB HEALTH CHECK ---
health_app = Flask(__name__)
@health_app.route('/')
def health(): 
    return "Bot is healthy.", 200

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    health_app.run(host='0.0.0.0', port=port, threaded=True)

# --- 2. LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 3. CONFIGURATION & QOBUZ AUTH ---
TOKEN = os.getenv("BOT_TOKEN")
APP_ID = os.getenv("QOBUZ_APP_ID")
APP_SECRET = os.getenv("QOBUZ_APP_SECRET")
DOWNLOAD_DIR = "downloads"

def setup_qobuz():
    """Generates the config file qobuz-dl needs to function."""
    config_path = os.path.expanduser("~/.config/qobuz-dl/config.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    config_data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET,
        "download_path": DOWNLOAD_DIR,
        "quality": 27,
        "embed_art": True
    }
    with open(config_path, "w") as f:
        json.dump(config_data, f)
    logger.info("Qobuz configuration initialized.")

# --- 4. HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("<b>🎵 Hi-Res 24-bit Downloader</b>\nSend a Qobuz link or type a song name.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    keyboard = [[InlineKeyboardButton("📥 Download 24-bit FLAC", callback_data=text)]]
    await update.message.reply_html(f"🔍 <b>Ready to process:</b> <code>{text}</code>", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    url = query.data 
    status_msg = await query.edit_message_text("📥 <b>Fetching Hi-Res Audio...</b>", parse_mode='HTML')

    if os.path.exists(DOWNLOAD_DIR): shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    try:
        # Run downloader
        process = await asyncio.create_subprocess_exec(
            "qobuz-dl", "dl", url, "-q", "27", "-d", DOWNLOAD_DIR, "--embed-art",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        if stdout: logger.info(f"Qobuz-DL Output: {stdout.decode()}")

        files = glob.glob(f"{DOWNLOAD_DIR}/**/*.flac", recursive=True)

        if files:
            audio_path = files[0]
            await status_msg.edit_text("🚀 <b>Uploading to Telegram...</b>", parse_mode='HTML')
            await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.UPLOAD_DOCUMENT)

            with open(audio_path, 'rb') as f:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    caption="✅ <b>24-bit Studio Master</b>",
                    parse_mode='HTML',
                    read_timeout=3600 
                )
            shutil.rmtree(DOWNLOAD_DIR)
            await status_msg.delete()
        else:
            await query.edit_message_text("❌ <b>Error:</b> File not found. Verify your Qobuz keys.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await query.edit_message_text(f"❌ <b>Failed:</b> {str(e)}", parse_mode='HTML')

# --- 5. MAIN EXECUTION ---

if __name__ == '__main__':
    if not TOKEN:
        logger.error("Missing BOT_TOKEN!")
        sys.exit(1)

    # 1. Initialize Qobuz configuration
    setup_qobuz()
    
    # 2. Start Health Server
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # 3. Setup Application
    app = ApplicationBuilder().token(TOKEN).build()
    
    # 4. Bootstrap / Conflict Resolver
    async def bootstrap():
        logger.info("Waiting 10s for old sessions to clear...")
        await asyncio.sleep(10)
        await app.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot connection ready.")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(bootstrap())

    # 5. Add Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_dl))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # 6. Start Polling
    logger.info("Bot is now polling...")
    app.run_polling(drop_pending_updates=True)
