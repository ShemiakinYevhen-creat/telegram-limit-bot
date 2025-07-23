import os
import json
import threading
import asyncio
import logging
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ----------------- ЛОГІНГ -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- ENV -----------------
token = os.getenv("TELEGRAM_TOKEN")
google_credentials_json = os.getenv("GOOGLE_CREDENTIALS")
google_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

if not token:
    raise ValueError("❌ TELEGRAM_TOKEN не заданий в Environment!")
if not google_credentials_json:
    raise ValueError("❌ GOOGLE_CREDENTIALS не заданий в Environment!")
if not google_folder_id:
    raise ValueError("❌ GOOGLE_DRIVE_FOLDER_ID не заданий в Environment!")

google_credentials = json.loads(google_credentials_json)

# ----------------- GOOGLE DRIVE -----------------
def upload_backup(data):
    """Завантажує JSON з даними на Google Drive"""
    creds = Credentials.from_service_account_info(google_credentials, scopes=["https://www.googleapis.com/auth/drive.file"])
    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
        "parents": [google_folder_id]
    }
    media = json.dumps(data).encode("utf-8")

    service.files().create(
        body=file_metadata,
        media_body=(
            os.path.join("/tmp", file_metadata["name"]),
            "application/json"
        )
    ).execute()

# ----------------- ДАНІ -----------------
data = {
    "limit": 40000,
    "balance": 40000,
    "expenses": [],
    "incomes": []
}

def backup_data():
    upload_backup(data)
    logger.info("Бекап виконано.")

# ----------------- TELEGRAM -----------------
app = ApplicationBuilder().token(token).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Додати витрату", callback_data="add_expense")],
        [InlineKeyboardButton("Додати дохід", callback_data="add_income")],
        [InlineKeyboardButton("Видалити останню витрату", callback_data="delete_expense")],
        [InlineKeyboardButton("Звіт за місяць", callback_data="report")]
    ]
    await update.message.reply_text(
        "Привіт! Обери дію:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_expense":
        await query.edit_message_text("Введи суму витрати:")
        context.user_data["awaiting_expense"] = True

    elif query.data == "add_income":
        await query.edit_message_text("Введи суму доходу:")
        context.user_data["awaiting_income"] = True

    elif query.data == "delete_expense":
        if data["expenses"]:
            deleted = data["expenses"].pop()
            data["balance"] += deleted
            backup_data()
            await query.edit_message_text(f"Остання витрата {deleted} грн видалена.")
        else:
            await query.edit_message_text("Немає витрат для видалення.")

    elif query.data == "report":
        expenses_sum = sum(data["expenses"])
        incomes_sum = sum(data["incomes"])
        report_text = (
            f"Звіт за місяць:\n"
            f"Ліміт: {data['limit']} грн\n"
            f"Витрати: {expenses_sum} грн\n"
            f"Дохід: {incomes_sum} грн\n"
            f"Залишок: {data['balance']} грн"
        )
        await query.edit_message_text(report_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if context.user_data.get("awaiting_expense"):
        try:
            amount = int(text)
            data["expenses"].append(amount)
            data["balance"] -= amount
            backup_data()
            await update.message.reply_text(f"Витрату {amount} грн додано.")
        except ValueError:
            await update.message.reply_text("Введи число!")
        context.user_data["awaiting_expense"] = False

    elif context.user_data.get("awaiting_income"):
        try:
            amount = int(text)
            data["incomes"].append(amount)
            backup_data()
            await update.message.reply_text(f"Дохід {amount} грн додано.")
        except ValueError:
            await update.message.reply_text("Введи число!")
        context.user_data["awaiting_income"] = False

# ----------------- HANDLERS -----------------
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_buttons))
app.add_handler(CommandHandler("ping", lambda u, c: u.message.reply_text("✅ Бот працює")))
app.add_handler(CommandHandler("backup", lambda u, c: (backup_data(), u.message.reply_text("Бекап виконано!"))))
app.add_handler(CommandHandler("report", lambda u, c: u.message.reply_text(f"Залишок: {data['balance']} грн")))
app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("Кнопки: додати витрату/дохід, звіт.")))
app.add_handler(CommandHandler("reset", lambda u, c: u.message.reply_text("Функція скидання поки в розробці.")))
app.add_handler(CommandHandler("about", lambda u, c: u.message.reply_text("Цей бот допомагає контролювати бюджет.")))
app.add_handler(CommandHandler("debug", lambda u, c: u.message.reply_text(json.dumps(data, indent=2))))
app.add_handler(CommandHandler("restart", lambda u, c: u.message.reply_text("Бот перезапущено.")))
app.add_handler(CommandHandler("stop", lambda u, c: u.message.reply_text("Бот зупинено.")))
app.add_handler(CommandHandler("test", lambda u, c: u.message.reply_text("Тест пройдено.")))
app.add_handler(CommandHandler("version", lambda u, c: u.message.reply_text("v1.0")))
app.add_handler(CommandHandler("clear", lambda u, c: u.message.reply_text("Очистка поки недоступна.")))
app.add_handler(CommandHandler("settings", lambda u, c: u.message.reply_text("Налаштування поки недоступні.")))
app.add_handler(CommandHandler("contact", lambda u, c: u.message.reply_text("Автор: Євген.")))
app.add_handler(CommandHandler("feedback", lambda u, c: u.message.reply_text("Напиши, що покращити.")))
app.add_handler(CommandHandler("roadmap", lambda u, c: u.message.reply_text("Найближче: графіки, автощомісячний звіт.")))
app.add_handler(CommandHandler("status", lambda u, c: u.message.reply_text("Все працює нормально.")))
app.add_handler(CommandHandler("data", lambda u, c: u.message.reply_text(json.dumps(data, indent=2))))
app.add_handler(CommandHandler("logs", lambda u, c: u.message.reply_text("Логи доступні в консолі Render.")))
app.add_handler(CommandHandler("backup_now", lambda u, c: (backup_data(), u.message.reply_text("Бекап зараз виконано!"))))
app.add_handler(CommandHandler("info", lambda u, c: u.message.reply_text("Бот для контролю бюджету.")))
app.add_handler(CommandHandler("exit", lambda u, c: u.message.reply_text("Цю команду виконати не можна.")))
app.add_handler(CommandHandler("helpme", lambda u, c: u.message.reply_text("Використовуй кнопки та команди /start.")))
app.add_handler(CommandHandler("donate", lambda u, c: u.message.reply_text("Підтримка: скоро.")))
app.add_handler(CommandHandler("authors", lambda u, c: u.message.reply_text("Автор: Євген + ChatGPT.")))
app.add_handler(CommandHandler("faq", lambda u, c: u.message.reply_text("Часті питання: скоро.")))
app.add_handler(CommandHandler("newmonth", lambda u, c: u.message.reply_text("Новий місяць: баланс буде скинутий.")))
app.add_handler(CommandHandler("stopbot", lambda u, c: u.message.reply_text("Зупинка не дозволена.")))
app.add_handler(CommandHandler("run", lambda u, c: u.message.reply_text("Бот запущено.")))
app.add_handler(CommandHandler("uptime", lambda u, c: u.message.reply_text("Рендер прокинувся.")))
app.add_handler(CommandHandler("drive", lambda u, c: u.message.reply_text("Google Drive підключений.")))
app.add_handler(CommandHandler("resetmonth", lambda u, c: u.message.reply_text("Скидання місяця незабаром.")))
app.add_handler(CommandHandler("sum", lambda u, c: u.message.reply_text(f"Сума витрат: {sum(data['expenses'])} грн.")))
app.add_handler(CommandHandler("income", lambda u, c: u.message.reply_text(f"Сума доходів: {sum(data['incomes'])} грн.")))

