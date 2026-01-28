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

# --- 1. KOYEB HEALTH CHECK ---
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
    """Improved downloader with buffer management and logging."""
    query = update.callback_query
    await query.answer()
    
    url = query.data 
    status_msg = await query.edit_message_text("📥 <b>Fetching Hi-Res Audio...</b>", parse_mode='HTML')

    if os.path.exists(DOWNLOAD_DIR): shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    try:
        # 1. RUN WITH LOGGING (Ensures subprocess doesn't hang)
        process = await asyncio.create_subprocess_exec(
            "qobuz-dl", "dl", url, "-q", "27", "-d", DOWNLOAD_DIR, "--embed-art",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Read logs in real-time to prevent buffer clog
        stdout, stderr = await process.communicate()
        
        if stdout: logger.info(f"Qobuz-DL Output: {stdout.decode()}")
        if stderr: logger.error(f"Qobuz-DL Error: {stderr.decode()}")

        # 2. FILE SEARCH
        files = glob.glob(f"{DOWNLOAD_DIR}/**/*.flac", recursive=True)

        if files:
            audio_path = files[0]
            # Update status for the user
            await status_msg.edit_text("🚀 <b>Uploading to Telegram...</b>", parse_mode='HTML')
            
            # Show 'Uploading' animation
            await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.UPLOAD_DOCUMENT)

            with open(audio_path, 'rb') as f:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    caption="✅ <b>24-bit Studio Master</b>",
                    parse_mode='HTML',
                    read_timeout=3600  # Give it 1 hour for huge files
                )
            shutil.rmtree(DOWNLOAD_DIR)
            await status_msg.delete()
        else:
            await query.edit_message_text("❌ <b>Error:</b> Audio file not found. Check Koyeb logs for authentication or link errors.")

    except Exception as e:
        logger.error(f"Critical Download Error: {e}")
        await query.edit_message_text(f"❌ <b>Crash:</b> {str(e)}", parse_mode='HTML')

# --- 5. INITIALIZATION HOOK ---

async def post_init(application):
    """Fixes 'Conflict' errors by wiping old connections on start."""
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhooks cleared. Bot connection established.")

# --- 6. MAIN EXECUTION ---

if __name__ == '__main__':
    if not TOKEN:
        logger.error("Missing BOT_TOKEN!")
        sys.exit(1)

    # Start Flask Health Server
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Setup Telegram Application
    app = ApplicationBuilder().token(TOKEN).build()
    
    # --- ENHANCED CONFLICT RESOLVER ---
    async def final_bootstrap():
        # 1. Wait for old Koyeb instances to shut down
        logger.info("Waiting 15 seconds for old sessions to clear...")
        await asyncio.sleep(15) 
        
        # 2. Force delete any webhooks
        await app.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhooks cleared. Bot connection established.")

    # Run the bootstrap
    loop = asyncio.get_event_loop()
    loop.run_until_complete(final_bootstrap())

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_dl))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("Polling started...")
    app.run_polling(drop_pending_updates=True)
