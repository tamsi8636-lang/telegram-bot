import os
import telebot
import pandas as pd
import time
from telebot.apihelper import ApiTelegramException
from flask import Flask
import threading
import logging

# === Logging setup ===
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Flask server (untuk Render keep alive) ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is running."

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def run_bot():
    bot.polling(skip_pending=True, none_stop=True)

def keep_alive():
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_bot).start()

# === CONFIG ===
TOKEN = os.environ.get("BOT_TOKEN")  # ambil dari environment variable
EXCEL_FILE = "ID DELIMA - DATA FEED CHATBOT.xlsx"

if not TOKEN:
    logging.error("❌ BOT_TOKEN tidak dijumpai dalam environment variables!")
    exit(1)

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
        "Selamat datang ke Chatbot DELIMa KPM.\n"
        "Sila masukkan nama penuh murid (tanpa kesalahan ejaan) untuk mendapatkan maklumat akses."
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(
        message,
        "📌 Senarai arahan yang tersedia:\n"
        "/start - Mula menggunakan bot\n"
        "/help - Senarai arahan\n"
        "/delima - Pautan rasmi DELIMa KPM\n\n"
        "Anda juga boleh hantar *nama penuh murid* untuk semakan maklumat."
    )

@bot.message_handler(commands=['delima'])
def send_delima_link(message):
    logging.info(f"Received /delima from {message.from_user.username} ({message.from_user.id})")
    bot.reply_to(
        message,
        "Tuan/Puan boleh mengakses DELIMa KPM melalui pautan rasmi berikut:\n"
        "🔗 https://d2.delima.edu.my/"
    )

@bot.message_handler(func=lambda message: True)
def send_info(message):
    try:
        text = message.text.strip().upper()
        logging.info(f"Received message: '{text}' from {message.from_user.username} ({message.from_user.id})")

        # Jika mesej berkaitan password
        if "PASSWORD" in text or "KATA LALUAN" in text:
            bot.reply_to(
                message,
                "Bagi isu berkaitan kata laluan, sila hubungi guru kelas "
                "untuk mendapatkan bantuan atau membuat penetapan semula kata laluan."
            )
            return

        if df.empty:
            logging.warning("Excel data is empty!")
            bot.reply_to(message, "❌ Data tidak tersedia buat masa ini.")
            return

        matches = df[df['Nama Murid'].str.contains(text, case=False, na=False)]
        logging.info(f"Matches found:\n{matches[['Nama Murid']]}")

        if matches.empty:
            logging.info("No matching name found.")
            bot.reply_to(message, "Maaf, nama tidak dijumpai dalam rekod.")
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
    except Exception as e:
        logging.error(f"Error in send_info handler: {e}")
        bot.reply_to(message, "Maaf, berlaku ralat dalam sistem.")

# === START EVERYTHING ===
logging.info("🚀 Starting bot and web server...")
keep_alive()