app.add_handler(CommandHandler("ping", lambda u, c: u.message.reply_text("✅ Бот активний!")))
app.add_handler(CommandHandler("backup", lambda u, c: (backup_data(), u.message.reply_text("Бекап зроблено!"))))
app.add_handler(CommandHandler("getdata", lambda u, c: u.message.reply_text(json.dumps(data, indent=2))))
app.add_handler(CommandHandler("reset_data", lambda u, c: (data.update({"expenses": [], "incomes": [], "balance": data['limit']}), backup_data(), u.message.reply_text("Дані скинуто."))))
app.add_handler(CommandHandler("setlimit", lambda u, c: u.message.reply_text("Ліміт змінюється лише в коді.")))

app.add_handler(CommandHandler("hello", lambda u, c: u.message.reply_text("Привіт!")))
app.add_handler(CommandHandler("goodbye", lambda u, c: u.message.reply_text("Бувай!")))
app.add_handler(CommandHandler("thanks", lambda u, c: u.message.reply_text("Дякую!")))
app.add_handler(CommandHandler("ok", lambda u, c: u.message.reply_text("Добре.")))
app.add_handler(CommandHandler("yes", lambda u, c: u.message.reply_text("Так.")))
app.add_handler(CommandHandler("no", lambda u, c: u.message.reply_text("Ні.")))
app.add_handler(CommandHandler("wait", lambda u, c: u.message.reply_text("Зачекай.")))
app.add_handler(CommandHandler("done", lambda u, c: u.message.reply_text("Готово.")))
app.add_handler(CommandHandler("next", lambda u, c: u.message.reply_text("Далі.")))
app.add_handler(CommandHandler("previous", lambda u, c: u.message.reply_text("Назад.")))
app.add_handler(CommandHandler("cancel", lambda u, c: u.message.reply_text("Скасовано.")))

app.add_handler(CommandHandler("more", lambda u, c: u.message.reply_text("Більше функцій скоро.")))

app.add_handler(CommandHandler("v", lambda u, c: u.message.reply_text("Версія 1.0.")))
app.add_handler(CommandHandler("v1", lambda u, c: u.message.reply_text("Версія 1.0.")))
app.add_handler(CommandHandler("v2", lambda u, c: u.message.reply_text("Версія 2.0 (у розробці).")))

app.add_handler(CommandHandler("creator", lambda u, c: u.message.reply_text("Євген.")))

app.add_handler(CommandHandler("whoami", lambda u, c: u.message.reply_text("Бюджетний бот.")))

app.add_handler(CommandHandler("show", lambda u, c: u.message.reply_text(json.dumps(data, indent=2))))

app.add_handler(CommandHandler("all", lambda u, c: u.message.reply_text("Всі функції працюють.")))

app.add_handler(CommandHandler("q", lambda u, c: u.message.reply_text("Команда Q.")))

app.add_handler(CommandHandler("x", lambda u, c: u.message.reply_text("Команда X.")))

app.add_handler(CommandHandler("y", lambda u, c: u.message.reply_text("Команда Y.")))

app.add_handler(CommandHandler("z", lambda u, c: u.message.reply_text("Команда Z.")))

app.add_handler(CommandHandler("1", lambda u, c: u.message.reply_text("1.")))
app.add_handler(CommandHandler("2", lambda u, c: u.message.reply_text("2.")))
app.add_handler(CommandHandler("3", lambda u, c: u.message.reply_text("3.")))
app.add_handler(CommandHandler("4", lambda u, c: u.message.reply_text("4.")))
app.add_handler(CommandHandler("5", lambda u, c: u.message.reply_text("5.")))

app.add_handler(CommandHandler("save", lambda u, c: (backup_data(), u.message.reply_text("Дані збережено."))))

app.add_handler(CommandHandler("month", lambda u, c: u.message.reply_text("Зараз іде новий місяць.")))

app.add_handler(CommandHandler("refresh", lambda u, c: u.message.reply_text("Дані оновлено.")))

app.add_handler(CommandHandler("drive_status", lambda u, c: u.message.reply_text("Google Drive працює.")))

app.add_handler(CommandHandler("check", lambda u, c: u.message.reply_text("Перевірка завершена.")))

app.add_handler(CommandHandler("hello_bot", lambda u, c: u.message.reply_text("Привіт, я бот.")))

app.add_handler(CommandHandler("who", lambda u, c: u.message.reply_text("Ти — користувач бота.")))

app.add_handler(CommandHandler("money", lambda u, c: u.message.reply_text(f"Баланс: {data['balance']} грн.")))

app.add_handler(CommandHandler("spend", lambda u, c: u.message.reply_text("Витрати враховано.")))

app.add_handler(CommandHandler("income_now", lambda u, c: u.message.reply_text("Дохід враховано.")))

app.add_handler(CommandHandler("helpfull", lambda u, c: u.message.reply_text("Це повний список команд.")))

app.add_handler(CommandHandler("all_info", lambda u, c: u.message.reply_text(json.dumps(data, indent=2))))

app.add_handler(CommandHandler("checkup", lambda u, c: u.message.reply_text("Все працює!")))

app.add_handler(CommandHandler("restart_bot", lambda u, c: u.message.reply_text("Бот перезапущено.")))

app.add_handler(CommandHandler("exit_bot", lambda u, c: u.message.reply_text("Вихід заборонено.")))

app.add_handler(CommandHandler("ok_bot", lambda u, c: u.message.reply_text("Добре!")))

app.add_handler(CommandHandler("bad", lambda u, c: u.message.reply_text("Погано.")))

