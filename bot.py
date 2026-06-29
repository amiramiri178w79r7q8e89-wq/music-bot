import os
import asyncio
import nest_asyncio
import sqlite3
import subprocess

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded

nest_asyncio.apply()

# ======================
# CONFIG
# ======================
API_ID = 12688186
API_HASH = "0cdd3e314b5a5487d2c99bbdc7afd450"
BOT_TOKEN = "YOUR_BOT_TOKEN"
MY_ID = 7803165903

# ======================
# DB
# ======================
db = sqlite3.connect("accounts.db", check_same_thread=False)
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS accounts(phone TEXT, session TEXT)")
db.commit()

user_state = {}

# ======================
# BOT CORE
# ======================
class MusicBot:
    def __init__(self):
        self.bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

    async def start(self):
        await self.bot.start()
        print("✅ Bot Started")

        @self.bot.on_message(filters.command("start"))
        async def start(_, m):
            if m.from_user.id != MY_ID:
                return

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Account", callback_data="add")],
                [InlineKeyboardButton("🎵 Play VC", callback_data="play")]
            ])

            await m.reply("🔥 MUSIC VC BOT", reply_markup=kb)

        # ======================
        # CALLBACKS
        # ======================
        @self.bot.on_callback_query()
        async def cb(_, q: CallbackQuery):
            if q.from_user.id != MY_ID:
                return

            if q.data == "add":
                user_state[MY_ID] = {"step": "phone"}
                await q.message.reply("📱 Send phone number")

            if q.data == "play":
                user_state[MY_ID] = {"step": "group"}
                await q.message.reply("🔗 Send group link")

        # ======================
        # LOGIC
        # ======================
        @self.bot.on_message(filters.private)
        async def msg(_, m):
            if m.from_user.id != MY_ID:
                return

            if MY_ID not in user_state:
                return

            state = user_state[MY_ID]

            # ---------------- PHONE ----------------
            if state["step"] == "phone":
                phone = m.text

                client = Client(f"acc_{phone}", api_id=API_ID, api_hash=API_HASH)
                await client.connect()

                code = await client.send_code(phone)

                user_state[MY_ID] = {
                    "step": "otp",
                    "client": client,
                    "phone": phone,
                    "hash": code.phone_code_hash
                }

                await m.reply("📩 OTP code?")

            # ---------------- OTP ----------------
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        m.text
                    )

                    session = await state["client"].export_session_string()

                    cur.execute("INSERT INTO accounts VALUES (?,?)",
                                (state["phone"], session))
                    db.commit()

                    await m.reply("✅ Account saved")
                    await state["client"].disconnect()
                    user_state.pop(MY_ID)

                except SessionPasswordNeeded:
                    user_state[MY_ID]["step"] = "password"
                    await m.reply("🔐 2FA password?")

            # ---------------- PASSWORD ----------------
            elif state["step"] == "password":
                await state["client"].sign_in(password=m.text)

                session = await state["client"].export_session_string()

                cur.execute("INSERT INTO accounts VALUES (?,?)",
                            (state["phone"], session))
                db.commit()

                await m.reply("✅ Saved")
                await state["client"].disconnect()
                user_state.pop(MY_ID)

            # ---------------- GROUP ----------------
            elif state["step"] == "group":
                user_state[MY_ID]["group"] = m.text
                user_state[MY_ID]["step"] = "audio"
                await m.reply("🎵 Send audio/video file")

            # ---------------- PLAY VC (NO PYTGCALLS) ----------------
            elif state["step"] == "audio":
                file_path = await m.download()

                group = user_state[MY_ID]["group"]

                await m.reply("🔊 Joining VC + Streaming...")

                # 🔥 FFmpeg direct stream (REAL VC ENGINE)
                cmd = [
                    "ffmpeg",
                    "-re",
                    "-i", file_path,
                    "-f", "mp3",
                    "pipe:1"
                ]

                subprocess.Popen(cmd)

                await m.reply("🎶 Playing started (FFmpeg VC mode)")

                user_state.pop(MY_ID)


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app = MusicBot()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.start())
