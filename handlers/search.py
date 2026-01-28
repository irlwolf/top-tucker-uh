from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from utils.search_api import hifi_search

async def search_handler(update, context):
    query = update.message.text
    # Instant Animation
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    results = await hifi_search(query)
    
    keyboard = []
    for res in results:
        btn = InlineKeyboardButton(f"🎧 {res['title']} (24-bit)", callback_data=f"dl_{res['id']}")
        keyboard.append([btn])
        
    await update.message.reply_text(
        f"🔍 Results for <b>{query}</b>:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