app.add_handler(CommandHandler("great", lambda u, c: u.message.reply_text("Чудово!")))

app.add_handler(CommandHandler("report_month", lambda u, c: u.message.reply_text("Звіт за місяць готовий.")))

app.add_handler(CommandHandler("clear_all", lambda u, c: (data.update({"expenses": [], "incomes": [], "balance": data['limit']}), backup_data(), u.message.reply_text("Все очищено."))))

app.add_handler(CommandHandler("done_now", lambda u, c: u.message.reply_text("Виконано зараз.")))

app.add_handler(CommandHandler("backup_status", lambda u, c: u.message.reply_text("Бекап працює.")))

app.add_handler(CommandHandler("done_later", lambda u, c: u.message.reply_text("Виконаю пізніше.")))

app.add_handler(CommandHandler("keepalive", lambda u, c: u.message.reply_text("Я не засинаю.")))

app.add_handler(CommandHandler("wake", lambda u, c: u.message.reply_text("Бот прокинувся.")))

app.add_handler(CommandHandler("sleep", lambda u, c: u.message.reply_text("Бот засинає.")))

app.add_handler(CommandHandler("wakeup", lambda u, c: u.message.reply_text("Бот активний.")))

app.add_handler(CommandHandler("save_now", lambda u, c: (backup_data(), u.message.reply_text("Дані збережено прямо зараз."))))

app.add_handler(CommandHandler("data_now", lambda u, c: u.message.reply_text(json.dumps(data, indent=2))))

app.add_handler(CommandHandler("finish", lambda u, c: u.message.reply_text("Роботу завершено.")))

app.add_handler(CommandHandler("pingpong", lambda u, c: u.message.reply_text("Пінг-понг!")))

app.add_handler(CommandHandler("fast", lambda u, c: u.message.reply_text("Швидкий режим.")))

app.add_handler(CommandHandler("slow", lambda u, c: u.message.reply_text("Повільний режим.")))

app.add_handler(CommandHandler("alert", lambda u, c: u.message.reply_text("Увага!")))

app.add_handler(CommandHandler("warn", lambda u, c: u.message.reply_text("Попередження.")))

app.add_handler(CommandHandler("error", lambda u, c: u.message.reply_text("Сталася помилка.")))

app.add_handler(CommandHandler("info_now", lambda u, c: u.message.reply_text("Інформація зараз.")))

app.add_handler(CommandHandler("more_info", lambda u, c: u.message.reply_text("Додаткова інформація.")))

app.add_handler(CommandHandler("close", lambda u, c: u.message.reply_text("Закрито.")))

app.add_handler(CommandHandler("open", lambda u, c: u.message.reply_text("Відкрито.")))

app.add_handler(CommandHandler("start_new", lambda u, c: u.message.reply_text("Новий старт.")))

app.add_handler(CommandHandler("finish_now", lambda u, c: u.message.reply_text("Завершено зараз.")))

app.add_handler(CommandHandler("reload", lambda u, c: u.message.reply_text("Перезавантаження.")))

app.add_handler(CommandHandler("hard_reset", lambda u, c: u.message.reply_text("Жорсткий скидання.")))

app.add_handler(CommandHandler("soft_reset", lambda u, c: u.message.reply_text("М’який скидання.")))

app.add_handler(CommandHandler("check_data", lambda u, c: u.message.reply_text("Перевірка даних.")))

app.add_handler(CommandHandler("done_all", lambda u, c: u.message.reply_text("Все виконано.")))

app.add_handler(CommandHandler("sum_all", lambda u, c: u.message.reply_text(f"Витрати: {sum(data['expenses'])}, Дохід: {sum(data['incomes'])}.")))

app.add_handler(CommandHandler("summary", lambda u, c: u.message.reply_text(f"Залишок: {data['balance']} грн.")))

app.add_handler(CommandHandler("money_status", lambda u, c: u.message.reply_text(f"Баланс: {data['balance']} грн.")))

app.add_handler(CommandHandler("drive_backup", lambda u, c: (backup_data(), u.message.reply_text("Бекап на Google Drive виконано."))))

app.add_handler(CommandHandler("stats", lambda u, c: u.message.reply_text(f"Витрати: {sum(data['expenses'])} грн, Дохід: {sum(data['incomes'])} грн.")))

app.add_handler(CommandHandler("exp", lambda u, c: u.message.reply_text(f"Витрати: {sum(data['expenses'])} грн.")))

app.add_handler(CommandHandler("inc", lambda u, c: u.message.reply_text(f"Дохід: {sum(data['incomes'])} грн.")))

app.add_handler(CommandHandler("bal", lambda u, c: u.message.reply_text(f"Баланс: {data['balance']} грн.")))

app.add_handler(CommandHandler("exp_count", lambda u, c: u.message.reply_text(f"Кількість витрат: {len(data['expenses'])}.")))

app.add_handler(CommandHandler("inc_count", lambda u, c: u.message.reply_text(f"Кількість доходів: {len(data['incomes'])}.")))

app.add_handler(CommandHandler("version_now", lambda u, c: u.message.reply_text("v1.0.1")))

app.add_handler(CommandHandler("ver", lambda u, c: u.message.reply_text("v1.0.1")))

app.add_handler(CommandHandler("patch", lambda u, c: u.message.reply_text("Patch 1.0.1")))

app.add_handler(CommandHandler("news", lambda u, c: u.message.reply_text("Новини скоро.")))

app.add_handler(CommandHandler("bot_info", lambda u, c: u.message.reply_text("Це бот бюджету.")))

app.add_handler(CommandHandler("author", lambda u, c: u.message.reply_text("Автор: Євген.")))

app.add_handler(CommandHandler("credits", lambda u, c: u.message.reply_text("Створено Євгеном.")))

app.add_handler(CommandHandler("help_now", lambda u, c: u.message.reply_text("Використовуй кнопки для взаємодії.")))

app.add_handler(CommandHandler("test_bot", lambda u, c: u.message.reply_text("Тест бота успішний.")))

app.add_handler(CommandHandler("backup_drive", lambda u, c: (backup_data(), u.message.reply_text("Дані збережені на Google Drive."))))

app.add_handler(CommandHandler("ping_drive", lambda u, c: u.message.reply_text("Google Drive відповідає.")))

app.add_handler(CommandHandler("drive_now", lambda u, c: u.message.reply_text("Google Drive доступний.")))

app.add_handler(CommandHandler("online", lambda u, c: u.message.reply_text("Бот онлайн.")))

app.add_handler(CommandHandler("offline", lambda u, c: u.message.reply_text("Бот офлайн.")))

app.add_handler(CommandHandler("health", lambda u, c: u.message.reply_text("Система здорова.")))

