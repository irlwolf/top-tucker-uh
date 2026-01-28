import os
import sys
import logging
import threading
import subprocess
import glob
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- 1. KOYEB HEALTH CHECK (Required for Free Tier) ---
health_app = Flask(__name__)
@health_app.route('/')
def health(): return "OK", 200

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    health_app.run(host='0.0.0.0', port=port)

# --- 2. LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING) # Hide token URLs from logs
logger = logging.getLogger(__name__)

# --- 3. CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("<b>🎵 Hi-Res 24-bit Downloader</b>\nSend a Qobuz link or use /search.")

async def handle_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    url = query.data 
    status_msg = await query.edit_message_text("📥 <b>Downloading Hi-Res Audio...</b>", parse_mode='HTML')

    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)

    try:
        # qobuz-dl command (-q 27 = Hi-Res Max, --embed-art for covers)
        subprocess.run([
            "qobuz-dl", "dl", url, 
            "-q", "27", 
            "-d", download_dir,
            "--embed-art"
        ], check=True)

        # Locate the .flac file (searching subfolders)
        files = glob.glob(f"{download_dir}/**/*.flac", recursive=True)

        if files:
            audio_path = files[0]
            filename = os.path.basename(audio_path)
            
            with open(audio_path, 'rb') as f:
                # send_audio enables the Telegram Music Player
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    caption="✨ <i>Source: Qobuz 24-bit Lossless</i>",
                    parse_mode='HTML',
                    title=filename.replace(".flac", ""),
                    read_timeout=2000 # Increased timeout for large FLAC files
                )
            # CLEANUP: Remove files so Koyeb storage doesn't fill up
            os.remove(audio_path)
            await status_msg.delete()
        else:
            await query.edit_message_text("❌ Error: Audio file not found.")

    except Exception as e:
        logger.error(f"Download failed: {e}")
        await query.edit_message_text(f"❌ <b>Download Error:</b> {str(e)}", parse_mode='HTML')

if __name__ == '__main__':
    if not TOKEN:
        logger.error("Missing BOT_TOKEN!")
        sys.exit(1)

    # Start health server thread
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Start Bot
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_dl))
    
    logger.info("Bot is running...")
    app.run_polling()
