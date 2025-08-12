import telebot
import pandas as pd
import time
from telebot.apihelper import ApiTelegramException
from flask import Flask
import threading
import logging

# Setup logging
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

# Robust polling with retry loop
def run_bot():
    while True:
        try:
            logging.info("Starting bot polling...")
            bot.polling(skip_pending=True, none_stop=True)
        except ApiTelegramException as e:
            # Handle Telegram API exceptions like rate limiting
            if e.error_code == 429:
                retry_after = int(e.result_json['parameters']['retry_after'])
                logging.warning(f"Rate limit hit. Sleeping for {retry_after} seconds.")
                time.sleep(retry_after)
            else:
                logging.error(f"Telegram API error: {e}")
                time.sleep(5)  # wait a bit before retrying
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(5)  # wait a bit before retrying

def keep_alive():
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_bot).start()

# === CONFIG ===
TOKEN = "8201238992:AAGZeU59gksGe6y6EE3ljETNim-RpjZjCCg"
EXCEL_FILE = "ID DELIMA - DATA FEED CHATBOT.xlsx"

bot = telebot.TeleBot(TOKEN)

# === LOAD EXCEL ===
try:
    df = pd.read_excel(EXCEL_FILE)
    df['Nama Murid'] = df['Nama Murid'].astype(str).str.strip().str.upper()
    logging.info("✅ Excel loaded successfully")
except FileNotFoundError:
    logging.error("❌ Excel file not found. Make sure it's in the same folder.")
    df = pd.DataFrame()

# === HANDLERS ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    logging.info(f"Received /start from {message.from_user.username} ({message.from_user.id})")
    bot.reply_to(
        message,
        "Sila isi nama penuh murid dan hantar, pastikan tiada kesalahan ejaan pada nama."
    )

@bot.message_handler(func=lambda message: True)
def send_info(message):
    logging.info(f"Received message: {message.text} from {message.from_user.username} ({message.from_user.id})")
    search_name = message.text.strip().upper()

    if df.empty:
        logging.warning("Excel data is empty!")
        bot.reply_to(message, "❌ Data tidak tersedia sekarang.")
        return

    matches = df[df['Nama Murid'].str.contains(search_name, case=False, na=False)]

    if matches.empty:
        logging.info("No matching name found.")
        bot.reply_to(message, "Maaf, nama tidak dijumpai.")
    else:
        row = matches.iloc[0]

        reply_text = (
            f"Nama Murid: {row['Nama Murid']}\n"
            f"Email: {row.iloc[1]}\n"
            f"Password: {row.iloc[2]}"
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

# === START EVERYTHING ===
logging.info("🚀 Starting bot and web server...")
keep_alive()