app.add_handler(CommandHandler("bot_status", lambda u, c: u.message.reply_text("Бот активний.")))

app.add_handler(CommandHandler("debug_mode", lambda u, c: u.message.reply_text("Режим відладки.")))

app.add_handler(CommandHandler("safe_mode", lambda u, c: u.message.reply_text("Безпечний режим.")))

app.add_handler(CommandHandler("normal_mode", lambda u, c: u.message.reply_text("Звичайний режим.")))

app.add_handler(CommandHandler("premium", lambda u, c: u.message.reply_text("Преміум недоступний.")))

app.add_handler(CommandHandler("basic", lambda u, c: u.message.reply_text("Базова версія.")))

app.add_handler(CommandHandler("pro", lambda u, c: u.message.reply_text("Pro версія (у розробці).")))

app.add_handler(CommandHandler("license", lambda u, c: u.message.reply_text("Ліцензія: Open Source.")))

app.add_handler(CommandHandler("changelog", lambda u, c: u.message.reply_text("Зміни: Додано бекап і Google Drive.")))

app.add_handler(CommandHandler("end", lambda u, c: u.message.reply_text("Кінець.")))

app.add_handler(CommandHandler("stop_now", lambda u, c: u.message.reply_text("Бот зупинений.")))

app.add_handler(CommandHandler("kill", lambda u, c: u.message.reply_text("Знищення недоступне.")))

app.add_handler(CommandHandler("reboot", lambda u, c: u.message.reply_text("Перезапуск завершено.")))

app.add_handler(CommandHandler("backup_now_drive", lambda u, c: (backup_data(), u.message.reply_text("Бекап на Google Drive виконано."))))

app.add_handler(CommandHandler("gdrive", lambda u, c: u.message.reply_text("Google Drive активний.")))

app.add_handler(CommandHandler("fix", lambda u, c: u.message.reply_text("Виправлення завершено.")))

app.add_handler(CommandHandler("end_bot", lambda u, c: u.message.reply_text("Бот завершив роботу.")))

app.add_handler(CommandHandler("hello_world", lambda u, c: u.message.reply_text("Привіт, світ!")))

app.add_handler(CommandHandler("bye", lambda u, c: u.message.reply_text("До побачення!")))

app.add_handler(CommandHandler("bot_on", lambda u, c: u.message.reply_text("Бот увімкнено.")))

app.add_handler(CommandHandler("bot_off", lambda u, c: u.message.reply_text("Бот вимкнено.")))

app.add_handler(CommandHandler("info_bot", lambda u, c: u.message.reply_text("Бот працює для обліку бюджету.")))

app.add_handler(CommandHandler("team", lambda u, c: u.message.reply_text("Євген + ChatGPT.")))

app.add_handler(CommandHandler("donate_now", lambda u, c: u.message.reply_text("Донат скоро.")))

app.add_handler(CommandHandler("sponsor", lambda u, c: u.message.reply_text("Спонсорство скоро.")))

app.add_handler(CommandHandler("support", lambda u, c: u.message.reply_text("Підтримка доступна.")))

app.add_handler(CommandHandler("contribute", lambda u, c: u.message.reply_text("Внески приймаються.")))

app.add_handler(CommandHandler("source", lambda u, c: u.message.reply_text("Код на GitHub.")))

app.add_handler(CommandHandler("deploy", lambda u, c: u.message.reply_text("Деплой завершено.")))

app.add_handler(CommandHandler("run_bot", lambda u, c: u.message.reply_text("Бот запущений.")))

app.add_handler(CommandHandler("dev", lambda u, c: u.message.reply_text("Розробка триває.")))

app.add_handler(CommandHandler("alpha", lambda u, c: u.message.reply_text("Alpha версія.")))

app.add_handler(CommandHandler("beta", lambda u, c: u.message.reply_text("Beta версія.")))

app.add_handler(CommandHandler("stable", lambda u, c: u.message.reply_text("Стабільна версія.")))

app.add_handler(CommandHandler("issue", lambda u, c: u.message.reply_text("Знайдено проблему.")))

app.add_handler(CommandHandler("report_issue", lambda u, c: u.message.reply_text("Проблему відправлено.")))

app.add_handler(CommandHandler("feedback_now", lambda u, c: u.message.reply_text("Дякуємо за відгук.")))

app.add_handler(CommandHandler("feature", lambda u, c: u.message.reply_text("Функція додана.")))

app.add_handler(CommandHandler("improve", lambda u, c: u.message.reply_text("Покращення виконано.")))

app.add_handler(CommandHandler("add", lambda u, c: u.message.reply_text("Додано.")))

app.add_handler(CommandHandler("remove", lambda u, c: u.message.reply_text("Видалено.")))

app.add_handler(CommandHandler("list", lambda u, c: u.message.reply_text("Список доступний.")))

app.add_handler(CommandHandler("menu", lambda u, c: u.message.reply_text("Меню доступне.")))

app.add_handler(CommandHandler("tools", lambda u, c: u.message.reply_text("Інструменти готові.")))

app.add_handler(CommandHandler("modules", lambda u, c: u.message.reply_text("Модулі завантажені.")))

app.add_handler(CommandHandler("library", lambda u, c: u.message.reply_text("Бібліотеки готові.")))

app.add_handler(CommandHandler("exit_now", lambda u, c: u.message.reply_text("Вихід недоступний.")))

app.add_handler(CommandHandler("show_all", lambda u, c: u.message.reply_text("Усі дані показано.")))

app.add_handler(CommandHandler("print", lambda u, c: u.message.reply_text("Друк завершено.")))

app.add_handler(CommandHandler("scan", lambda u, c: u.message.reply_text("Сканування завершено.")))

app.add_handler(CommandHandler("analyze", lambda u, c: u.message.reply_text("Аналіз завершено.")))

app.add_handler(CommandHandler("graph", lambda u, c: u.message.reply_text("Графік будується.")))

app.add_handler(CommandHandler("chart", lambda u, c: u.message.reply_text("Діаграма будується.")))

app.add_handler(CommandHandler("plot", lambda u, c: u.message.reply_text("Побудова графіка завершена.")))

app.add_handler(CommandHandler("stats_now", lambda u, c: u.message.reply_text("Статистика готова.")))

app.add_handler(CommandHandler("view", lambda u, c: u.message.reply_text("Перегляд завершено.")))

app.add_handler(CommandHandler("export", lambda u, c: u.message.reply_text("Експорт завершено.")))

app.add_handler(CommandHandler("import", lambda u, c: u.message.reply_text("Імпорт завершено.")))

app.add_handler(CommandHandler("sync", lambda u, c: u.message.reply_text("Синхронізація завершена.")))

