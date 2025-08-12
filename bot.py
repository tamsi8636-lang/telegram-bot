import telebot
import pandas as pd
import time
from telebot.apihelper import ApiTelegramException
from flask import Flask
import threading

# === Flask minimal web server to keep Render happy ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is running."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

keep_alive()

# === CONFIG ===
TOKEN = "8201238992:AAGZeU59gksGe6y6EE3ljETNim-RpjZjCCg"
EXCEL_FILE = "ID DELIMA - DATA FEED CHATBOT.xlsx"

bot = telebot.TeleBot(TOKEN)

# === LOAD EXCEL ===
try:
    df = pd.read_excel(EXCEL_FILE)
    df['Nama Murid'] = df['Nama Murid'].astype(str).str.strip().str.upper()
    print("✅ Excel loaded successfully")
except FileNotFoundError:
    print("❌ Excel file not found. Make sure it's in the same folder.")
    df = pd.DataFrame()

# === HANDLERS ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    print(f"Received /start from {message.from_user.username} ({message.from_user.id})")
    bot.reply_to(
        message,
        "Sila isi nama penuh murid dan hantar, pastikan tiada kesalahan ejaan pada nama."
    )

@bot.message_handler(func=lambda message: True)
def send_info(message):
    print(f"Received message: {message.text} from {message.from_user.username} ({message.from_user.id})")
    search_name = message.text.strip().upper()

    if df.empty:
        print("Excel data is empty!")
        bot.reply_to(message, "❌ Data tidak tersedia sekarang.")
        return

    matches = df[df['Nama Murid'].str.contains(search_name, case=False, na=False)]

    if matches.empty:
        print("No matching name found.")
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
            print(f"Replied with data for {row['Nama Murid']}")
        except ApiTelegramException as e:
            if e.error_code == 429:
                retry_after = int(e.result_json['parameters']['retry_after'])
                print(f"⏳ Rate limit hit, retrying after {retry_after}s")
                time.sleep(retry_after)
                bot.reply_to(message, reply_text)

# === START BOT ===
print("🚀 Bot is running...")
bot.polling(skip_pending=True, none_stop=True)
