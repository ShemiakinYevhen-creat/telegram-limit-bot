import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Доступ дозволено лише цим ID
ALLOWED_USERS = [84807467, 163952863]

# Дані бота
user_data = {'limit': 0, 'dad_spent': 0, 'mom_spent': 0}
DAD_ID = 84807467
MOM_ID = 163952863
keyboard = [["➖ Витрати"], ["🎯 Ліміт", "💰 Баланс"]]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Перевірка доступу
async def check_access(update: Update):
    user = update.message.from_user
    if user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ У вас немає доступу до цього бота.")
        return False
    return True

# Команди
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
        dad, mom, limit = user_data['dad_spent'], user_data['mom_spent'], user_data['limit']
        balance = limit - dad - mom
        await update.message.reply_text(
            f"🎯 Ліміт: {limit} грн\n"
            f"🧔‍♂️ Витрати Суперпапа: {dad} грн\n"
            f"👩‍🍼 Витрати Супермама: {mom} грн\n"
            f"💚 Залишок: {balance} грн"
        )

async def handle_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Введи правильну суму.")
        return

    user = update.message.from_user
    action = context.user_data.get('action')
    if action == 'limit':
        user_data['limit'] = amount
        await update.message.reply_text(f"🎯 Встановлено ліміт: {amount} грн")
    elif action == 'spend':
        if user.id == DAD_ID:
            user_data['dad_spent'] += amount
            await update.message.reply_text(f"➖ Додано витрату: {amount} грн (Суперпапа)")
        elif user.id == MOM_ID:
            user_data['mom_spent'] += amount
            await update.message.reply_text(f"➖ Додано витрату: {amount} грн (Супермама)")
    context.user_data['action'] = None

# === Запуск
if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^[^\d]+$"), handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+(\.\d+)?$"), handle_numbers))

    # Webhook
    webhook_url = os.getenv("RENDER_EXTERNAL_URL") + "/webhook"
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path="",
        webhook_url=webhook_url
    )