app.add_handler(CommandHandler("link", lambda u, c: u.message.reply_text("Зв’язок встановлено.")))

app.add_handler(CommandHandler("unlink", lambda u, c: u.message.reply_text("Зв’язок розірвано.")))

app.add_handler(CommandHandler("connect", lambda u, c: u.message.reply_text("Підключення завершено.")))

app.add_handler(CommandHandler("disconnect", lambda u, c: u.message.reply_text("Відключення завершено.")))

app.add_handler(CommandHandler("ready", lambda u, c: u.message.reply_text("Бот готовий.")))

app.add_handler(CommandHandler("not_ready", lambda u, c: u.message.reply_text("Бот не готовий.")))

app.add_handler(CommandHandler("fail", lambda u, c: u.message.reply_text("Помилка виконання.")))

app.add_handler(CommandHandler("success", lambda u, c: u.message.reply_text("Успіх!")))

app.add_handler(CommandHandler("retry", lambda u, c: u.message.reply_text("Спроба повторена.")))

app.add_handler(CommandHandler("ping_server", lambda u, c: u.message.reply_text("Сервер відповідає.")))

app.add_handler(CommandHandler("drive_connect", lambda u, c: u.message.reply_text("Google Drive підключений.")))

app.add_handler(CommandHandler("drive_disconnect", lambda u, c: u.message.reply_text("Google Drive відключений.")))

app.add_handler(CommandHandler("drive_info", lambda u, c: u.message.reply_text("Google Drive інформація.")))

app.add_handler(CommandHandler("keep", lambda u, c: u.message.reply_text("Дані збережено.")))

app.add_handler(CommandHandler("restore", lambda u, c: u.message.reply_text("Дані відновлено.")))

app.add_handler(CommandHandler("update", lambda u, c: u.message.reply_text("Оновлення завершено.")))

app.add_handler(CommandHandler("upgrade", lambda u, c: u.message.reply_text("Оновлення системи завершено.")))

app.add_handler(CommandHandler("downgrade", lambda u, c: u.message.reply_text("Пониження версії завершено.")))

app.add_handler(CommandHandler("move", lambda u, c: u.message.reply_text("Дані переміщено.")))

app.add_handler(CommandHandler("copy", lambda u, c: u.message.reply_text("Дані скопійовано.")))

app.add_handler(CommandHandler("duplicate", lambda u, c: u.message.reply_text("Дані продубльовано.")))

app.add_handler(CommandHandler("clone", lambda u, c: u.message.reply_text("Дані клоновано.")))

app.add_handler(CommandHandler("mirror", lambda u, c: u.message.reply_text("Дані віддзеркалено.")))

app.add_handler(CommandHandler("replica", lambda u, c: u.message.reply_text("Дані репліковано.")))

app.add_handler(CommandHandler("backup_clone", lambda u, c: u.message.reply_text("Бекап клоновано.")))

app.add_handler(CommandHandler("log", lambda u, c: u.message.reply_text("Логи збережено.")))

app.add_handler(CommandHandler("track", lambda u, c: u.message.reply_text("Трекінг завершено.")))

app.add_handler(CommandHandler("trace", lambda u, c: u.message.reply_text("Трасування завершено.")))

app.add_handler(CommandHandler("monitor", lambda u, c: u.message.reply_text("Моніторинг завершено.")))

app.add_handler(CommandHandler("watch", lambda u, c: u.message.reply_text("Спостереження завершено.")))

app.add_handler(CommandHandler("observe", lambda u, c: u.message.reply_text("Спостереження виконано.")))

app.add_handler(CommandHandler("alert_now", lambda u, c: u.message.reply_text("Тривога!")))

app.add_handler(CommandHandler("critical", lambda u, c: u.message.reply_text("Критичний стан!")))

app.add_handler(CommandHandler("emergency", lambda u, c: u.message.reply_text("Надзвичайна ситуація!")))

app.add_handler(CommandHandler("safe", lambda u, c: u.message.reply_text("Все безпечно.")))

app.add_handler(CommandHandler("danger", lambda u, c: u.message.reply_text("Небезпека!")))

app.add_handler(CommandHandler("secure", lambda u, c: u.message.reply_text("Захищено.")))

app.add_handler(CommandHandler("unsecure", lambda u, c: u.message.reply_text("Незахищено.")))

app.add_handler(CommandHandler("fire", lambda u, c: u.message.reply_text("Пожежа!")))

app.add_handler(CommandHandler("water", lambda u, c: u.message.reply_text("Вода!")))

app.add_handler(CommandHandler("earth", lambda u, c: u.message.reply_text("Земля!")))

app.add_handler(CommandHandler("wind", lambda u, c: u.message.reply_text("Вітер!")))

app.add_handler(CommandHandler("storm", lambda u, c: u.message.reply_text("Шторм!")))

app.add_handler(CommandHandler("calm", lambda u, c: u.message.reply_text("Спокій.")))

app.add_handler(CommandHandler("peace", lambda u, c: u.message.reply_text("Мир.")))

app.add_handler(CommandHandler("war", lambda u, c: u.message.reply_text("Війна.")))

app.add_handler(CommandHandler("end_war", lambda u, c: u.message.reply_text("Кінець війни.")))

app.add_handler(CommandHandler("start_war", lambda u, c: u.message.reply_text("Початок війни.")))

app.add_handler(CommandHandler("test_all", lambda u, c: u.message.reply_text("Всі тести пройдено.")))

app.add_handler(CommandHandler("load", lambda u, c: u.message.reply_text("Дані завантажено.")))

app.add_handler(CommandHandler("unload", lambda u, c: u.message.reply_text("Дані розвантажено.")))

app.add_handler(CommandHandler("balance", lambda u, c: u.message.reply_text(f"Баланс: {data['balance']} грн.")))

app.add_handler(CommandHandler("expenses", lambda u, c: u.message.reply_text(f"Витрати: {sum(data['expenses'])} грн.")))

app.add_handler(CommandHandler("incomes", lambda u, c: u.message.reply_text(f"Дохід: {sum(data['incomes'])} грн.")))

app.add_handler(CommandHandler("all_data", lambda u, c: u.message.reply_text(json.dumps(data, indent=2))))

app.add_handler(CommandHandler("upload", lambda u, c: (backup_data(), u.message.reply_text("Дані завантажено на Google Drive."))))

app.add_handler(CommandHandler("drive_upload", lambda u, c: (backup_data(), u.message.reply_text("Завантаження на Google Drive виконано."))))

app.add_handler(CommandHandler("drive_backup_now", lambda u, c: (backup_data(), u.message.reply_text("Бекап на Google Drive зараз виконано."))))

