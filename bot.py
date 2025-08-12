import telebot
import pandas as pd
import time
from telebot.apihelper import ApiTelegramException

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
    bot.reply_to(
        message,
        "Sila isi nama penuh murid dan hantar, pastikan tiada kesalahan ejaan pada nama."
    )

@bot.message_handler(func=lambda message: True)
def send_info(message):
    search_name = message.text.strip().upper()

    if df.empty:
        bot.reply_to(message, "❌ Data tidak tersedia sekarang.")
        return

    matches = df[df['Nama Murid'].str.contains(search_name, case=False, na=False)]

    if matches.empty:
        bot.reply_to(message, "Maaf, nama tidak dijumpai.")
    else:
        # Only reply with the first (closest) match
        row = matches.iloc[0]

        reply_text = (
            f"Nama Murid: {row['Nama Murid']}\n"
            f"Email: {row.iloc[1]}\n"
            f"Password: {row.iloc[2]}"
        )

        try:
            bot.reply_to(message, reply_text)
        except ApiTelegramException as e:
            if e.error_code == 429:
                retry_after = int(e.result_json['parameters']['retry_after'])
                print(f"⏳ Rate limit hit, retrying after {retry_after}s")
                time.sleep(retry_after)
                bot.reply_to(message, reply_text)

# === START BOT ===
print("🚀 Bot is running...")
bot.polling(skip_pending=True, none_stop=True)
