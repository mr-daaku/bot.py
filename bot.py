# ============================================
# TonCloude Telegram Bot
# WITHOUT Firebase Admin SDK
# Uses Firebase REST API directly
# ============================================

import os
import asyncio
import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

# ============================================
# CONFIGURATION
# ============================================

BOT_TOKEN = "8554049757:AAHAHYfMJXEEsUfvkkRGDbHkUIZm4rnW1dg"

# Firebase REST API URL
FIREBASE_URL = "https://toncloudeid-default-rtdb.firebaseio.com"

# Default Welcome Settings
DEFAULT_WELCOME_IMAGE = "https://i.postimg.cc/T2BX8Pvk/copilot-image-1767015699295.png"

DEFAULT_WELCOME_MESSAGE = """
🎮 <b>Welcome to TonCloude!</b> 💎

🚀 <b>Earn rewards by completing tasks!</b>

💰 <b>Gold</b> - Complete tasks & earn
💎 <b>Diamond</b> - Daily rewards & bonuses
🪙 <b>TON</b> - Deposit, withdraw & trade

📱 <b>Open the app below to start earning!</b>

👥 Invite friends & get <b>+1000 Gold</b> and <b>+10 Diamond</b> per referral!
"""

# Web App URL (apna URL daalo)
WEB_APP_URL = "https://AliHamza0007.github.io/TonCloude"

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# FIREBASE REST API FUNCTIONS
# ============================================

