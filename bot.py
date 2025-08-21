import telebot
import pandas as pd
import time
from telebot.apihelper import ApiTelegramException
from flask import Flask
import threading
import logging

# === Setup logging ===
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Flask server (untuk Render/uptime) ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is running."

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# === CONFIG ===
TOKEN = "YOUR_BOT_TOKEN_HERE"   # <-- Ganti dengan token sebenar
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

# === COMMAND HANDLERS ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    logging.info(f"Received /start from {message.from_user.username} ({message.from_user.id})")
    bot.reply_to(
        message,
        "Selamat datang. Sila masukkan nama penuh murid dan hantar. "
        "Pastikan ejaan adalah tepat tanpa sebarang kesalahan."
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    logging.info(f"Received /help from {message.from_user.username} ({message.from_user.id})")
    help_text = (
        "Senarai arahan yang tersedia:\n\n"
        "/start - Memulakan interaksi dengan bot\n"
        "/help - Senarai arahan bantuan\n"
        "/delima - Pautan rasmi ke DELIMa KPM\n\n"
        "Selain itu, anda boleh menghantar nama penuh murid "
        "untuk mendapatkan maklumat akaun."
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['delima'])
def send_delima_link(message):
    logging.info(f"Received /delima from {message.from_user.username} ({message.from_user.id})")
    bot.reply_to(
        message,
        "Tuan/Puan boleh mengakses DELIMa KPM melalui pautan rasmi berikut:\n"
        "🔗 https://d2.delima.edu.my/"
    )

# === AUTO-DETECTION: Password related ===
PASSWORD_KEYWORDS = ["password", "kata laluan", "lupa password", "lupa kata laluan", "reset password", "reset kata laluan"]

@bot.message_handler(func=lambda message: True)
def send_info(message):
    try:
        user_text = message.text.strip().lower()
        logging.info(f"Received message: '{message.text}' from {message.from_user.username} ({message.from_user.id})")

        # Check if related to password
        if any(keyword in user_text for keyword in PASSWORD_KEYWORDS):
            bot.reply_to(
                message,
                "Sekiranya anda menghadapi masalah berkaitan kata laluan, "
                "sila hubungi guru kelas untuk mendapatkan bantuan dan "
                "melaksanakan proses set semula kata laluan."
            )
            return

        # Handle normal name search
        search_name = message.text.strip().upper()
        logging.info(f"Searching for name: '{search_name}'")

        if df.empty:
            logging.warning("Excel data is empty!")
            bot.reply_to(message, "❌ Data tidak tersedia buat masa ini.")
            return

        matches = df[df['Nama Murid'].str.contains(search_name, case=False, na=False)]
        logging.info(f"Matches found:\n{matches[['Nama Murid']]}")

        if matches.empty:
            logging.info("No matching name found.")
            bot.reply_to(message, "Maaf, nama tidak dijumpai dalam rekod.")
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

# === BOT RUNNER WITH EXPONENTIAL BACKOFF ===
def run_bot():
    delay = 5
    while True:
        try:
            logging.info("🚀 Starting polling...")
            bot.polling(skip_pending=True, none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            logging.error(f"Polling error: {e}. Restarting in {delay}s...")
            time.sleep(delay)
            delay = min(delay * 2, 60)  # Gandakan delay sehingga maksimum 60s

# === START EVERYTHING ===
def keep_alive():
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_bot).start()

logging.info("🚀 Starting bot and web server...")
keep_alive()
