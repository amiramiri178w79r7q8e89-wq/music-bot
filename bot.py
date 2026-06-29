import os
import asyncio
import nest_asyncio
import sqlite3

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import SessionPasswordNeeded

from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped

nest_asyncio.apply()

# ======================
# ENV (FIXED)
# ======================
API_ID = int(os.getenv("API_ID", "12688186"))
API_HASH = os.getenv("API_HASH", "0cdd3e314b5a5487d2c99bbdc7afd450")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8576876988:AAEW3VXtqkXAyDsMiapTQxYTkGzfcKPQHDw")
MY_ID = int(os.getenv("MY_ID", "7803165903"))

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise Exception("❌ API_ID / API_HASH / BOT_TOKEN تنظیم نشده")

# ======================
# DB
# ======================
db = sqlite3.connect("accounts.db", check_same_thread=False)
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS accounts(phone TEXT, session TEXT)")
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

        self.call = PyTgCalls(self.bot)

    async def start(self):
        await self.bot.start()
        await self.call.start()

        print("✅ BOT STARTED")

        @self.bot.on_message(filters.command("start"))
        async def start(_, m):
            if m.from_user.id != MY_ID:
                return

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Account", callback_data="add")],
                [InlineKeyboardButton("🎵 Play VC", callback_data="play")]
            ])

            await m.reply("🔥 MUSIC BOT ACTIVE", reply_markup=kb)

        # ======================
        # CALLBACK
        # ======================
        @self.bot.on_callback_query()
        async def cb(_, q):
            if q.from_user.id != MY_ID:
                return

            if q.data == "add":
                user_state[MY_ID] = {"step": "phone"}
                await q.message.reply("📱 شماره را ارسال کن")

            if q.data == "play":
                user_state[MY_ID] = {"step": "link"}
                await q.message.reply("🔗 لینک گروه VC را بفرست")

        # ======================
        # MESSAGE FLOW
        # ======================
        @self.bot.on_message(filters.private)
        async def msg(_, m):
            if m.from_user.id != MY_ID:
                return

            if MY_ID not in user_state:
                return

            state = user_state[MY_ID]

            # PHONE
            if state["step"] == "phone":
                phone = m.text

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

                await m.reply("📩 OTP را بفرست")

            # OTP
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        m.text
                    )

                    session = await state["client"].export_session_string()

                    cur.execute(
                        "INSERT INTO accounts VALUES (?,?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await m.reply("✅ Account Saved")
                    await state["client"].disconnect()
                    user_state.pop(MY_ID)

                except SessionPasswordNeeded:
                    user_state[MY_ID]["step"] = "password"
                    await m.reply("🔐 2FA password؟")

            # VC LINK
            elif state["step"] == "link":
                user_state[MY_ID]["link"] = m.text
                user_state[MY_ID]["step"] = "file"
                await m.reply("🎵 حالا فایل MP3 بده")

            # FILE + VC PLAY
            elif state["step"] == "file":
                file_path = await m.download()

                chat = user_state[MY_ID]["link"]

                await m.reply("🔊 Joining VC...")

                await self.call.join_group_call(
                    chat,
                    AudioPiped(file_path)
                )

                await m.reply("🎶 Playing in Voice Chat")

                user_state.pop(MY_ID)


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app = MusicBot()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.start())
