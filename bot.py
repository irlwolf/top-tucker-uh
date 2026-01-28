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
    port = int(os.environ.get("PORT", 8000))
    # Threaded mode ensures Flask doesn't block
    health_app.run(host='0.0.0.0', port=port, threaded=True)

# --- 2. LOGGING ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Disable verbose logging for internal libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- 3. CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "<b>🎵 Hi-Res 24-bit Downloader</b>\n"
        "Send a Qobuz link to begin. Use /help for more."
    )

async def handle_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    url = query.data 
    status_msg = await query.edit_message_text(
        "📥 <b>Downloading Hi-Res Audio...</b>", 
        parse_mode='HTML'
    )

    # Ensure clean workspace
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    try:
        # Run qobuz-dl in a non-blocking way using asyncio
        process = await asyncio.create_subprocess_exec(
            "qobuz-dl", "dl", url, 
            "-q", "27", 
            "-d", DOWNLOAD_DIR,
            "--embed-art",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()

        # Find the .flac file in subfolders
        files = glob.glob(f"{DOWNLOAD_DIR}/**/*.flac", recursive=True)

        if files:
            audio_path = files[0]
            filename = os.path.basename(audio_path)
            
            with open(audio_path, 'rb') as f:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    caption="✨ <i>Source: Qobuz 24-bit Lossless</i>",
                    parse_mode='HTML',
                    title=filename.replace(".flac", ""),
                    read_timeout=3000 # Critical for large files
                )
            
            # Final Cleanup
            shutil.rmtree(DOWNLOAD_DIR)
            await status_msg.delete()
        else:
            logger.error(f"File search failed. Output: {stdout.decode()}")
            await query.edit_message_text("❌ Error: Audio file not found.")

    except Exception as e:
        logger.error(f"Download failed: {e}")
        await query.edit_message_text(f"❌ <b>Download Error:</b> {str(e)}", parse_mode='HTML')

if __name__ == '__main__':
    if not TOKEN:
        logger.error("Missing BOT_TOKEN environment variable!")
        sys.exit(1)

    # Start Flask Health Server in a separate thread
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Initialize the Telegram Application
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_dl))
    
    logger.info("Bot is initializing...")

    # drop_pending_updates=True clears old conflict errors on start
    # stop_signals are handled automatically by run_polling
    app.run_polling(drop_pending_updates=True)
