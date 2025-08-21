import telebot
import pandas as pd
import time
from telebot.apihelper import ApiTelegramException
from flask import Flask
import threading
import logging
import os

# === Logging setup ===
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Flask minimal web server (untuk Render) ===
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
TOKEN = os.environ.get("BOT_TOKEN")
EXCEL_FILE = "ID DELIMA - DATA FEED CHATBOT.xlsx"

if not TOKEN:
    logging.error("❌ BOT_TOKEN tidak dijumpai dalam environment variables!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

# === SET COMMAND MENU ===
bot.set_my_commands([
    telebot.types.BotCommand("start", "🚀 Mula gunakan bot"),
    telebot.types.BotCommand("help", "📌 Lihat senarai arahan"),
    telebot.types.BotCommand("delima", "🌐 Akses laman rasmi DELIMa KPM"),
    telebot.types.BotCommand("resetpassword", "🔑 Panduan reset kata laluan DELIMa"),
])

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
        "👋 Selamat datang ke sistem bantuan *DELIMa KPM*.\n\n"
        "Sila isi *nama penuh murid* dan hantar.\n"
        "⚠️ Pastikan tiada kesalahan ejaan pada nama.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📌 *Senarai arahan tersedia:*\n\n"
        "🚀 /start - Mula gunakan bot\n"
        "📌 /help - Lihat senarai arahan\n"
        "🌐 /delima - Akses laman rasmi DELIMa KPM\n"
        "🔑 /resetpassword - Panduan reset kata laluan DELIMa\n\n"
        "✍️ Untuk semakan, sila hantar *nama penuh murid*."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['delima'])
def send_delima_link(message):
    bot.reply_to(
        message,
        "🌐 Akses laman rasmi DELIMa KPM di pautan berikut:\n"
        "👉 https://d2.delima.edu.my/"
    )

@bot.message_handler(commands=['resetpassword'])
def send_reset_password(message):
    reply_text = (
        "🔑 *Peringatan Reset Kata Laluan DELIMa KPM*\n\n"
        "Untuk menetapkan semula kata laluan, sila hubungi *guru kelas anak anda* "
        "untuk mendapatkan bantuan rasmi.\n\n"
        "📂 Pihak sekolah menasihatkan agar ibu bapa / penjaga menyimpan kata laluan dengan baik "
        "supaya tidak menghadapi masalah akses pada masa hadapan."
    )
    bot.reply_to(message, reply_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def send_info(message):
    try:
        logging.info(f"Received message: '{message.text}' from {message.from_user.username} ({message.from_user.id})")
        search_name = message.text.strip().upper()
        logging.info(f"Searching for name: '{search_name}'")

        # Jika mesej mengandungi "password" atau "kata laluan"
        if "PASSWORD" in search_name or "KATA LALUAN" in search_name:
            bot.reply_to(
                message,
                "🔑 Untuk isu kata laluan, sila hubungi *guru kelas anak anda* bagi bantuan reset.\n\n"
                "📂 Pihak sekolah mengingatkan agar kata laluan sentiasa disimpan dengan baik.",
                parse_mode="Markdown"
            )
            return

        if df.empty:
            logging.warning("Excel data is empty!")
            bot.reply_to(message, "❌ Data tidak tersedia sekarang.")
            return

        matches = df[df['Nama Murid'].str.contains(search_name, case=False, na=False)]
        logging.info(f"Matches found:\n{matches[['Nama Murid']]}")

        if matches.empty:
            logging.info("No matching name found.")
            bot.reply_to(message, "⚠️ Maaf, nama tidak dijumpai dalam rekod.")
        else:
            row = matches.iloc[0]

            reply_text = (
                f"👤 Nama Murid: {row['Nama Murid']}\n"
                f"📧 Email: {row.iloc[1]}\n"
                f"🔑 Password: {row.iloc[2]}"
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
        bot.reply_to(message, "⚠️ Maaf, berlaku ralat dalam sistem.")

# === START EVERYTHING ===
logging.info("🚀 Starting bot and web server...")
keep_alive()
