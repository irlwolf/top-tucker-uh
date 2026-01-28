import os, subprocess, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Setup Logging
logging.basicConfig(level=logging.INFO)

# Config from .env via Docker
TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL") # Points to local server

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("<b>Hi-Res 24-bit Downloader</b>\nUse /search [song] or send a link.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        return await update.message.reply_text("Usage: /search artist song")
    
    # Mocking search results - in real bot, call qobuz_dl.search(query)
    btn = [[InlineKeyboardButton("Download 24-bit FLAC", callback_data="dl_track_123")]]
    await update.message.reply_text(f"Results for: {query}", reply_markup=InlineKeyboardMarkup(btn))

async def handle_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    msg = await query.edit_message_text("📥 Downloading 24-bit Master Stream...")
    
    # FFmpeg command for true 24-bit conversion
    # -sample_fmt s32 ensures 24-bit depth
    # -ar 96000 ensures high sample rate
    output_file = "downloads/HiRes_Audio.flac"
    
    # Example shell command (replace with real downloader logic)
    # subprocess.run(["qobuz-dl", "dl", "URL", "-q", "27", "-o", "./downloads"])

    with open(output_file, 'rb') as f:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=f,
            caption="✨ 24-bit / 96kHz Lossless",
            read_timeout=1000 # Critical for large files
        )

if __name__ == '__main__':
    # Initialize with the Local API Server base_url
    app = ApplicationBuilder().token(TOKEN).base_url(API_URL).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(handle_dl))
    
    app.run_polling()
