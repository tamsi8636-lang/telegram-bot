import telebot
import pandas as pd
import time
from telebot.apihelper import ApiTelegramException
from flask import Flask, request
import threading
import logging

# Setup logging to show info level logs with timestamps
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Flask minimal web server to keep Render happy ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is running."

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def run_bot():
    """Run Telegram bot with auto-reconnect using exponential backoff."""
    delay = 5
    while True:
        try:
            logging.info("🚀 Starting polling...")
            bot.polling(skip_pending=True, none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            logging.error(f"❌ Polling error: {e}. Restarting in {delay}s...")
            time.sleep(delay)
            delay = min(delay * 2, 60)  # gandakan delay sampai max 60s
        else:
            delay = 5  # reset delay kalau berjaya run

def keep_alive():
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_bot).start()

# === CONFIG ===
TOKEN = "8201238992:AAGZeU59gksGe6y6EE3ljETNim-RpjZjCCg"
EXCEL_FILE = "ID DELIMA - DATA FEED CHATBOT.xlsx"

bot = telebot.TeleBot(TOKEN)

# === LOAD EXCEL ===
def load_excel():
    try:
        df = pd.read_excel(EXCEL_FILE)
        df['Nama Murid'] = df['Nama Murid'].astype(str).str.strip().str.upper()
        logging.info("✅ Excel loaded successfully")
        return df
    except FileNotFoundError:
        logging.error("❌ Excel file not found. Make sure it's in the same folder.")
        return pd.DataFrame()

df = load_excel()

# === HANDLERS ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    logging.info(f"Received /start from {message.from_user.username} ({message.from_user.id})")
    bot.reply_to(
        message,
        "Sila isi nama penuh murid dan hantar, pastikan tiada kesalahan ejaan pada nama."
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    logging.info(f"Received /help from {message.from_user.username} ({message.from_user.id})")
    help_text = (
        "**Panduan Penggunaan Bot**\n"
        "1. Hantar nama penuh murid untuk semakan.\n"
        "2. Pastikan tiada kesalahan ejaan pada nama.\n"
        "3. Jika berkaitan kata laluan, sila hubungi guru kelas untuk bantuan set semula.\n"
        "4. Gunakan arahan /start untuk mula semula."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

# Keyword untuk detect mesej berkaitan password
PASSWORD_KEYWORDS = [
    "password", "kata laluan",
    "lupa password", "lupa kata laluan",
    "reset password", "reset kata laluan"
]

# Handler khas untuk detect mesej berkaitan password
@bot.message_handler(func=lambda message: any(keyword in message.text.lower() for keyword in PASSWORD_KEYWORDS))
def handle_password(message):
    logging.info(f"Password help requested by {message.from_user.username} ({message.from_user.id})")
    bot.reply_to(
        message,
        "Sekiranya anda menghadapi masalah berkaitan kata laluan, sila hubungi guru kelas untuk mendapatkan bantuan dan proses set semula kata laluan."
    )

# Handler default untuk carian nama
@bot.message_handler(func=lambda message: True)
def send_info(message):
    try:
        logging.info(f"Received message: '{message.text}' from {message.from_user.username} ({message.from_user.id})")
        search_name = message.text.strip().upper()
        logging.info(f"Searching for name: '{search_name}'")

        if df.empty:
            logging.warning("Excel data is empty!")
            bot.reply_to(message, "❌ Data tidak tersedia sekarang.")
            return

        matches = df[df['Nama Murid'].str.contains(search_name, case=False, na=False)]
        logging.info(f"Matches found:\n{matches[['Nama Murid']]}")

        if matches.empty:
            logging.info("No matching name found.")
            bot.reply_to(message, "Maaf, nama tidak dijumpai.")
        else:
            row = matches.iloc[0]

            reply_text = (
                f"Nama Murid: {row['Nama Murid']}\n"
                f"Email: {row.iloc[1]}\n"
                f"Kata Laluan: {row.iloc[2]}"
            )

            try:
                bot.reply_to(message, reply_text)
                logging.info(f"Replied with data for {row['Nama Murid']}")
            except ApiTelegramException as e:
                if e.error_code == 429:
                    retry_after = int(e.result_json['parameters']['retry_after'])
                    logging.warning(f"⏳ Rate limit hit, retrying after {retry_after}s")
                    time.sleep(retry_after)
                    bot.reply_to(message, reply_text)
    except Exception as e:
        logging.error(f"Error in send_info handler: {e}")
        bot.reply_to(message, "Maaf, berlaku ralat dalam sistem.")

# === START EVERYTHING ===
logging.info("🚀 Starting bot and web server...")
keep_alive()
