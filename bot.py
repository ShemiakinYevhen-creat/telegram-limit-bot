import os
import json
import asyncio
import datetime
from flask import Flask, request
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import httpx

# ===== Константи =====
TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_CREDENTIALS = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
BACKUP_FILE = "data.json"
MONTHLY_LIMIT = 40000
ALLOWED_USERS = [84807467, 163952863]

# ===== Ініціалізація Flask =====
app = Flask(__name__)

# ===== Данні =====
data = {
    "expenses": [],
    "incomes": [],
    "balance": MONTHLY_LIMIT,
    "last_month_balance": 0,
    "current_month": datetime.datetime.now().month
}

# ===== Збереження / Завантаження =====
def save_data():
    with open(BACKUP_FILE, "w") as f:
        json.dump(data, f)

def load_data():
    global data
    if os.path.exists(BACKUP_FILE):
        with open(BACKUP_FILE, "r") as f:
            data = json.load(f)

def upload_to_drive():
    creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS)
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': f'backup_{datetime.datetime.now().strftime("%Y-%m-%d")}.json', 'parents': [GOOGLE_DRIVE_FOLDER_ID]}
    media = open(BACKUP_FILE, 'rb')
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    media.close()

# ===== Перевірка місяця =====
def check_month():
    now = datetime.datetime.now()
    if data["current_month"] != now.month:
        data["last_month_balance"] = data["balance"] - MONTHLY_LIMIT
        data["balance"] = MONTHLY_LIMIT + data["last_month_balance"]
        data["current_month"] = now.month
        data["expenses"].clear()
        data["incomes"].clear()
        save_data()
        upload_to_drive()

# ===== Команди =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    keyboard = [["Витрата", "Дохід"], ["Залишок", "Звіт"], ["Видалити останню"]]
    await update.message.reply_text("Вітаю! Оберіть дію:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    try:
        amount = float(update.message.text.split()[1])
        data["expenses"].append(amount)
        data["balance"] -= amount
        save_data()
        await update.message.reply_text(f"Додано витрату {amount} грн. Залишок: {data['balance']} грн.")
    except:
        await update.message.reply_text("Формат: /expense сума")

async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    try:
        amount = float(update.message.text.split()[1])
        data["incomes"].append(amount)
        save_data()
        await update.message.reply_text(f"Додано дохід {amount} грн.")
    except:
        await update.message.reply_text("Формат: /income сума")

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    await update.message.reply_text(f"Залишок: {data['balance']} грн.")

async def delete_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    if data["expenses"]:
        last = data["expenses"].pop()
        data["balance"] += last
        save_data()
        await update.message.reply_text(f"Видалено останню витрату: {last} грн.")
    else:
        await update.message.reply_text("Немає витрат для видалення.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    total_exp = sum(data["expenses"])
    total_inc = sum(data["incomes"])
    await update.message.reply_text(f"Звіт за місяць:\nВитрати: {total_exp} грн.\nДоходи: {total_inc} грн.\nЗалишок: {data['balance']} грн.")

# ===== Пінг Render =====
async def ping():
    url = os.getenv("RENDER_EXTERNAL_URL", "")
    while True:
        if url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(url)
            except:
                pass
        await asyncio.sleep(300)

# ===== Flask Webhook =====
@app.route("/", methods=["GET"])
def index():
    return "Бот працює!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "ok"

# ===== Запуск =====
def run_flask():
    app.run(host="0.0.0.0", port=10000)

load_data()
check_month()
bot_app = ApplicationBuilder().token(TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("expense", add_expense))
bot_app.add_handler(CommandHandler("income", add_income))
bot_app.add_handler(CommandHandler("balance", show_balance))
bot_app.add_handler(CommandHandler("delete", delete_last))
bot_app.add_handler(CommandHandler("report", report))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

Thread(target=run_flask).start()
asyncio.get_event_loop().create_task(ping())
bot_app.run_webhook(listen="0.0.0.0", port=10000, url_path="webhook", webhook_url=os.getenv("RENDER_EXTERNAL_URL") + "/webhook")