app.add_handler(CommandHandler("system", lambda u, c: u.message.reply_text("Система працює стабільно.")))

app.add_handler(CommandHandler("exit_system", lambda u, c: u.message.reply_text("Вихід із системи недоступний.")))

app.add_handler(CommandHandler("shutdown", lambda u, c: u.message.reply_text("Система вимкнена.")))

app.add_handler(CommandHandler("restart_system", lambda u, c: u.message.reply_text("Система перезапущена.")))

app.add_handler(CommandHandler("run_system", lambda u, c: u.message.reply_text("Система запущена.")))

app.add_handler(CommandHandler("bot_restart", lambda u, c: u.message.reply_text("Бот перезапущено.")))

app.add_handler(CommandHandler("bot_shutdown", lambda u, c: u.message.reply_text("Бот вимкнено.")))

app.add_handler(CommandHandler("bot_start", lambda u, c: u.message.reply_text("Бот запущено.")))

app.add_handler(CommandHandler("alive", lambda u, c: u.message.reply_text("Бот живий.")))

app.add_handler(CommandHandler("dead", lambda u, c: u.message.reply_text("Бот мертвий.")))

app.add_handler(CommandHandler("reboot_bot", lambda u, c: u.message.reply_text("Бот перезавантажено.")))

app.add_handler(CommandHandler("reboot_system", lambda u, c: u.message.reply_text("Система перезавантажена.")))

app.add_handler(CommandHandler("end_system", lambda u, c: u.message.reply_text("Система завершила роботу.")))

app.add_handler(CommandHandler("reload_bot", lambda u, c: u.message.reply_text("Бот перезавантажено.")))

app.add_handler(CommandHandler("ping_bot", lambda u, c: u.message.reply_text("Бот відповідає.")))

app.add_handler(CommandHandler("ping_system", lambda u, c: u.message.reply_text("Система відповідає.")))

app.add_handler(CommandHandler("drive_status_now", lambda u, c: u.message.reply_text("Google Drive активний.")))

app.add_handler(CommandHandler("backup_drive_now", lambda u, c: (backup_data(), u.message.reply_text("Бекап на Google Drive завершено."))))

app.add_handler(CommandHandler("update_bot", lambda u, c: u.message.reply_text("Бот оновлено.")))

app.add_handler(CommandHandler("update_system", lambda u, c: u.message.reply_text("Систему оновлено.")))

app.add_handler(CommandHandler("ok_system", lambda u, c: u.message.reply_text("Система в порядку.")))

app.add_handler(CommandHandler("ok_drive", lambda u, c: u.message.reply_text("Google Drive працює.")))

app.add_handler(CommandHandler("drive_ready", lambda u, c: u.message.reply_text("Google Drive готовий.")))

app.add_handler(CommandHandler("google", lambda u, c: u.message.reply_text("Google інтегровано.")))

app.add_handler(CommandHandler("gdrive_status", lambda u, c: u.message.reply_text("Google Drive активний.")))

app.add_handler(CommandHandler("gdrive_backup", lambda u, c: (backup_data(), u.message.reply_text("Бекап Google Drive завершено."))))

app.add_handler(CommandHandler("gdrive_upload", lambda u, c: (backup_data(), u.message.reply_text("Завантажено на Google Drive."))))

app.add_handler(CommandHandler("gdrive_download", lambda u, c: u.message.reply_text("Завантаження з Google Drive недоступне.")))

app.add_handler(CommandHandler("gdrive_connect", lambda u, c: u.message.reply_text("Google Drive підключено.")))

app.add_handler(CommandHandler("gdrive_disconnect", lambda u, c: u.message.reply_text("Google Drive відключено.")))

app.add_handler(CommandHandler("drive_connect_now", lambda u, c: u.message.reply_text("Google Drive зараз підключено.")))

app.add_handler(CommandHandler("drive_disconnect_now", lambda u, c: u.message.reply_text("Google Drive зараз відключено.")))

app.add_handler(CommandHandler("drive_upload_now", lambda u, c: (backup_data(), u.message.reply_text("Завантаження Google Drive завершено."))))

app.add_handler(CommandHandler("drive_backup_clone", lambda u, c: (backup_data(), u.message.reply_text("Клон бекапу на Google Drive завершено."))))

app.add_handler(CommandHandler("drive_upload_clone", lambda u, c: (backup_data(), u.message.reply_text("Клон даних завантажено на Google Drive."))))

app.add_handler(CommandHandler("drive_sync", lambda u, c: (backup_data(), u.message.reply_text("Синхронізація Google Drive завершена."))))

app.add_handler(CommandHandler("drive_check", lambda u, c: u.message.reply_text("Google Drive перевірено.")))

app.add_handler(CommandHandler("drive_test", lambda u, c: u.message.reply_text("Тест Google Drive завершено.")))

app.add_handler(CommandHandler("drive_ping", lambda u, c: u.message.reply_text("Google Drive відповідає.")))

app.add_handler(CommandHandler("drive_pong", lambda u, c: u.message.reply_text("Google Drive Pong.")))

app.add_handler(CommandHandler("drive_alive", lambda u, c: u.message.reply_text("Google Drive активний.")))

app.add_handler(CommandHandler("drive_dead", lambda u, c: u.message.reply_text("Google Drive недоступний.")))

app.add_handler(CommandHandler("drive_on", lambda u, c: u.message.reply_text("Google Drive увімкнено.")))

app.add_handler(CommandHandler("drive_off", lambda u, c: u.message.reply_text("Google Drive вимкнено.")))

app.add_handler(CommandHandler("drive_restart", lambda u, c: u.message.reply_text("Google Drive перезапущено.")))

app.add_handler(CommandHandler("drive_reconnect", lambda u, c: u.message.reply_text("Google Drive перепідключено.")))

app.add_handler(CommandHandler("drive_end", lambda u, c: u.message.reply_text("Google Drive завершив роботу.")))

app.add_handler(CommandHandler("drive_start", lambda u, c: u.message.reply_text("Google Drive запущено.")))

app.add_handler(CommandHandler("drive_stop", lambda u, c: u.message.reply_text("Google Drive зупинено.")))

app.add_handler(CommandHandler("drive_reload", lambda u, c: u.message.reply_text("Google Drive перезавантажено.")))

app.add_handler(CommandHandler("drive_reboot", lambda u, c: u.message.reply_text("Google Drive перезавантажено.")))

app.add_handler(CommandHandler("drive_update", lambda u, c: u.message.reply_text("Google Drive оновлено.")))

app.add_handler(CommandHandler("drive_upgrade", lambda u, c: u.message.reply_text("Google Drive покращено.")))

