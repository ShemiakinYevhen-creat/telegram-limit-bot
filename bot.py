import os
import json
import asyncio
import logging
import datetime
import httpx
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- Налаштування ---
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Вкажи в Render → Environment
ALLOWED_USERS = [84807467, 163952863]  # Ти і дружина
LIMIT = 40000
BACKUP_FILE = "data.json"
PING_URL = os.getenv("PING_URL", "https://telegram-limit-bot.onrender.com")  # URL Render
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

# --- Логування ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask для Render ---
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Bot is running!"

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    asyncio.run(app.update_queue.put(Update.de_json(data, app.bot)))
    return "ok"

# --- Дані ---
data = {
    "limit": LIMIT,
    "expenses": [],
    "income": [],
    "month": datetime.date.today().month
}

# --- Збереження/Завантаження ---
def save_data():
    with open(BACKUP_FILE, "w") as f:
        json.dump(data, f)
    upload_backup()

def load_data():
    global data
    if os.path.exists(BACKUP_FILE):
        with open(BACKUP_FILE, "r") as f:
            data = json.load(f)

# --- Google Drive бекап ---
def upload_backup():
    if not GOOGLE_CREDENTIALS or not GOOGLE_DRIVE_FOLDER_ID:
        return
    import google.oauth2.service_account
    from googleapiclient.discovery import build
    creds = google.oauth2.service_account.Credentials.from_service_account_info(json.loads(GOOGLE_CREDENTIALS))
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {"name": BACKUP_FILE, "parents": [GOOGLE_DRIVE_FOLDER_ID]}
    media = googleapiclient.http.MediaFileUpload(BACKUP_FILE, resumable=True)
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

# --- Пінг ---
async def keep_alive():
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(PING_URL, timeout=10)
            except Exception as e:
                logger.error(f"Ping error: {e}")
            await asyncio.sleep(300)

# --- Хендлери ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return await update.message.reply_text("⛔ Доступ заборонено.")
    kb = [["Витрати Супермама", "Витрати Суперпапа"], ["Дохід", "Видалити витрату"], ["Звіт за місяць"]]
    await update.message.reply_text("Обери дію:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    text = update.message.text
    context.user_data["action"] = text
    if "Витрати" in text:
        await update.message.reply_text("Введи суму витрати:")
    elif "Дохід" in text:
        await update.message.reply_text("Введи суму доходу:")
    elif "Видалити" in text:
        if data["expenses"]:
            data["expenses"].pop()
            save_data()
            await update.message.reply_text("Останню витрату видалено.")
        else:
            await update.message.reply_text("Немає витрат для видалення.")
    elif "Звіт" in text:
        total_exp = sum(e["amount"] for e in data["expenses"])
        total_inc = sum(i["amount"] for i in data["income"])
        await update.message.reply_text(f"Звіт за {datetime.date.today().strftime('%B')}:\nВитрати: {total_exp} грн\nДохід: {total_inc} грн")

async def handle_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    try:
        value = float(update.message.text)
    except:
        return await update.message.reply_text("Введи число.")
    action = context.user_data.get("action")
    if "Витрати" in action:
        data["expenses"].append({"amount": value, "user": update.effective_user.id})
    elif "Дохід" in action:
        data["income"].append({"amount": value})
    save_data()
    await update.message.reply_text("Збережено!")

# --- Авто-ресет ---
async def check_month():
    while True:
        today = datetime.date.today()
        if today.day == 1 and data["month"] != today.month:
            last_total = data["limit"] - sum(e["amount"] for e in data["expenses"])
            data["month"] = today.month
            data["limit"] = LIMIT + last_total
            data["expenses"] = []
            data["income"] = []
            save_data()
        await asyncio.sleep(3600)

# --- Запуск ---
load_data()
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_buttons))
app.add_handler(MessageHandler(filters.Regex(r"^\d+(\.\d+)?$"), handle_numbers))

async def main():
    asyncio.create_task(keep_alive())
    asyncio.create_task(check_month())
    await app.bot.set_webhook(f"{PING_URL}/webhook")
    flask_app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    asyncio.run(main())