class FirebaseDB:
    """Firebase Realtime Database REST API Wrapper"""
    
    @staticmethod
    def get(path: str):
        """GET data from Firebase"""
        try:
            url = f"{FIREBASE_URL}/{path}.json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Firebase GET error: {e}")
            return None
    
    @staticmethod
    def set(path: str, data):
        """SET data in Firebase (overwrite)"""
        try:
            url = f"{FIREBASE_URL}/{path}.json"
            response = requests.put(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Firebase SET error: {e}")
            return False
    
    @staticmethod
    def update(path: str, data: dict):
        """UPDATE data in Firebase (merge)"""
        try:
            url = f"{FIREBASE_URL}/{path}.json"
            response = requests.patch(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Firebase UPDATE error: {e}")
            return False
    
    @staticmethod
    def push(path: str, data):
        """PUSH data to Firebase (auto-generate key)"""
        try:
            url = f"{FIREBASE_URL}/{path}.json"
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                return response.json().get('name')
            return None
        except Exception as e:
            logger.error(f"Firebase PUSH error: {e}")
            return None
    
    @staticmethod
    def delete(path: str):
        """DELETE data from Firebase"""
        try:
            url = f"{FIREBASE_URL}/{path}.json"
            response = requests.delete(url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Firebase DELETE error: {e}")
            return False

# Short alias
fb = FirebaseDB

# ============================================
# USER FUNCTIONS
# ============================================

def get_user(user_id: str):
    """Get user from Firebase"""
    return fb.get(f"users/{user_id}")

def create_user(user_id: str, username: str, first_name: str):
    """Create new user in Firebase"""
    user_data = {
        'userId': user_id,
        'username': username or '',
        'firstName': first_name or '',
        'gold': 100,
        'diamond': 0,
        'ton': 0,
        'createdAt': int(datetime.now().timestamp() * 1000),
        'dailyTasks': {
            'dailyCheck': 0,
            'shareApp': 0,
            'checkUpdate': 0
        },
        'referralProcessed': False
    }
    
    success = fb.set(f"users/{user_id}", user_data)
    if success:
        logger.info(f"✅ New user created: {user_id}")
    return success

def update_user(user_id: str, data: dict):
    """Update user data"""
    return fb.update(f"users/{user_id}", data)

def process_referral(referrer_id: str, new_user_id: str):
    """Process referral reward"""
    if referrer_id == new_user_id:
        return False
    
    try:
        # Check new user
        new_user = get_user(new_user_id)
        if not new_user:
            return False
        
        if new_user.get('referredBy') or new_user.get('referralProcessed'):
            logger.info(f"Referral already processed for: {new_user_id}")
            return False
        
        # Check referrer exists
        referrer = get_user(referrer_id)
        if not referrer:
            return False
        
        # Update new user
        fb.update(f"users/{new_user_id}", {
            'referredBy': referrer_id,
            'referralProcessed': True
        })
        
        # Reward referrer
        current_gold = referrer.get('gold', 0)
        current_diamond = referrer.get('diamond', 0)
        refer_data = referrer.get('refer', {})
        ref_count = len(refer_data) + 1 if refer_data else 1
        
        fb.update(f"users/{referrer_id}", {
            'gold': current_gold + 1000,
            'diamond': current_diamond + 10
        })
        fb.set(f"users/{referrer_id}/refer/{ref_count}", new_user_id)
        
        logger.info(f"🎁 Referral processed: {referrer_id} got reward for {new_user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing referral: {e}")
        return False

def get_user_referrals(user_id: str):
    """Get user referral count"""
    refer_data = fb.get(f"users/{user_id}/refer")
    if refer_data and isinstance(refer_data, dict):
        return len(refer_data)
    return 0

# ============================================
# BOT SETTINGS FUNCTIONS
# ============================================

def get_welcome_settings():
    """Get welcome message settings from Firebase"""
    return fb.get("botSettings/welcome")

def get_bot_buttons():
    """Get bot buttons from Firebase"""
    return fb.get("botSettings/buttons")

def get_required_channels():
    """Get required channels from Firebase"""
    return fb.get("botSettings/channels")

# ============================================
# BROADCAST FUNCTIONS
# ============================================

def get_pending_broadcasts():
    """Get pending broadcasts"""
    all_broadcasts = fb.get("botBroadcasts")
    if not all_broadcasts:
        return {}
    
    pending = {}
    for key, value in all_broadcasts.items():
        if isinstance(value, dict) and value.get('status') == 'pending':
            pending[key] = value
    return pending

def update_broadcast_status(broadcast_id: str, status: str, sent_count: int = 0, fail_count: int = 0):
    """Update broadcast status"""
    fb.update(f"botBroadcasts/{broadcast_id}", {
        'status': status,
        'sentCount': sent_count,
        'failCount': fail_count,
        'sentAt': int(datetime.now().timestamp() * 1000)
    })

def get_all_user_ids():
    """Get all user IDs for broadcast"""
    users = fb.get("users")
    if users and isinstance(users, dict):
        return list(users.keys())
    return []

# ============================================
# DEPOSIT FUNCTIONS
# ============================================

def get_user_deposits(user_id: str):
    """Get user deposits"""
    return fb.get(f"processedDeposits/{user_id}")

def get_user_withdrawals(user_id: str):
    """Get user withdrawals"""
    return fb.get(f"users/{user_id}/withdrawals")

# ============================================
# PROMO CODE FUNCTIONS
# ============================================

def get_promo_code(code: str):
    """Get promo code details"""
    return fb.get(f"promoCodes/{code.upper()}")

def claim_promo_code(user_id: str, code: str):
    """Claim a promo code"""
    code = code.upper()
    promo = get_promo_code(code)
    
    if not promo:
        return {'success': False, 'error': 'Invalid promo code'}
    
    # Check if already used by this user
    used_by = fb.get(f"promoCodes/{code}/usedBy/{user_id}")
    if used_by:
        return {'success': False, 'error': 'Already claimed'}
    
    # Check limit
    used_count = promo.get('usedCount', 0)
    limit = promo.get('limit', 0)
    if used_count >= limit:
        return {'success': False, 'error': 'Promo code expired'}
    
    # Get user
    user = get_user(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}
    
    # Apply rewards
    gold_reward = promo.get('gold', 0)
    diamond_reward = promo.get('diamond', 0)
    ton_reward = promo.get('ton', 0)
    
    new_gold = user.get('gold', 0) + gold_reward
    new_diamond = user.get('diamond', 0) + diamond_reward
    new_ton = user.get('ton', 0) + ton_reward
    
    # Update user
    fb.update(f"users/{user_id}", {
        'gold': new_gold,
        'diamond': new_diamond,
        'ton': new_ton
    })
    
    # Mark promo as used
    fb.update(f"promoCodes/{code}", {
        'usedCount': used_count + 1
    })
    fb.set(f"promoCodes/{code}/usedBy/{user_id}", int(datetime.now().timestamp() * 1000))
    
    return {
        'success': True,
        'gold': gold_reward,
        'diamond': diamond_reward,
        'ton': ton_reward
    }

# ============================================
# BOT COMMANDS
# ============================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = str(user.id)
    
    logger.info(f"👤 /start from user: {user_id} (@{user.username})")
    
    # Get start parameter (referral)
    start_param = None
    if context.args and len(context.args) > 0:
        start_param = context.args[0]
        logger.info(f"📎 Referral param: {start_param}")
    
    # Check/Create user
    existing_user = get_user(user_id)
    if not existing_user:
        create_user(user_id, user.username, user.first_name)
        
        # Process referral if exists
        if start_param and start_param != user_id:
            process_referral(start_param, user_id)
    
    # Get welcome settings from Firebase or use defaults
    welcome_settings = get_welcome_settings()
    custom_buttons = get_bot_buttons()
    
    # Prepare message
    if welcome_settings and welcome_settings.get('message'):
        welcome_message = welcome_settings.get('message')
        welcome_image = welcome_settings.get('image', DEFAULT_WELCOME_IMAGE)
    else:
        welcome_message = DEFAULT_WELCOME_MESSAGE
        welcome_image = DEFAULT_WELCOME_IMAGE
    
    # Prepare keyboard
    keyboard = []
    
    # Add custom buttons from Firebase
    if custom_buttons and isinstance(custom_buttons, list):
        for btn in custom_buttons:
            if isinstance(btn, dict) and btn.get('text') and btn.get('url'):
                keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
    
    # Default buttons
    keyboard.extend([
        [InlineKeyboardButton("🚀 Open App", web_app=WebAppInfo(url=WEB_APP_URL))],
        [
            InlineKeyboardButton("👥 Community", url="https://t.me/TonCloude_chat"),
            InlineKeyboardButton("📢 Updates", url="https://t.me/TonCloude_updates")
        ],
        [InlineKeyboardButton("🎁 Invite Friends", callback_data="refer")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send message with image
    try:
        if welcome_image:
            await update.message.reply_photo(
                photo=welcome_image,
                caption=welcome_message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                welcome_message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error sending welcome: {e}")
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    user_id = str(update.effective_user.id)
    
    user_data = get_user(user_id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ <b>User not found!</b>\n\nPlease use /start first.",
            parse_mode=ParseMode.HTML
        )
        return
    
    gold = user_data.get('gold', 0)
    diamond = user_data.get('diamond', 0)
    ton = user_data.get('ton', 0)
    referrals = get_user_referrals(user_id)
    
    # Get deposits count
    deposits = get_user_deposits(user_id)
    deposit_count = len(deposits) if deposits else 0
    
    # Get withdrawals
    withdrawals = get_user_withdrawals(user_id)
    pending_wd = 0
    if withdrawals:
        for wd in withdrawals.values():
            if isinstance(wd, dict) and wd.get('status') == 'pending':
                pending_wd += 1
    
    message = f"""
💼 <b>Your Balance</b>

🪙 <b>Gold:</b> {gold:,}
💎 <b>Diamond:</b> {diamond:,}
💰 <b>TON:</b> {ton:.4f}

📊 <b>Stats:</b>
👥 Referrals: {referrals}
📥 Deposits: {deposit_count}
📤 Pending Withdrawals: {pending_wd}

📱 Open the app to earn more rewards!
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Open App", web_app=WebAppInfo(url=WEB_APP_URL))],
        [
            InlineKeyboardButton("🎁 Invite", callback_data="refer"),
            InlineKeyboardButton("🎟️ Promo", callback_data="promo")
        ]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def refer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /refer command"""
    user_id = str(update.effective_user.id)
    
    refer_link = f"https://t.me/TonCloudeBot?start={user_id}"
    referral_count = get_user_referrals(user_id)
    
    message = f"""
🎁 <b>Invite Friends & Earn!</b>

Get rewards for each friend who joins:
💰 <b>+1000 Gold</b>
💎 <b>+10 Diamond</b>

👥 <b>Your Referrals:</b> {referral_count}
💵 <b>Total Earned:</b> {referral_count * 1000:,} Gold, {referral_count * 10:,} Diamond

📎 <b>Your Referral Link:</b>
<code>{refer_link}</code>

<i>Tap to copy, then share with friends!</i>
"""
    
    share_text = "🎮 Join TonCloude and earn crypto rewards! 💰💎"
    share_url = f"https://t.me/share/url?url={refer_link}&text={share_text}"
    
    keyboard = [
        [InlineKeyboardButton("📤 Share Link", url=share_url)],
        [InlineKeyboardButton("📋 Copy Link", callback_data="copy_refer")],
        [InlineKeyboardButton("🚀 Open App", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /promo command"""
    user_id = str(update.effective_user.id)
    
    # Check if code provided
    if context.args and len(context.args) > 0:
        code = context.args[0]
        result = claim_promo_code(user_id, code)
        
        if result['success']:
            rewards = []
            if result.get('gold', 0) > 0:
                rewards.append(f"🪙 +{result['gold']:,} Gold")
            if result.get('diamond', 0) > 0:
                rewards.append(f"💎 +{result['diamond']:,} Diamond")
            if result.get('ton', 0) > 0:
                rewards.append(f"💰 +{result['ton']:.4f} TON")
            
            message = f"""
✅ <b>Promo Code Claimed!</b>

🎁 <b>Rewards:</b>
{chr(10).join(rewards)}

📱 Open the app to see your new balance!
"""
        else:
            message = f"❌ <b>Error:</b> {result['error']}"
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    else:
        message = """
🎟️ <b>Promo Codes</b>

Enter a promo code to claim rewards!

<b>Usage:</b>
<code>/promo YOURCODE</code>

📱 Or enter codes in the app!
"""
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deposit command"""
    user_id = str(update.effective_user.id)
    
    deposit_wallet = "UQDqx6Ds4sZdlQI9ooU22YM0eBSqxIx03rPF2ylB35a3xdWc"
    
    message = f"""
📥 <b>Deposit TON</b>

Send TON to this address with your User ID as memo:

<b>Wallet Address:</b>
<code>{deposit_wallet}</code>

<b>Your Memo (User ID):</b>
<code>{user_id}</code>

⚠️ <b>Important:</b>
• Minimum deposit: 0.01 TON
• Always include your User ID as memo
• Deposits are processed within 5 minutes

📱 Or deposit easily through the app!
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Deposit in App", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("📋 Copy Address", callback_data="copy_deposit_addr")],
        [InlineKeyboardButton("📋 Copy Memo", callback_data="copy_memo")]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /withdraw command"""
    user_id = str(update.effective_user.id)
    
    user_data = get_user(user_id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ Please use /start first!",
            parse_mode=ParseMode.HTML
        )
        return
    
    gold = user_data.get('gold', 0)
    diamond = user_data.get('diamond', 0)
    
    message = f"""
📤 <b>Withdraw</b>

💼 <b>Your Balance:</b>
🪙 Gold: {gold:,}
💎 Diamond: {diamond:,}

📋 <b>Withdrawal Rules:</b>
• Minimum: 100,000 Gold
• Fee: 20,000 Diamond per 100K Gold
• Rate: 100,000 Gold = 1 TON

⚠️ <b>Requirements:</b>
• You need: {100000:,} Gold minimum
• Diamond fee: {20000:,} Diamond per withdrawal

📱 Withdraw through the app for easy process!
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Withdraw in App", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - Show user statistics"""
    user_id = str(update.effective_user.id)
    
    user_data = get_user(user_id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ Please use /start first!",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Get various stats
    referrals = get_user_referrals(user_id)
    deposits = get_user_deposits(user_id)
    withdrawals = get_user_withdrawals(user_id)
    
    deposit_count = len(deposits) if deposits else 0
    total_deposited = 0
    if deposits:
        for dep in deposits.values():
            if isinstance(dep, (int, float)):
                total_deposited += dep
    
    withdrawal_count = 0
    pending_wd = 0
    completed_wd = 0
    if withdrawals:
        for wd in withdrawals.values():
            if isinstance(wd, dict):
                withdrawal_count += 1
                if wd.get('status') == 'pending':
                    pending_wd += 1
                elif wd.get('status') == 'paid':
                    completed_wd += 1
    
    # Calculate account age
    created_at = user_data.get('createdAt', 0)
    if created_at:
        days_old = (datetime.now().timestamp() * 1000 - created_at) / (1000 * 60 * 60 * 24)
        days_old = int(days_old)
    else:
        days_old = 0
    
    message = f"""
📊 <b>Your Statistics</b>

👤 <b>Account:</b>
📅 Account Age: {days_old} days
🆔 User ID: <code>{user_id}</code>

💰 <b>Balance:</b>
🪙 Gold: {user_data.get('gold', 0):,}
💎 Diamond: {user_data.get('diamond', 0):,}
💵 TON: {user_data.get('ton', 0):.4f}

📈 <b>Activity:</b>
👥 Referrals: {referrals}
💵 Referral Earnings: {referrals * 1000:,} Gold

📥 <b>Deposits:</b>
Total: {deposit_count}
Amount: {total_deposited:.4f} TON

📤 <b>Withdrawals:</b>
Total: {withdrawal_count}
✅ Completed: {completed_wd}
⏳ Pending: {pending_wd}
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Open App", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    message = """
📚 <b>TonCloude Bot Commands</b>

🎮 <b>Basic:</b>
/start - Start bot & open app
/help - Show this help

💰 <b>Balance:</b>
/balance - Check your balance
/stats - Detailed statistics

💵 <b>Transactions:</b>
/deposit - How to deposit TON
/withdraw - How to withdraw

🎁 <b>Earn More:</b>
/refer - Get referral link
/promo [code] - Claim promo code

━━━━━━━━━━━━━━━━━━

💡 <b>How to Earn:</b>
• ✅ Complete daily tasks
• 👥 Invite friends (referrals)
• 📥 Deposit TON & trade
• 🎯 Complete special tasks

🎁 <b>Referral Rewards:</b>
+1000 Gold & +10 Diamond per friend!

📱 <b>Open the app for full features!</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Open App", web_app=WebAppInfo(url=WEB_APP_URL))],
        [
            InlineKeyboardButton("👥 Community", url="https://t.me/TonCloude_chat"),
            InlineKeyboardButton("📢 Updates", url="https://t.me/TonCloude_updates")
        ]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard command"""
    users = fb.get("users")
    
    if not users:
        await update.message.reply_text("❌ No data available")
        return
    
    # Sort users by gold
    user_list = []
    for uid, data in users.items():
        if isinstance(data, dict):
            user_list.append({
                'id': uid,
                'name': data.get('firstName') or data.get('username') or uid[:8],
                'gold': data.get('gold', 0),
                'diamond': data.get('diamond', 0)
            })
    
    # Sort by gold descending
    user_list.sort(key=lambda x: x['gold'], reverse=True)
    
    # Top 10
    top_users = user_list[:10]
    
    leaderboard_text = ""
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, u in enumerate(top_users):
        leaderboard_text += f"{medals[i]} <b>{u['name']}</b> - {u['gold']:,} Gold\n"
    
    # Find current user rank
    user_id = str(update.effective_user.id)
    user_rank = None
    for i, u in enumerate(user_list):
        if u['id'] == user_id:
            user_rank = i + 1
            break
    
    message = f"""
🏆 <b>Leaderboard - Top 10</b>

{leaderboard_text}
━━━━━━━━━━━━━━━━━━

👤 <b>Your Rank:</b> #{user_rank if user_rank else 'N/A'}

📱 Complete tasks to climb the leaderboard!
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Open App", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ============================================
# CALLBACK HANDLERS
# ============================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    
    if data == "refer":
        refer_link = f"https://t.me/TonCloudeBot?start={user_id}"
        referral_count = get_user_referrals(user_id)
        
        message = f"""
🎁 <b>Invite Friends & Earn!</b>

💰 <b>+1000 Gold</b> per friend
💎 <b>+10 Diamond</b> per friend

👥 <b>Your Referrals:</b> {referral_count}

📎 <b>Your Link:</b>
<code>{refer_link}</code>
"""
        
        share_text = "🎮 Join TonCloude and earn crypto rewards!"
        share_url = f"https://t.me/share/url?url={refer_link}&text={share_text}"
        
        keyboard = [[InlineKeyboardButton("📤 Share Link", url=share_url)]]
        
        await query.message.reply_text(
            message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "promo":
        message = """
🎟️ <b>Enter Promo Code</b>

Use command:
<code>/promo YOURCODE</code>

Example:
<code>/promo WELCOME2024</code>
"""
        await query.message.reply_text(message, parse_mode=ParseMode.HTML)
    
    elif data == "balance":
        user_data = get_user(user_id)
        
        if user_data:
            message = f"""
💼 <b>Your Balance</b>

🪙 Gold: {user_data.get('gold', 0):,}
💎 Diamond: {user_data.get('diamond', 0):,}
💰 TON: {user_data.get('ton', 0):.4f}
"""
            await query.message.reply_text(message, parse_mode=ParseMode.HTML)
    
    elif data == "copy_refer":
        refer_link = f"https://t.me/TonCloudeBot?start={user_id}"
        await query.message.reply_text(
            f"📋 <b>Your Referral Link:</b>\n\n<code>{refer_link}</code>",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "copy_deposit_addr":
        deposit_wallet = "UQDqx6Ds4sZdlQI9ooU22YM0eBSqxIx03rPF2ylB35a3xdWc"
        await query.message.reply_text(
            f"📋 <b>Deposit Address:</b>\n\n<code>{deposit_wallet}</code>",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "copy_memo":
        await query.message.reply_text(
            f"📋 <b>Your Memo:</b>\n\n<code>{user_id}</code>",
            parse_mode=ParseMode.HTML
        )

# ============================================
# BROADCAST PROCESSOR
# ============================================

async def process_broadcasts(app: Application):
    """Process pending broadcasts"""
    try:
        broadcasts = get_pending_broadcasts()
        
        for broadcast_id, broadcast in broadcasts.items():
            logger.info(f"📢 Processing broadcast: {broadcast_id}")
            
            # Update status to sending
            fb.update(f"botBroadcasts/{broadcast_id}", {'status': 'sending'})
            
            # Get all user IDs
            user_ids = get_all_user_ids()
            
            sent_count = 0
            fail_count = 0
            
            message = broadcast.get('message', '')
            image = broadcast.get('image')
            button = broadcast.get('button')
            
            # Prepare keyboard
            keyboard = []
            if button and isinstance(button, dict) and button.get('text') and button.get('url'):
                keyboard = [[InlineKeyboardButton(button['text'], url=button['url'])]]
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            for uid in user_ids:
                try:
                    if image:
                        await app.bot.send_photo(
                            chat_id=int(uid),
                            photo=image,
                            caption=message,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup
                        )
                    else:
                        await app.bot.send_message(
                            chat_id=int(uid),
                            text=message,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup
                        )
                    sent_count += 1
                except Exception as e:
                    fail_count += 1
                    logger.debug(f"Failed to send to {uid}: {e}")
                
                # Rate limiting
                await asyncio.sleep(0.05)
            
            # Update status
            update_broadcast_status(broadcast_id, 'sent', sent_count, fail_count)
            logger.info(f"✅ Broadcast sent: {sent_count} success, {fail_count} failed")
            
    except Exception as e:
        logger.error(f"Broadcast processor error: {e}")


async def broadcast_scheduler(app: Application):
    """Run broadcast processor periodically"""
    while True:
        await asyncio.sleep(30)
        await process_broadcasts(app)

# ============================================
# ERROR HANDLER
# ============================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Error: {context.error}")

# ============================================
# MAIN
# ============================================

def main():
    """Start the bot"""
    logger.info("🚀 Starting TonCloude Bot...")
    logger.info(f"📡 Firebase URL: {FIREBASE_URL}")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("refer", refer_command))
    app.add_handler(CommandHandler("promo", promo_command))
    app.add_handler(CommandHandler("deposit", deposit_command))
    app.add_handler(CommandHandler("withdraw", withdraw_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Add callback handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    logger.info("🤖 Bot is running!")
    logger.info("📋 Commands: /start, /balance, /refer, /promo, /deposit, /withdraw, /stats, /leaderboard, /help")
    
    # Run bot
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
