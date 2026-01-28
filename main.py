from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN, BASE_URL
from handlers.search import search_handler
from database.models import init_db

def main():
    init_db() # Ensure DB is ready
    
    app = ApplicationBuilder().token(BOT_TOKEN).base_url(BASE_URL).build()
    
    # Registering Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
