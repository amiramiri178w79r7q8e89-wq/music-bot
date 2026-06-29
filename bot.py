import os
import asyncio
import nest_asyncio
import sqlite3

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded

from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped

nest_asyncio.apply()

# ======================
# CONFIG (FIXED)
# ======================
API_ID = int(os.getenv("API_ID", "12688186"))
API_HASH = os.getenv("API_HASH", "0cdd3e314b5a5487d2c99bbdc7afd450")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8576876988:AAEW3VXtqkXAyDsMiapTQxYTkGzfcKPQHDw")
MY_ID = int(os.getenv("MY_ID", "7803165903"))

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise Exception("❌ ENV NOT SET")

# ======================
# DB
# ======================
db = sqlite3.connect("accounts.db", check_same_thread=False)
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS accounts (
phone TEXT PRIMARY KEY,
session TEXT
)
""")
db.commit()

user_state = {}

# ======================
# BOT CLASS
# ======================
class MusicBot:
    def __init__(self):
        self.bot = Client(
            "bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )

        self.vc = PyTgCalls(self.bot)

    async def start(self):
        await self.bot.start()
        await self.vc.start()

        print("✅ BOT STARTED")

        # ================= START =================
        @self.bot.on_message(filters.command("start"))
        async def start(_, m):
            if m.from_user.id != MY_ID:
                return

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Account", callback_data="add")],
                [InlineKeyboardButton("🎵 Play VC", callback_data="play")]
            ])

            await m.reply("🔥 Music Bot Panel", reply_markup=kb)

        # ================= CALLBACKS =================
        @self.bot.on_callback_query()
        async def cb(_, q: CallbackQuery):
            if q.from_user.id != MY_ID:
                return

            if q.data == "add":
                user_state[MY_ID] = {"step": "phone"}
                await q.message.reply("📱 Send phone number:")

            elif q.data == "play":
                user_state[MY_ID] = {"step": "link"}
                await q.message.reply("🔗 Send group link")

        # ================= MESSAGE HANDLER =================
        @self.bot.on_message(filters.private)
        async def msg(_, m):
            if m.from_user.id != MY_ID:
                return

            if MY_ID not in user_state:
                return

            state = user_state[MY_ID]

            # ---------------- PHONE ----------------
            if state["step"] == "phone":
                phone = m.text.strip()

                client = Client(
                    f"acc_{phone}",
                    api_id=API_ID,
                    api_hash=API_HASH
                )

                await client.connect()
                code = await client.send_code(phone)

                user_state[MY_ID] = {
                    "step": "otp",
                    "client": client,
                    "phone": phone,
                    "hash": code.phone_code_hash
                }

                await m.reply("📩 Send OTP code")

            # ---------------- OTP ----------------
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        m.text.strip()
                    )

                    session = await state["client"].export_session_string()

                    cur.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?,?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await m.reply("✅ Account saved")
                    await state["client"].disconnect()
                    user_state.pop(MY_ID)

                except SessionPasswordNeeded:
                    user_state[MY_ID]["step"] = "password"
                    await m.reply("🔐 Send 2FA password")

            # ---------------- PASSWORD ----------------
            elif state["step"] == "password":
                await state["client"].sign_in(password=m.text.strip())

                session = await state["client"].export_session_string()

                cur.execute(
                    "INSERT OR REPLACE INTO accounts VALUES (?,?)",
                    (state["phone"], session)
                )
                db.commit()

                await m.reply("✅ 2FA login success")
                await state["client"].disconnect()
                user_state.pop(MY_ID)

            # ---------------- LINK ----------------
            elif state["step"] == "link":
                user_state[MY_ID] = {
                    "step": "file",
                    "chat": m.text.strip()
                }

                await m.reply("🎵 Now send audio/video file")

            # ---------------- FILE ----------------
            elif state["step"] == "file":
                file_path = await m.download()

                chat = user_state[MY_ID]["chat"]

                await m.reply("🔊 Joining VC...")

                try:
                    await self.vc.join_group_call(
                        chat,
                        AudioPiped(file_path)
                    )

                    await m.reply("🎶 Now playing in VC")

                except Exception as e:
                    await m.reply(f"❌ VC ERROR: {e}")

                user_state.pop(MY_ID)


# ======================
# RUN
# ======================
if __name__ == "__main__":
    bot = MusicBot()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.start())
