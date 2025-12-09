import asyncio
import aiosqlite
import datetime
import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, DefaultBotProperties
from aiogram.filters import Command, Text

BOT_TOKEN = "8520176300:AAEU1qoEmP2Nn1Fu8_CYicS3jbgF016fN_8"
ADMIN_ID = 5166153612
DB_PATH = 'quran_bot.db'
DEFAULT_TZ = pytz.timezone("Africa/Cairo")

# ---- Bot and Dispatcher ----
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher(bot)

# ---- Database setup ----
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER UNIQUE,
            lang TEXT DEFAULT 'ar',
            enabled_ayah INTEGER DEFAULT 1,
            enabled_hadith INTEGER DEFAULT 1,
            enabled_azkar_morning INTEGER DEFAULT 1,
            enabled_azkar_evening INTEGER DEFAULT 1,
            enabled_daily_recap INTEGER DEFAULT 1,
            enabled_audio INTEGER DEFAULT 1
        )
        """)
        await db.commit()

# ---- Admin commands ----
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton('➕ إضافة قناة', callback_data='add_ch')],
            [InlineKeyboardButton('📢 القنوات', callback_data='list_ch')],
            [InlineKeyboardButton('⏰ ضبط الأوقات', callback_data='times')]
        ])
        await msg.answer("لوحة تحكم المشرف", reply_markup=kb)
    else:
        await msg.answer("بوت نشر تلقائي للقرآن والأذكار")

@dp.callback_query(Text("add_ch"))
async def add_channel_cb(cb: types.CallbackQuery):
    await cb.message.answer("ارسل معرف القناة (ID) ولغتها ar/en مفصولة بمسافة")
    await cb.answer()

# ---- Admin message handler for adding channels ----
@dp.message()
async def add_channel(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    parts = msg.text.split()
    if len(parts) != 2:
        await msg.reply("صيغة خاطئة. مثال: -100123456789 ar")
        return
    try:
        ch_id, lang = int(parts[0]), parts[1]
    except ValueError:
        await msg.reply("معرف القناة يجب أن يكون رقماً صحيحاً")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO channels(channel_id, lang) VALUES (?,?)", (ch_id, lang))
        await db.commit()
    await msg.reply(f"تم إضافة القناة {ch_id} باللغة {lang}")

# ---- Content fetching ----
async def fetch_content(kind: str, lang: str):
    if kind == 'ayah':
        return 'بسم الله الرحمن الرحيم' if lang=='ar' else 'In the name of Allah, the Most Gracious'
    elif kind == 'hadith':
        return 'عن النبي ﷺ: خيركم من تعلم القرآن وعلمه' if lang=='ar' else 'The best of you are those who learn and teach the Qur’an.'
    elif kind == 'azkar_morning':
        return 'أذكار الصباح' if lang=='ar' else 'Morning Remembrance'
    elif kind == 'azkar_evening':
        return 'أذكار المساء' if lang=='ar' else 'Evening Remembrance'
    elif kind == 'daily_recap':
        return 'ملخص اليوم' if lang=='ar' else 'Daily Recap'
    elif kind == 'audio':
        return {'file_id': None, 'url': 'https://example.com/sample.mp3', 'caption': 'تلاوة قصيرة' if lang=='ar' else 'Short recitation'}
    return None

# ---- Scheduler ----
async def auto_poster():
    while True:
        now = datetime.datetime.now(DEFAULT_TZ)
        hour = now.hour
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("""
                SELECT channel_id, lang, enabled_ayah, enabled_hadith, enabled_azkar_morning,
                       enabled_azkar_evening, enabled_daily_recap, enabled_audio
                FROM channels
            """)
            channels = await cur.fetchall()

        for ch_id, lang, e_ayah, e_hadith, e_morn, e_even, e_recap, e_audio in channels:
            content = None
            if hour == 6 and e_morn:
                content = await fetch_content('azkar_morning', lang)
            elif hour == 18 and e_even:
                content = await fetch_content('azkar_evening', lang)
            elif hour % 3 == 0 and e_ayah:
                content = await fetch_content('ayah', lang)

            if content is None:
                continue

            try:
                if isinstance(content, dict):
                    if content.get('file_id'):
                        await bot.send_audio(ch_id, content['file_id'], caption=content.get('caption'))
                    else:
                        await bot.send_audio(ch_id, content['url'], caption=content.get('caption'))
                else:
                    await bot.send_message(ch_id, content)
            except Exception as e:
                print(f"خطأ أثناء الإرسال للقناة {ch_id}: {e}")

        await asyncio.sleep(3600)

# ---- Main ----
async def main():
    await init_db()
    asyncio.create_task(auto_poster())
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
