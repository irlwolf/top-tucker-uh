import os
import sys
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# We use .get() to avoid crashing, then check if it's actually there
TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("<b>Hi-Res 24-bit Downloader</b>\nUse /search [song] or send a link.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        return await update.message.reply_text("Usage: /search artist song")
    
    # Example button
    btn = [[InlineKeyboardButton("Download 24-bit FLAC", callback_data="dl_track_123")]]
    await update.message.reply_text(f"Results for: {query}", reply_markup=InlineKeyboardMarkup(btn))

async def handle_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("📥 Downloading 24-bit Master Stream...")
    
    # Ensure the downloads folder exists
    os.makedirs("downloads", exist_ok=True)
    output_file = "downloads/HiRes_Audio.flac"
    
    # Placeholder: Create a dummy file for testing if it doesn't exist
    if not os.path.exists(output_file):
        with open(output_file, "wb") as f:
            f.write(b"Dummy Hi-Res Data")

    with open(output_file, 'rb') as f:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=f,
            caption="✨ 24-bit / 96kHz Lossless",
            read_timeout=1000  # Crucial for large Hi-Res files
        )

if __name__ == '__main__':
    # --- SAFETY CHECK ---
    if not TOKEN:
        logger.error("BOT_TOKEN is missing! Make sure to set it in Koyeb Environment Variables.")
        sys.exit(1)

    # Build Application
    builder = ApplicationBuilder().token(TOKEN)
    
    # Only use base_url if API_URL is actually provided
    if API_URL:
        builder.base_url(API_URL)
        logger.info(f"Using custom API Server: {API_URL}")

    app = builder.build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(handle_dl))
    
    logger.info("Bot started successfully.")
    app.run_polling()
