import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =================== SOZLAMALAR ===================
BOT_TOKEN = "8335969395:AAEDVgSrqifUwf23--PcrR7tWHRd9KNF27A"
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@majburiy_kanal"
# ====================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

db = sqlite3.connect("kino.db")
cur = db.cursor()

# =================== DATABASE ======================
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

cur.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    movie_id INTEGER
)
""")

db.commit()
# ====================================================

# =================== FOYDALANUVCHI OBUNA ======================
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# =================== START / FOYDALANUVCHI QO‘SHISH ======================
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

    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Saqlanganlar", callback_data="saved")

    await msg.answer(
        "🎥 Kino botga xush kelibsiz!\n"
        "🔍 Inline qidiruv orqali yoki kod bilan kino oling.",
        reply_markup=kb.as_markup()
    )

# =================== ADMIN KINO QO‘SHISH ======================
@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def add_movie(msg: Message):
    if not msg.caption or "|" not in msg.caption:
        await msg.answer(
            "❗ Format noto‘g‘ri\n"
            "To‘g‘ri format:\n"
            "001|Kino nomi"
        )
        return

    code, title = msg.caption.split("|", 1)
    code = code.strip()
    title = title.strip()

    try:
        cur.execute(
            "INSERT INTO movies (code, title, file_id) VALUES (?,?,?)",
            (code, title, msg.video.file_id)
        )
        db.commit()
    except:
        await msg.answer("❌ Bu kod allaqachon mavjud")
        return

    await msg.answer(
        f"✅ Kino qo‘shildi\n"
        f"🎬 {title}\n"
        f"🔢 Kod: {code}"
    )

# =================== INLINE QIDIRUV ======================
@dp.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query
    cur.execute(
        "SELECT id,title,file_id FROM movies WHERE title LIKE ?",
        (f"%{text}%",)
    )
    movies = cur.fetchall()

    results = []
    for m in movies:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_{m[0]}")

        results.append(
            InlineQueryResultCachedVideo(
                id=str(m[0]),
                video_file_id=m[2],
                title=m[1],
                reply_markup=kb.as_markup()
            )
        )

    await query.answer(results, cache_time=1)

# =================== /KINO NOM OR KOD ======================
@dp.message(F.text.startswith("/kino"))
async def kino_cmd(msg: Message):
    text = msg.text.replace("/kino", "").strip()

    if not text:
        await msg.answer("❗ Foydalanish:\n/kino kino_nomi")
        return

    cur.execute(
        "SELECT id, title, file_id FROM movies WHERE title LIKE ?",
        (f"%{text}%",)
    )
    movies = cur.fetchall()

    if not movies:
        await msg.answer("❌ Kino topilmadi")
        return

    for m in movies:
        kb = InlineKeyboardBuilder()
        kb.button(text="💾 Saqlash", callback_data=f"save_{m[0]}")

        await bot.send_video(
            msg.from_user.id,
            m[2],
            caption=f"🎬 {m[1]}",
            reply_markup=kb.as_markup()
        )

# =================== FOYDALANUVCHI KOD BO‘YICHA KINO ======================
@dp.message(F.text.regexp(r"^\d{3}$"))
async def get_movie_by_code(msg: Message):
    code = msg.text

    cur.execute(
        "SELECT id, title, file_id FROM movies WHERE code = ?",
        (code,)
    )
    movie = cur.fetchone()

    if not movie:
        await msg.answer("❌ Bu kodda kino topilmadi")
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="💾 Saqlash", callback_data=f"save_{movie[0]}")

    await bot.send_video(
        msg.from_user.id,
        movie[2],
        caption=f"🎬 {movie[1]}\n🔢 Kod: {code}",
        reply_markup=kb.as_markup()
    )

# =================== SAQLASH TUGMASI ======================
@dp.callback_query(F.data.startswith("save_"))
async def save_movie(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])

    cur.execute(
        "INSERT INTO saved VALUES (?,?)",
        (call.from_user.id, movie_id)
    )
    db.commit()

    await call.answer("💾 Saqlandi")

# =================== SAQLANGANLAR ======================
@dp.callback_query(F.data == "saved")
async def saved_movies(call: CallbackQuery):
    cur.execute("""
        SELECT movies.title, movies.file_id
        FROM saved
        JOIN movies ON movies.id = saved.movie_id
        WHERE saved.user_id = ?
    """, (call.from_user.id,))

    data = cur.fetchall()
    if not data:
        await call.message.answer("❌ Saqlangan kinolar yo‘q")
        return

    for title, file_id in data:
        await bot.send_video(call.from_user.id, file_id, caption=title)

# =================== KINO O‘CHIRISH ======================
@dp.message(F.text == "/del")
async def delete_menu(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    cur.execute("SELECT id, title FROM movies")
    movies = cur.fetchall()

    if not movies:
        await msg.answer("❌ Kino yo‘q")
        return

    kb = InlineKeyboardBuilder()
    for m in movies:
        kb.button(text=f"🗑 {m[1]}", callback_data=f"del_{m[0]}")
    kb.adjust(1)

    await msg.answer(
        "🗑 O‘chirish uchun kinoni tanlang:",
        reply_markup=kb.as_markup()
    )

@dp.callback_query(F.data.startswith("del_"))
async def delete_movie(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    movie_id = int(call.data.split("_")[1])

    cur.execute("DELETE FROM saved WHERE movie_id = ?", (movie_id,))
    cur.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    db.commit()

    await call.message.edit_text("✅ Kino o‘chirildi")

# =================== STATISTIKA ======================
@dp.message(F.text == "/stat")
async def stat(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM movies")
    movies = cur.fetchone()[0]

    await msg.answer(
        f"📊 Statistika\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🎬 Kinolar: {movies}"
    )

# =================== BROADCAST ======================
@dp.message(F.text.startswith("/send"))
async def broadcast(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    text = msg.text.replace("/send", "").strip()
    if not text:
        await msg.answer("❗ Matn yozing")
        return

    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], text)
        except:
            pass

    await msg.answer("✅ Xabar yuborildi")

# =================== ASOSIY ======================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
