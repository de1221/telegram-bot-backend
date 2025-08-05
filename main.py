
import os
import json
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
GOOGLE_CREDENTIALS_FILE = "google_creds.json"
SPREADSHEET_NAME = "Telegram Leads"
SEND_FILE_PATH = "your_file.pdf"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).sheet1

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚀 Открыть мини-приложение", web_app=WebAppInfo(url=WEBAPP_URL)))
    await msg.answer("Привет! Нажми на кнопку, чтобы открыть форму 👇", reply_markup=kb)

@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def handle_webapp(msg: types.Message):
    try:
        data = json.loads(msg.web_app_data.data)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([
            msg.from_user.full_name,
            data.get("name", ""),
            data.get("phone", ""),
            data.get("email", ""),
            now,
            "",
            ""
        ])
        await msg.answer_document(open(SEND_FILE_PATH, "rb"))
        await msg.answer("✅ Спасибо! Вот ваш файл. Мы скоро с вами свяжемся!")
        scheduler.add_job(send_day1, 'date', run_date=datetime.datetime.now() + datetime.timedelta(days=1), args=[msg.chat.id])
    except Exception as e:
        await msg.answer("Произошла ошибка при обработке формы.")
        print("ERROR in WebAppData:", e)

async def send_day1(chat_id):
    await bot.send_message(
        chat_id,
        "👋 Привет! Напоминаем, что вы можете забронировать установку или связаться с менеджером.",
        reply_markup=followup_kb()
    )
    scheduler.add_job(send_day2, 'date', run_date=datetime.datetime.now() + datetime.timedelta(days=1), args=[chat_id])

async def send_day2(chat_id):
    await bot.send_message(
        chat_id,
        "📌 Остались вопросы? Мы всегда на связи!",
        reply_markup=followup_kb()
    )

def followup_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📞 Связаться с менеджером", callback_data="contact"),
        types.InlineKeyboardButton("🛠 Забронировать установку", callback_data="book")
    )
    return kb

@dp.callback_query_handler(lambda c: c.data in ['contact', 'book'])
async def callbacks(call: types.CallbackQuery):
    action = 'Запрос на связь' if call.data == 'contact' else 'Бронирование'
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([
        call.from_user.full_name, "", "", "", now, action, "✅"
    ])
    await call.message.answer(f"✅ Ваш запрос «{action}» принят!")

if __name__ == '__main__':
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)
