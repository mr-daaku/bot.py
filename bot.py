from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import requests
import asyncio

# Bot token
BOT_TOKEN = "8554049757:AAH8fOJoWTZCEd98rdEnnxKZTso2Vwh-1Is"

# Firebase Realtime Database URL
FIREBASE_URL = "https://toncloudeid-default-rtdb.firebaseio.com"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    
    # Message text
    message_text = """🎮 Welcome to TonCloude! 💎

🚀 Earn rewards by completing tasks!

💰 Gold - Complete tasks & earn
💎 Diamond - Daily rewards & bonuses
🪙 TON - Deposit, withdraw & trade

📱 Open the app below to start earning!

👥 Invite friends & get +1000 Gold and +10 Diamond per referral!"""
    
    # Image URL
    image_url = "https://i.postimg.cc/T2BX8Pvk/copilot-image-1767015699295.png"
    
    # Inline keyboard buttons
    keyboard = [
        [InlineKeyboardButton("🚀 Open App", url="https://t.me/TonCloudeBot/TonCloude")],
        [
            InlineKeyboardButton("👥 Community", url="https://t.me/TonCloude_chat"),
            InlineKeyboardButton("📢 Updates", url="https://t.me/TonCloude_updates")
        ],
        [InlineKeyboardButton("🎁 Invite Friends", callback_data="invite_friends")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send photo with caption and buttons
    await update.message.reply_photo(
        photo=image_url,
        caption=message_text,
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "invite_friends":
        user_id = query.from_user.id
        invite_link = f"https://t.me/TonCloudeBot/TonCloude?startapp={user_id}"
        
        invite_text = f"""🎁 Invite Friends & Earn Rewards!

Your referral link:
{invite_link}

Share this link with friends and get:
💰 +1000 Gold
💎 +10 Diamond

per referral!"""
        
        await query.edit_message_caption(
            caption=invite_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")
            ]])
        )
    
    elif query.data == "back_to_main":
        message_text = """🎮 Welcome to TonCloude! 💎

🚀 Earn rewards by completing tasks!

💰 Gold - Complete tasks & earn
💎 Diamond - Daily rewards & bonuses
🪙 TON - Deposit, withdraw & trade

📱 Open the app below to start earning!

👥 Invite friends & get +1000 Gold and +10 Diamond per referral!"""
        
        keyboard = [
            [InlineKeyboardButton("🚀 Open App", url="https://t.me/TonCloudeBot/TonCloude")],
            [
                InlineKeyboardButton("👥 Community", url="https://t.me/TonCloude_chat"),
                InlineKeyboardButton("📢 Updates", url="https://t.me/TonCloude_updates")
            ],
            [InlineKeyboardButton("🎁 Invite Friends", callback_data="invite_friends")]
        ]
        
        await query.edit_message_caption(
            caption=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def fetch_messages_from_firebase():
    """Firebase se messages fetch karein"""
    try:
        response = requests.get(f"{FIREBASE_URL}/msg.json")
        if response.status_code == 200:
            data = response.json()
            return data if data else {}
        else:
            print(f"Firebase error: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error fetching from Firebase: {e}")
        return {}

def delete_message_from_firebase(user_id):
    """Message send karne ke baad Firebase se delete karein"""
    try:
        response = requests.delete(f"{FIREBASE_URL}/msg/{user_id}.json")
        if response.status_code == 200:
            print(f"Message deleted for user {user_id}")
        else:
            print(f"Error deleting message: {response.status_code}")
    except Exception as e:
        print(f"Error deleting from Firebase: {e}")

async def check_and_send_messages(context: ContextTypes.DEFAULT_TYPE):
    """Firebase se messages check karein aur users ko send karein"""
    messages = fetch_messages_from_firebase()
    
    if messages:
        for user_id, message in messages.items():
            try:
                # Message send karein
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=message,
                    parse_mode='HTML'
                )
                print(f"Message sent to user {user_id}")
                
                # Message send hone ke baad Firebase se delete karein
                delete_message_from_firebase(user_id)
                
                # Rate limiting ke liye thoda wait karein
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error sending message to {user_id}: {e}")

def main():
    """Main function to run the bot"""
    # Application banayein
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers add karein
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Job queue setup - har 10 seconds mein Firebase check karega
    job_queue = application.job_queue
    job_queue.run_repeating(check_and_send_messages, interval=10, first=5)
    
    # Bot ko run karein
    print("Bot start ho gaya hai...")
    print("Firebase broadcast system active hai...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()