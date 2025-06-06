# Time Tracker Bot for Telegram with Formatted Duration (m:sec)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import datetime
import gspread
import telegram
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Sheets setup
gc = gspread.service_account(filename=os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE'))
sh = gc.open(os.getenv('GOOGLE_SHEETS_NAME'))
worksheet = sh.sheet1

# Whitelist of allowed users
ALLOWED_USERS = [int(user_id) for user_id in os.getenv('ALLOWED_USERS', '').split(',') if user_id.strip()]

active_sessions = {}
categories = ['💼 Работа', '🏋️ Спорт', '🌴 Отдых', '📚 Учёба', '🔧 Другое']
awaiting_category = {}
awaiting_activity_name = {}
awaiting_custom_interval = {}
goals_file = os.getenv('GOALS_FILE', 'goals.json')
record_file = os.getenv('RECORD_FILE', 'record.json')
interval_file = os.getenv('INTERVAL_FILE', 'user_intervals.json')

def load_json(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def is_user_allowed(user_id):
    return user_id in ALLOWED_USERS

goals = load_json(goals_file)
record = load_json(record_file)
user_intervals = load_json(interval_file)

def get_main_menu(user_id):
    keyboard = []
    if user_id not in active_sessions:
        keyboard.append([InlineKeyboardButton("▶️ Начать активность", callback_data="start_activity")])
    else:
        keyboard.append([InlineKeyboardButton("⏹️ Завершить активность", callback_data="stop_activity")])
    keyboard.append([InlineKeyboardButton("📅 Текущая активность", callback_data="current_activity")])
    keyboard.append([InlineKeyboardButton("📊 Отчёт за день", callback_data="daily_report")])
    keyboard.append([InlineKeyboardButton("🔔 Настройки напоминаний", callback_data="reminder_settings")])
    keyboard.append([InlineKeyboardButton("🎯 Моя цель", callback_data="my_goal")])
    keyboard.append([InlineKeyboardButton("🏆 Личный рекорд", callback_data="personal_best")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        await update.effective_chat.send_message("❌ У вас нет доступа к этому боту.")
        return
    
    reply_markup = get_main_menu(user_id)
    best = record.get(str(user_id), "ещё нет")
    if user_id in active_sessions:
        start_time = active_sessions[user_id]
        message_text = (
            f"👋 Привет! У тебя уже запущена активность.\n\n"
            f"🕒 Начата: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🏆 Личный рекорд: {best}\n\n"
            "Выбери действие:"
        )
    else:
        message_text = f"👋 Привет! Я бот для трекинга времени.\n🏆 Личный рекорд: {best}\n\nВыбери действие:"
    await update.effective_chat.send_message(message_text, reply_markup=reply_markup, parse_mode='Markdown')

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data
    if user_id in active_sessions:
        await context.bot.send_message(chat_id=user_id, text="🔔 Напоминание: активность всё ещё продолжается.")
    else:
        await context.bot.send_message(chat_id=user_id, text="🔔 Пора начать новую активность!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_user_allowed(user_id):
        await query.edit_message_text("❌ У вас нет доступа к этому боту.")
        return
    
    current_time = datetime.datetime.now()

    try:
        if query.data == "start_activity":
            if user_id in active_sessions:
                await query.edit_message_text("❗️ Активность уже запущена.", reply_markup=get_main_menu(user_id))
            else:
                active_sessions[user_id] = current_time
                await query.edit_message_text(
                    "✅ Активность начата! Нажмите \"Завершить активность\" когда закончите.",
                    reply_markup=get_main_menu(user_id)
                )
                minutes = user_intervals.get(str(user_id), 30)
                context.job_queue.run_repeating(send_reminder, interval=minutes*60, first=minutes*60, name=f"reminder_{user_id}", data=user_id)

        elif query.data.startswith("cat_"):
            category = query.data.split("_", 1)[1]
            if awaiting_category.get(user_id):
                context.user_data['category'] = category
                awaiting_category.pop(user_id)
                awaiting_activity_name[user_id] = True
                await query.edit_message_text(f"Категория выбрана: {category}. Введите название активности:")
            else:
                await query.edit_message_text("❗️ Неожиданный выбор категории.", reply_markup=get_main_menu(user_id))

        elif query.data == "stop_activity":
            if user_id in active_sessions:
                start_time = active_sessions.pop(user_id)
                end_time = current_time
                context.user_data['start_time'] = start_time
                context.user_data['end_time'] = end_time
                awaiting_category[user_id] = True
                jobs = context.job_queue.get_jobs_by_name(f"reminder_{user_id}")
                for job in jobs:
                    job.schedule_removal()
                keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in categories]
                await query.edit_message_text(
                    "Выберите категорию завершённой активности:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ Нет активной активности.", reply_markup=get_main_menu(user_id))

        elif query.data == "current_activity":
            if user_id in active_sessions:
                start_time = active_sessions[user_id]
                await query.edit_message_text(
                    f"📅 Активность начата в {start_time}",
                    reply_markup=get_main_menu(user_id)
                )
            else:
                await query.edit_message_text("❌ Нет активной активности.", reply_markup=get_main_menu(user_id))

        elif query.data == "daily_report":
            rows = worksheet.get_all_records()
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            report_lines = []
            for row in rows:
                start_time = row.get('Start Time', '')
                if start_time.startswith(today):
                    report_lines.append(f"- {row['Activity Name']} ({row['Category']}): {row['Duration']}")
            report_text = "📊 Отчёт за сегодня:\n" + "\n".join(report_lines) if report_lines else "❗️ Сегодня активностей не найдено."
            await query.edit_message_text(report_text, reply_markup=get_main_menu(user_id))

        elif query.data == "reminder_settings":
            keyboard = [
                [InlineKeyboardButton("15 мин", callback_data="set_interval_15")],
                [InlineKeyboardButton("30 мин", callback_data="set_interval_30")],
                [InlineKeyboardButton("60 мин", callback_data="set_interval_60")],
                [InlineKeyboardButton("✏️ Ввести свой интервал", callback_data="set_custom_interval")]
            ]
            await query.edit_message_text("🔔 Выбери интервал напоминаний:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif query.data.startswith("set_interval_"):
            minutes = int(query.data.split("_")[2])
            user_intervals[str(user_id)] = minutes
            save_json(interval_file, user_intervals)
            await query.edit_message_text(f"✅ Напоминания каждые {minutes} минут установлены.", reply_markup=get_main_menu(user_id))
            jobs = context.job_queue.get_jobs_by_name(f"reminder_{user_id}")
            for job in jobs:
                job.schedule_removal()
            context.job_queue.run_repeating(send_reminder, interval=minutes*60, first=minutes*60, name=f"reminder_{user_id}", data=user_id)

        elif query.data == "set_custom_interval":
            awaiting_custom_interval[user_id] = True
            await query.edit_message_text("✏️ Введи интервал в минутах (1-180):")

        elif query.data == "my_goal":
            goal = goals.get(str(user_id), "не установлена")
            await query.edit_message_text(f"🎯 Текущая цель: {goal}\n\nОтправь новую цель одним сообщением.", reply_markup=get_main_menu(user_id))
            context.user_data['awaiting_goal'] = True

        elif query.data == "personal_best":
            best = record.get(str(user_id), "ещё нет")
            await query.edit_message_text(f"🏆 Личный рекорд: {best} сек", reply_markup=get_main_menu(user_id))

    except telegram.error.BadRequest as e:
        if "Message is not modified" not in str(e):
            raise e

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return
    
    if context.user_data.get('awaiting_goal'):
        goal = update.message.text.strip()
        goals[str(user_id)] = goal
        save_json(goals_file, goals)
        context.user_data['awaiting_goal'] = False
        await update.message.reply_text(f"🎯 Цель установлена: {goal}", reply_markup=get_main_menu(user_id))
    elif awaiting_activity_name.get(user_id):
        activity_name = update.message.text.strip()
        category = context.user_data.get('category', 'Другое')
        start_time = context.user_data.pop('start_time', datetime.datetime.now())
        end_time = context.user_data.pop('end_time', datetime.datetime.now())
        awaiting_activity_name.pop(user_id)

        duration_seconds = int((end_time - start_time).total_seconds())
        minutes, seconds = divmod(duration_seconds, 60)
        duration_formatted = f"{minutes}:{seconds:02d}"

        worksheet.append_row([activity_name, category, str(start_time), str(end_time), duration_formatted])

        old_record = record.get(str(user_id), 0)
        if duration_seconds > float(old_record):
            record[str(user_id)] = duration_seconds
            save_json(record_file, record)
            record_text = "🏆 Это новый рекорд!"
        else:
            record_text = f"🏆 Личный рекорд: {old_record} сек"

        await update.message.reply_text(
            f"✅ Активность '{activity_name}' завершена.\nДлительность: {duration_formatted}\n{record_text}",
            reply_markup=get_main_menu(user_id)
        )
    elif awaiting_custom_interval.get(user_id):
        try:
            minutes = int(update.message.text.strip())
            if 1 <= minutes <= 180:
                user_intervals[str(user_id)] = minutes
                save_json(interval_file, user_intervals)
                awaiting_custom_interval.pop(user_id)
                await update.message.reply_text(f"✅ Напоминания каждые {minutes} минут установлены.", reply_markup=get_main_menu(user_id))
                jobs = context.job_queue.get_jobs_by_name(f"reminder_{user_id}")
                for job in jobs:
                    job.schedule_removal()
                context.job_queue.run_repeating(send_reminder, interval=minutes*60, first=minutes*60, name=f"reminder_{user_id}", data=user_id)
            else:
                await update.message.reply_text("❌ Введи число от 1 до 180 минут.")
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введи корректное число.")
    else:
        await update.message.reply_text("❗️ Пожалуйста, используй кнопки меню.", reply_markup=get_main_menu(user_id))

app = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.run_polling()
