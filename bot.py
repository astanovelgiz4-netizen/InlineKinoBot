
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =================== SOZLAMALAR ===================
BOT_TOKEN = "8335969395:AAEDVgSrqifUwf23--PcrR7tWHRd9KNF27A"
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@kinolashamz"  # Majburiy obuna kanali
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

# =================== OBUNA TEKSHIRISH ===================
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# =================== START / MAJBURIY OBUNA ===================
@dp.message(F.text.startswith("/start"))
async def start(msg: Message):
    user_name = msg.from_user.full_name
    text = msg.text

    # URL orqali start parametri (masalan ?start=135)
    param = None
    if len(text.split()) > 1:
        param = text.split()[1]

    # Obuna tugmalari
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    kb.button(text="🔍 Tekshirish", callback_data="check_sub")
    kb.adjust(2)

    # Kanalga obuna bo‘lmasa
    if not await check_sub(msg.from_user.id):
        await msg.answer(
            f"Salom {user_name} siz botdan foydalanishingiz uchun avval 1 ta rasmiy kanalimizga obuna bo‘lishingiz kerak❗️",
            reply_markup=kb.as_markup()
        )
        return

    # Foydalanuvchi obuna bo‘lsa bazaga qo‘shish va adminga xabar
    cur.execute(
        "INSERT OR IGNORE INTO users VALUES (?,?)",
        (msg.from_user.id, msg.from_user.username)
    )
    db.commit()
    await bot.send_message(
        ADMIN_ID,
        f"🆕 Yangi foydalanuvchi\n👤 {user_name}\n🆔 {msg.from_user.id}"
    )

    # Agar URL parametri bo‘lsa va 3 xonali kod bo‘lsa
    if param and param.isdigit() and len(param) == 3:
        cur.execute(
            "SELECT title, file_id FROM movies WHERE code=?", (param,)
        )
        movie = cur.fetchone()
        if movie:
            await bot.send_video(
                msg.from_user.id,
                movie[1],
                caption=f"🎬 {movie[0]}\n🔢 Kod: {param}"
            )
        else:
            await msg.answer("❌ Bu kodda kino topilmadi")

    # Oddiy welcome xabari va inline qidiruv tugmasi
    kb2 = InlineKeyboardBuilder()
    kb2.button(text="🔍 Inline qidiruv", switch_inline_query_current_chat="")
    kb2.adjust(1)

    await msg.answer(
        f"🎬 Xush kelibsiz! {user_name}\nInline qidiruv orqali kinolarni topishingiz mumkin yoki kod bilan kino oling.",
        reply_markup=kb2.as_markup()
    )

# =================== Tekshirish tugmasi ===================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    user_name = call.from_user.full_name
    if await check_sub(call.from_user.id):
        # Obuna bo‘lgan bo‘lsa
        cur.execute(
            "INSERT OR IGNORE INTO users VALUES (?,?)",
            (call.from_user.id, call.from_user.username)
        )
        db.commit()
        await bot.send_message(
            ADMIN_ID,
            f"🆕 Yangi foydalanuvchi\n👤 {user_name}\n🆔 {call.from_user.id}"
        )

        kb2 = InlineKeyboardBuilder()
        kb2.button(text="🔍 Inline qidiruv", switch_inline_query_current_chat="")
        kb2.adjust(1)

        await call.message.edit_text(
            f"🎬 Xush kelibsiz! {user_name}\nInline qidiruv orqali kinolarni topishingiz mumkin yoki kod bilan kino oling.",
            reply_markup=kb2.as_markup()
        )
    else:
        await call.answer("❌ Siz hali kanalga obuna bo‘lmadingiz", show_alert=True)

# =================== INLINE QIDIRUV ===================
@dp.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query
    cur.execute(
        "SELECT id, title, file_id FROM movies WHERE title LIKE ?",
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

# =================== KOD ORQALI KINO ===================
@dp.message(F.text.regexp(r"^\d{3}$"))
async def by_code(msg: Message):
    if not await check_sub(msg.from_user.id):
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        kb.button(text="🔍 Tekshirish", callback_data="check_sub")
        kb.adjust(2)
        await msg.answer("❗ Avval kanalga obuna bo‘ling", reply_markup=kb.as_markup())
        return

    cur.execute(
        "SELECT id, title, file_id FROM movies WHERE code=?", (msg.text,)
    )
    movie = cur.fetchone()
    if not movie:
        await msg.answer("❌ Bu kodda kino topilmadi")
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="💾 Saqlash", callback_data=f"save_{movie[0]}")

    await bot.send_video(
        msg.chat.id,
        movie[2],
        caption=f"🎬 {movie[1]}\n🔢 Kod: {msg.text}",
        reply_markup=kb.as_markup()
    )

# =================== FOYDALANUVCHI KINO SAQLASH ===================
@dp.callback_query(F.data.startswith("save_"))
async def save_movie(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])
    cur.execute(
        "INSERT INTO saved VALUES (?,?)",
        (call.from_user.id, movie_id)
    )
    db.commit()
    await call.answer("💾 Saqlandi")

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
        "🎬 Video yuboring va captionga yozing:\n`001|Kino nomi`"
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
    cur.execute("DELETE FROM saved WHERE movie_id=?", (movie_id,))
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
        f"📊 Statistika\n👥 Foydalanuvchilar: {users}\n🎬 Kinolar: {movies}"
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