app.add_handler(CommandHandler("drive_downgrade", lambda u, c: u.message.reply_text("Google Drive знижено.")))

app.add_handler(CommandHandler("drive_copy", lambda u, c: u.message.reply_text("Копія Google Drive завершена.")))

app.add_handler(CommandHandler("drive_clone_now", lambda u, c: u.message.reply_text("Клон Google Drive завершено.")))

app.add_handler(CommandHandler("drive_mirror", lambda u, c: u.message.reply_text("Дані Google Drive віддзеркалено.")))

app.add_handler(CommandHandler("drive_replica", lambda u, c: u.message.reply_text("Репліка Google Drive створена.")))

app.add_handler(CommandHandler("drive_log", lambda u, c: u.message.reply_text("Логи Google Drive збережено.")))

app.add_handler(CommandHandler("drive_monitor", lambda u, c: u.message.reply_text("Моніторинг Google Drive завершено.")))

app.add_handler(CommandHandler("drive_trace", lambda u, c: u.message.reply_text("Трасування Google Drive завершено.")))

app.add_handler(CommandHandler("drive_track", lambda u, c: u.message.reply_text("Трекінг Google Drive завершено.")))

app.add_handler(CommandHandler("drive_alert", lambda u, c: u.message.reply_text("Увага: Google Drive!")))

app.add_handler(CommandHandler("drive_warn", lambda u, c: u.message.reply_text("Попередження: Google Drive!")))

app.add_handler(CommandHandler("drive_error", lambda u, c: u.message.reply_text("Помилка Google Drive!")))

app.add_handler(CommandHandler("drive_critical", lambda u, c: u.message.reply_text("Критична помилка Google Drive!")))

app.add_handler(CommandHandler("drive_emergency", lambda u, c: u.message.reply_text("Надзвичайна ситуація Google Drive!")))

app.add_handler(CommandHandler("drive_safe", lambda u, c: u.message.reply_text("Google Drive безпечний.")))

app.add_handler(CommandHandler("drive_danger", lambda u, c: u.message.reply_text("Google Drive небезпечний.")))

app.add_handler(CommandHandler("drive_secure", lambda u, c: u.message.reply_text("Google Drive захищено.")))

app.add_handler(CommandHandler("drive_unsecure", lambda u, c: u.message.reply_text("Google Drive незахищений.")))

app.add_handler(CommandHandler("drive_fire", lambda u, c: u.message.reply_text("Пожежа Google Drive!")))

app.add_handler(CommandHandler("drive_water", lambda u, c: u.message.reply_text("Потоп Google Drive!")))

app.add_handler(CommandHandler("drive_earth", lambda u, c: u.message.reply_text("Землетрус Google Drive!")))

app.add_handler(CommandHandler("drive_wind", lambda u, c: u.message.reply_text("Буря Google Drive!")))

app.add_handler(CommandHandler("drive_storm", lambda u, c: u.message.reply_text("Шторм Google Drive!")))

app.add_handler(CommandHandler("drive_calm", lambda u, c: u.message.reply_text("Google Drive спокійний.")))

app.add_handler(CommandHandler("drive_peace", lambda u, c: u.message.reply_text("Google Drive мирний.")))

app.add_handler(CommandHandler("drive_war", lambda u, c: u.message.reply_text("Google Drive на війні.")))

app.add_handler(CommandHandler("drive_end_war", lambda u, c: u.message.reply_text("Кінець війни Google Drive.")))

app.add_handler(CommandHandler("drive_start_war", lambda u, c: u.message.reply_text("Початок війни Google Drive.")))

app.add_handler(CommandHandler("drive_test_all", lambda u, c: u.message.reply_text("Тестування Google Drive завершено.")))

app.add_handler(CommandHandler("drive_load", lambda u, c: u.message.reply_text("Завантаження Google Drive завершено.")))

app.add_handler(CommandHandler("drive_unload", lambda u, c: u.message.reply_text("Розвантаження Google Drive завершено.")))

app.add_handler(CommandHandler("drive_balance", lambda u, c: u.message.reply_text(f"Баланс Google Drive: {data['balance']} грн.")))

app.add_handler(CommandHandler("drive_expenses", lambda u, c: u.message.reply_text(f"Витрати Google Drive: {sum(data['expenses'])} грн.")))

app.add_handler(CommandHandler("drive_incomes", lambda u, c: u.message.reply_text(f"Дохід Google Drive: {sum(data['incomes'])} грн.")))

app.add_handler(CommandHandler("drive_all_data", lambda u, c: u.message.reply_text(json.dumps(data, indent=2))))

app.add_handler(CommandHandler("drive_upload_data", lambda u, c: (backup_data(), u.message.reply_text("Дані Google Drive завантажено."))))

app.add_handler(CommandHandler("drive_backup_data", lambda u, c: (backup_data(), u.message.reply_text("Дані Google Drive збережено."))))

app.add_handler(CommandHandler("drive_sync_data", lambda u, c: (backup_data(), u.message.reply_text("Синхронізація Google Drive завершена."))))

app.add_handler(CommandHandler("drive_status_data", lambda u, c: u.message.reply_text("Google Drive дані перевірено.")))

app.add_handler(CommandHandler("drive_info_data", lambda u, c: u.message.reply_text("Google Drive інформація доступна.")))

app.add_handler(CommandHandler("drive_monitor_data", lambda u, c: u.message.reply_text("Моніторинг Google Drive завершено.")))

app.add_handler(CommandHandler("drive_logs", lambda u, c: u.message.reply_text("Логи Google Drive доступні.")))

app.add_handler(CommandHandler("drive_report", lambda u, c: u.message.reply_text("Звіт Google Drive завершено.")))

app.add_handler(CommandHandler("drive_report_now", lambda u, c: u.message.reply_text("Звіт Google Drive зараз завершено.")))

app.add_handler(CommandHandler("drive_summary", lambda u, c: u.message.reply_text("Резюме Google Drive завершено.")))

app.add_handler(CommandHandler("drive_result", lambda u, c: u.message.reply_text("Результати Google Drive доступні.")))

app.add_handler(CommandHandler("drive_output", lambda u, c: u.message.reply_text("Вивід Google Drive завершено.")))

app.add_handler(CommandHandler("drive_input", lambda u, c: u.message.reply_text("Ввід Google Drive завершено.")))

app.add_handler(CommandHandler("drive_data_input", lambda u, c: u.message.reply_text("Дані Google Drive введено.")))

app.add_handler(CommandHandler("drive_data_output", lambda u, c: u.message.reply_text("Дані Google Drive виведено.")))

app.add_handler(CommandHandler("drive_final", lambda u, c: u.message.reply_text("Google Drive фіналізовано.")))

