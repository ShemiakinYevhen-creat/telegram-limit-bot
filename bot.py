import os
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Дані бота
user_data = {'limit': 0, 'dad_spent': 0, 'mom_spent': 0}
DAD_ID = 84807467
MOM_ID = 163952863
keyboard = [["➖ Витрати"], ["🎯 Ліміт", "💰 Баланс"]]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Flask вебсервер
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# Telegram хендлери
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привіт! Я — ваш родинний бот. Оберіть дію:", reply_markup=markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    text = update.message.text
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("Введи правильну суму.")
        return

    user_id = update.message.from_user.id
    action = context.user_data.get('action')

    if action == 'limit':
        user_data['limit'] = amount
        await update.message.reply_text(f"🎯 Встановлено ліміт: {amount} грн")
    elif action == 'spend':
        if user_id == DAD_ID:
            user_data['dad_spent'] += amount
            await update.message.reply_text(f"➖ Додано витрату: {amount} грн (Суперпапа)")
        elif user_id == MOM_ID:
            user_data['mom_spent'] += amount
            await update.message.reply_text(f"➖ Додано витрату: {amount} грн (Супермама)")
        else:
            await update.message.reply_text("❌ Ви не маєте доступу.")
    context.user_data['action'] = None

def run_telegram():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set.")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^[^\d]+$"), handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+(\.\d+)?$"), handle_numbers))
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_telegram()
