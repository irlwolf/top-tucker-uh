import os
import sys
import logging
import threading
import subprocess
import glob
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- 1. HEALTH CHECK SERVER (For Koyeb Free Tier) ---
health_app = Flask(__name__)
@health_app.route('/')
def health_check(): return "OK", 200

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    health_app.run(host='0.0.0.0', port=port)

# --- 2. BOT LOGIC ---
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("<b>Hi-Res Downloader</b>\nSend a Qobuz link or search.")

async def handle_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # query.data would be the URL or ID you passed in search
    url = query.data 
    status_msg = await query.edit_message_text("📥 Downloading Hi-Res FLAC...")

    download_path = "downloads"
    os.makedirs(download_path, exist_ok=True)

    try:
        # qobuz-dl command (-q 27 for max 24-bit quality)
        subprocess.run(["qobuz-dl", "dl", url, "-q", "27", "-d", download_path], check=True)

        # Find the actual .flac file (it might be in a subfolder)
        files = glob.glob(f"{download_path}/**/*.flac", recursive=True)

        if files:
            audio_file = files[0]
            with open(audio_file, 'rb') as f:
                # Use send_audio so Telegram shows the Play button
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    caption="✨ 24-bit Lossless Audio",
                    title=os.path.basename(audio_file),
                    read_timeout=1000
                )
            os.remove(audio_file) # Clean up to save Koyeb disk space
            await status_msg.delete()
        else:
            await query.edit_message_text("❌ Error: Could not find the audio file.")

    except Exception as e:
        await query.edit_message_text(f"❌ Download failed: {str(e)}")

if __name__ == '__main__':
    if not TOKEN: sys.exit("No BOT_TOKEN found!")
    threading.Thread(target=run_health_server, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_dl))
    app.run_polling()