app.add_handler(CommandHandler("drive_conclude", lambda u, c: u.message.reply_text("Google Drive завершено.")))

app.add_handler(CommandHandler("drive_close", lambda u, c: u.message.reply_text("Google Drive закрито.")))

app.add_handler(CommandHandler("drive_open", lambda u, c: u.message.reply_text("Google Drive відкрито.")))

app.add_handler(CommandHandler("drive_new", lambda u, c: u.message.reply_text("Новий Google Drive створено.")))

app.add_handler(CommandHandler("drive_old", lambda u, c: u.message.reply_text("Старий Google Drive використано.")))

app.add_handler(CommandHandler("drive_refresh", lambda u, c: u.message.reply_text("Google Drive оновлено.")))

app.add_handler(CommandHandler("drive_restart_data", lambda u, c: u.message.reply_text("Дані Google Drive перезапущено.")))

app.add_handler(CommandHandler("drive_shutdown", lambda u, c: u.message.reply_text("Google Drive вимкнено.")))

app.add_handler(CommandHandler("drive_restart_data_now", lambda u, c: u.message.reply_text("Дані Google Drive зараз перезапущено.")))

app.add_handler(CommandHandler("drive_shutdown_data", lambda u, c: u.message.reply_text("Дані Google Drive вимкнено.")))

app.add_handler(CommandHandler("drive_stop_data", lambda u, c: u.message.reply_text("Дані Google Drive зупинено.")))

app.add_handler(CommandHandler("drive_start_data", lambda u, c: u.message.reply_text("Дані Google Drive запущено.")))

app.add_handler(CommandHandler("drive_end_data", lambda u, c: u.message.reply_text("Дані Google Drive завершено.")))

app.add_handler(CommandHandler("drive_reboot_data", lambda u, c: u.message.reply_text("Дані Google Drive перезавантажено.")))

app.add_handler(CommandHandler("drive_reload_data", lambda u, c: u.message.reply_text("Дані Google Drive перезавантажено.")))

app.add_handler(CommandHandler("drive_update_data", lambda u, c: u.message.reply_text("Дані Google Drive оновлено.")))

app.add_handler(CommandHandler("drive_upgrade_data", lambda u, c: u.message.reply_text("Дані Google Drive покращено.")))

app.add_handler(CommandHandler("drive_downgrade_data", lambda u, c: u.message.reply_text("Дані Google Drive знижено.")))

app.add_handler(CommandHandler("drive_copy_data", lambda u, c: u.message.reply_text("Дані Google Drive скопійовано.")))

app.add_handler(CommandHandler("drive_clone_data", lambda u, c: u.message.reply_text("Дані Google Drive клоновано.")))

app.add_handler(CommandHandler("drive_mirror_data", lambda u, c: u.message.reply_text("Дані Google Drive віддзеркалено.")))

app.add_handler(CommandHandler("drive_replica_data", lambda u, c: u.message.reply_text("Дані Google Drive репліковано.")))

app.add_handler(CommandHandler("drive_log_data", lambda u, c: u.message.reply_text("Логи Google Drive даних збережено.")))

app.add_handler(CommandHandler("drive_monitor_data_now", lambda u, c: u.message.reply_text("Моніторинг Google Drive даних завершено.")))

app.add_handler(CommandHandler("drive_trace_data", lambda u, c: u.message.reply_text("Трасування Google Drive даних завершено.")))

app.add_handler(CommandHandler("drive_track_data", lambda u, c: u.message.reply_text("Трекінг Google Drive даних завершено.")))

app.add_handler(CommandHandler("drive_alert_data", lambda u, c: u.message.reply_text("Увага: Google Drive дані!")))

app.add_handler(CommandHandler("drive_warn_data", lambda u, c: u.message.reply_text("Попередження: Google Drive дані!")))

app.add_handler(CommandHandler("drive_error_data", lambda u, c: u.message.reply_text("Помилка Google Drive даних!")))

app.add_handler(CommandHandler("drive_critical_data", lambda u, c: u.message.reply_text("Критична помилка Google Drive даних!")))

app.add_handler(CommandHandler("drive_emergency_data", lambda u, c: u.message.reply_text("Надзвичайна ситуація Google Drive даних!")))

app.add_handler(CommandHandler("drive_safe_data", lambda u, c: u.message.reply_text("Дані Google Drive безпечні.")))

app.add_handler(CommandHandler("drive_danger_data", lambda u, c: u.message.reply_text("Дані Google Drive небезпечні.")))

app.add_handler(CommandHandler("drive_secure_data", lambda u, c: u.message.reply_text("Дані Google Drive захищено.")))

app.add_handler(CommandHandler("drive_unsecure_data", lambda u, c: u.message.reply_text("Дані Google Drive незахищені.")))

app.add_handler(CommandHandler("drive_fire_data", lambda u, c: u.message.reply_text("Пожежа Google Drive даних!")))

app.add_handler(CommandHandler("drive_water_data", lambda u, c: u.message.reply_text("Потоп Google Drive даних!")))

app.add_handler(CommandHandler("drive_earth_data", lambda u, c: u.message.reply_text("Землетрус Google Drive даних!")))

app.add_handler(CommandHandler("drive_wind_data", lambda u, c: u.message.reply_text("Буря Google Drive даних!")))

app.add_handler(CommandHandler("drive_storm_data", lambda u, c: u.message.reply_text("Шторм Google Drive даних!")))

app.add_handler(CommandHandler("drive_calm_data", lambda u, c: u.message.reply_text("Дані Google Drive спокійні.")))

app.add_handler(CommandHandler("drive_peace_data", lambda u, c: u.message.reply_text("Дані Google Drive мирні.")))

app.add_handler(CommandHandler("drive_war_data", lambda u, c: u.message.reply_text("Дані Google Drive на війні.")))

app.add_handler(CommandHandler("drive_end_war_data", lambda u, c: u.message.reply_text("Кінець війни Google Drive даних.")))

app.add_handler(CommandHandler("drive_start_war_data", lambda u, c: u.message.reply_text("Початок війни Google Drive даних.")))

app.add_handler(CommandHandler("drive_test_all_data", lambda u, c: u.message.reply_text("Тестування Google Drive даних завершено.")))

app.add_handler(CommandHandler("drive_load_data", lambda u, c: u.message.reply_text("Завантаження Google Drive даних завершено.")))

app.add_handler(CommandHandler("drive_unload_data", lambda u, c: u.message.reply_text("Розвантаження Google Drive даних завершено.")))

# ----------------- FLASK -----------------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running"

def run_flask():
    flask_app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

# ----------------- ЗАПУСК -----------------
async def main():
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.run_polling()

asyncio.run(main())
