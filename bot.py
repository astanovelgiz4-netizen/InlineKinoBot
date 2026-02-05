import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =================== SOZLAMALAR ===================
BOT_TOKEN = "8335969395:AAEDVgSrqifUwf23--PcrR7tWHRd9KNF27A"
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@kinolashamz"
# =================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

db = sqlite3.connect("kino.db")
cur = db.cursor()

# =================== DATABASE =====================
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    file_id TEXT
)
""")
db.commit()
# =================================================

# =================== OBUNA TEKSHIRISH ===================
async def check_sub(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# =================== START ===================
@dp.message(F.text == "/start")
async def start(msg: Message):
    if not await check_sub(msg.from_user.id):
        await msg.answer(f"❗ Avval kanalga obuna bo‘ling:\n{CHANNEL_USERNAME}")
        return

    cur.execute(
        "INSERT OR IGNORE INTO users VALUES (?,?)",
        (msg.from_user.id, msg.from_user.username)
    )
    db.commit()

    await bot.send_message(
        ADMIN_ID,
        f"🆕 Yangi foydalanuvchi\n"
        f"👤 {msg.from_user.full_name}\n"
        f"🆔 {msg.from_user.id}"
    )

    await msg.answer("🎬 Xush kelibsiz!\n🔍 Inline qidiruv yoki 3 xonali kod yuboring.")

# =================== INLINE QIDIRUV (NOM) ===================
@dp.inline_query()
async def inline_search(q: InlineQuery):
    cur.execute(
        "SELECT title, file_id FROM movies WHERE title LIKE ?",
        (f"%{q.query}%",)
    )
    data = cur.fetchall()

    results = [
        InlineQueryResultCachedVideo(
            id=str(i),
            video_file_id=m[1],
            title=m[0]
        )
        for i, m in enumerate(data)
    ]
    await q.answer(results, cache_time=1)

# =================== KOD ORQALI KINO ===================
@dp.message(F.text.regexp(r"^\d{3}$"))
async def by_code(msg: Message):
    if not await check_sub(msg.from_user.id):
        await msg.answer(f"❗ Avval kanalga obuna bo‘ling:\n{CHANNEL_USERNAME}")
        return

    cur.execute(
        "SELECT title, file_id FROM movies WHERE code=?",
        (msg.text,)
    )
    m = cur.fetchone()

    if not m:
        await msg.answer("❌ Kino topilmadi")
        return

    await bot.send_video(msg.chat.id, m[1], caption=f"🎬 {m[0]}")

# =================== ADMIN PANEL ===================
@dp.message(F.text == "/panel")
async def panel(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kino qo‘shish", callback_data="add")
    kb.button(text="🗑 Kino o‘chirish", callback_data="del")
    kb.button(text="📊 Statistika", callback_data="stat")
    kb.button(text="📢 Xabar yuborish", callback_data="send")
    kb.adjust(1)

    await msg.answer("🛠 Admin panel", reply_markup=kb.as_markup())

# =================== KINO QO‘SHISH ===================
@dp.callback_query(F.data == "add")
async def add_info(call: CallbackQuery):
    await call.message.answer(
        "🎬 Video yuboring va captionga yozing:\n"
        "`001|Kino nomi`"
    )

@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def add_movie(msg: Message):
    if not msg.caption or "|" not in msg.caption:
        await msg.answer("❗ Format: 001|Kino nomi")
        return

    code, title = msg.caption.split("|", 1)
    try:
        cur.execute(
            "INSERT INTO movies (code,title,file_id) VALUES (?,?,?)",
            (code.strip(), title.strip(), msg.video.file_id)
        )
        db.commit()
        await msg.answer("✅ Kino qo‘shildi")
    except:
        await msg.answer("❌ Bu kod allaqachon mavjud")

# =================== KINO O‘CHIRISH ===================
@dp.callback_query(F.data == "del")
async def del_list(call: CallbackQuery):
    cur.execute("SELECT id,title FROM movies")
    movies = cur.fetchall()

    if not movies:
        await call.message.answer("❌ Kino yo‘q")
        return

    kb = InlineKeyboardBuilder()
    for m in movies:
        kb.button(text=f"🗑 {m[1]}", callback_data=f"d_{m[0]}")
    kb.adjust(1)

    await call.message.answer("O‘chirish uchun tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("d_"))
async def delete(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])
    cur.execute("DELETE FROM movies WHERE id=?", (movie_id,))
    db.commit()
    await call.message.edit_text("✅ O‘chirildi")

# =================== STATISTIKA ===================
@dp.callback_query(F.data == "stat")
async def stat(call: CallbackQuery):
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM movies")
    movies = cur.fetchone()[0]

    await call.message.answer(
        f"📊 Statistika\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🎬 Kinolar: {movies}"
    )

# =================== BROADCAST ===================
@dp.callback_query(F.data == "send")
async def send_info(call: CallbackQuery):
    await call.message.answer("📢 Yuboriladigan xabarni yozing:")

@dp.message(F.from_user.id == ADMIN_ID)
async def broadcast(msg: Message):
    if msg.text.startswith("/"):
        return

    cur.execute("SELECT user_id FROM users")
    for (uid,) in cur.fetchall():
        try:
            await bot.send_message(uid, msg.text)
        except:
            pass

    await msg.answer("✅ Xabar yuborildi")

# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
            
