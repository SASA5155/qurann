
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite
import datetime
import pytz

BOT_TOKEN = "8520176300:AAEU1qoEmP2Nn1Fu8_CYicS3jbgF016fN_8"
ADMIN_ID = 5166153612
DEFAULT_TZ = pytz.timezone("Africa/Cairo")

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect("data.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY)")
        await db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        await db.commit()

@dp.message(commands=["start"])
async def start_cmd(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ إضافة قناة", callback_data="add_ch")],
            [InlineKeyboardButton(text="📢 القنوات", callback_data="list_ch")],
            [InlineKeyboardButton(text="⏰ ضبط التواقيت", callback_data="times")]
        ])
        await msg.answer("هلا يا مدير 😎\nاختر من القائمة:", reply_markup=kb)
    else:
        await msg.answer("بوت نشر تلقائي — تابع قنوات القرآن.")

@dp.callback_query(lambda c: c.data == "add_ch")
async def add_channel(cb: types.CallbackQuery):
    await cb.message.answer("ابعتلي ID القناة (لازم البوت يكون أدمن فيها).")
    await cb.answer()

@dp.message()
async def add_channel_id(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    if msg.text.lstrip("-").isdigit():
        ch = int(msg.text)
        async with aiosqlite.connect("data.db") as db:
            await db.execute("INSERT OR IGNORE INTO channels (id) VALUES (?)", (ch,))
            await db.commit()
        await msg.answer("تم إضافة القناة ✔")
    else:
        await msg.answer("ID غير صالح.")

async def auto_poster():
    await init_db()
    while True:
        now = datetime.datetime.now(DEFAULT_TZ)
        hour = now.hour

        async with aiosqlite.connect("data.db") as db:
            cur = await db.execute("SELECT id FROM channels")
            channels = [row[0] for row in await cur.fetchall()]

        if hour == 6:
            text = "🌅 أذكار الصباح:\n<em>بسم الله الذي لا يضر..</em>"
        elif hour == 18:
            text = "🌆 أذكار المساء:\n<em>أمسينا وأمسى الملك لله..</em>"
        elif hour % 3 == 0:
            text = "📖 آية اليوم:\n<em>إِنَّ اللّهَ مَعَ الصَّابِرِينَ</em>"
        else:
            await asyncio.sleep(120)
            continue

        for ch in channels:
            try:
                await bot.send_message(ch, text)
            except:
                pass

        await asyncio.sleep(3600)

async def main():
    asyncio.create_task(auto_poster())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
