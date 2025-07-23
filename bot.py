import os
import threading
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Доступ дозволено лише цим ID
ALLOWED_USERS = [84807467, 163952863]

# Дані бота
user_data = {'limit': 0, 'dad_spent': 0, 'mom_spent': 0}
DAD_ID = 84807467
MOM_ID = 163952863
keyboard = [["➖ Витрати"], ["🎯 Ліміт", "💰 Баланс"]]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Flask вебсервер
app_flask = Flask(__name__)
telegram_app = None  # Сюди збережемо телеграм-додаток

@app_flask.route("/")
def home():
    return "Bot is running!"

@app_flask.route("/webhook", methods=["POST"])
def webhook():
    if telegram_app:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        telegram_app.update_queue.put(update)
    return "OK"

def run_flask():
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# Перевірка доступу
async def check_access(update: Update):
    user = update.message.from_user
    if user.id not in ALLOWED_USERS:
        print(f"[ACCESS DENIED] {user.first_name} ({user.id}) tried to use the bot.")
        await update.message.reply_text("❌ У вас немає доступу до цього бота.")
        return False
    return True

# Telegram хендлери
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    await update.message.reply_text("👋 Привіт! Я — ваш родинний бот. Оберіть дію:", reply_markup=markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    text = update.message.text
    if text == "➖ Витрати":
        await update.message.reply_text("Введи суму витрати:")
        context.user_data['action'] = 'spend'
    elif text == "🎯 Ліміт":
        await update.message.reply_text("Введи ліміт на місяць:")
        context.user_data['action'] = 'limit'
    elif text == "💰 Баланс":
        dad = user_data['dad_spent']
        mom = user_data['mom_spent']
        limit = user_data['limit']
        balance = limit - dad - mom
        await update.message.reply_text(
            f"🎯 Ліміт: {limit} грн\n"
            f"🧔‍♂️ Витрати Суперпапа: {dad} грн\n"
            f"👩‍🍼 Витрати Супермама: {mom} грн\n"
            f"💚 Залишок: {balance} грн"
        )

async def handle_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    text = update.message.text
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("Введи правильну суму.")
        return

    user = update.message.from_user
    action = context.user_data.get('action')

    if action == 'limit':
        user_data['limit'] = amount
        print(f"[LIMIT] {user.first_name} ({user.id}) set limit to {amount} грн.")
        await update.message.reply_text(f"🎯 Встановлено ліміт: {amount} грн")
    elif action == 'spend':
        if user.id == DAD_ID:
            user_data['dad_spent'] += amount
            print(f"[EXPENSE] Суперпапа додав {amount} грн. Загальні витрати Папи: {user_data['dad_spent']}")
            await update.message.reply_text(f"➖ Додано витрату: {amount} грн (Суперпапа)")
        elif user.id == MOM_ID:
            user_data['mom_spent'] += amount
            print(f"[EXPENSE] Супермама додала {amount} грн. Загальні витрати Мами: {user_data['mom_spent']}")
            await update.message.reply_text(f"➖ Додано витрату: {amount} грн (Супермама)")
    context.user_data['action'] = None

def run_telegram():
    global telegram_app
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set.")
    telegram_app = ApplicationBuilder().token(token).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^[^\d]+$"), handle_buttons))
    telegram_app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+(\.\d+)?$"), handle_numbers))

    # Встановлюємо webhook
    webhook_url = os.getenv("RENDER_EXTERNAL_URL") + "/webhook"
    telegram_app.bot.set_webhook(webhook_url)
    telegram_app.run_async()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_telegram()
