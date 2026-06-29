import nest_asyncio
nest_asyncio.apply()

import asyncio
import sqlite3
import os

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded

from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped


# =========================
# CONFIG FIXED (IMPORTANT)
# =========================
API_ID = int(os.getenv("API_ID", "12688186"))
API_HASH = os.getenv("API_HASH", "0cdd3e314b5a5487d2c99bbdc7afd450")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8576876988:AAEW3VXtqkXAyDsMiapTQxYTkGzfcKPQHDw")
MY_ID = int(os.getenv("MY_ID", "7803165903"))


# =========================
# DATABASE
# =========================
db = sqlite3.connect("accounts.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS accounts (
    phone TEXT PRIMARY KEY,
    session_string TEXT
)
""")
db.commit()

user_states = {}


# =========================
# BOT CLASS
# =========================
class ProfessionalPanel:
    def __init__(self):
        self.bot = Client(
            "music_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )

        self.voice = PyTgCalls(self.bot)

    async def start_menu(self, message):
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Account", callback_data="add")],
            [InlineKeyboardButton("📊 List Accounts", callback_data="list")],
            [InlineKeyboardButton("🎵 Send Music", callback_data="music")],
            [InlineKeyboardButton("🎧 Join Voice", callback_data="voice")]
        ])

        await message.reply("🎛 Panel Ready", reply_markup=buttons)

    async def run(self):
        await self.bot.start()
        await self.voice.start()

        print("✅ Bot Running")

        # ================= START =================
        @self.bot.on_message(filters.command("start") & filters.private)
        async def start(_, msg):
            if msg.from_user.id != MY_ID:
                return
            await self.start_menu(msg)

        # ================= CALLBACKS =================
        @self.bot.on_callback_query()
        async def cb(_, cq: CallbackQuery):

            uid = cq.from_user.id
            if uid != MY_ID:
                return

            data = cq.data

            if data == "add":
                user_states[uid] = {"step": "phone"}
                await cq.message.reply("Send phone number")

            elif data == "list":
                cursor.execute("SELECT phone FROM accounts")
                rows = cursor.fetchall()
                await cq.message.reply("\n".join([r[0] for r in rows]) or "Empty")

            elif data == "voice":
                user_states[uid] = {"step": "chat"}
                await cq.message.reply("Send chat link or ID")

            elif data == "music":
                user_states[uid] = {"step": "file"}
                await cq.message.reply("Send mp3 file")

        # ================= MESSAGE HANDLER =================
        @self.bot.on_message(filters.private)
        async def msg_handler(_, msg):

            uid = msg.from_user.id
            if uid != MY_ID:
                return

            if uid not in user_states:
                return

            state = user_states[uid]

            # ---------------- PHONE ----------------
            if state["step"] == "phone":
                phone = msg.text

                temp = Client("temp", api_id=API_ID, api_hash=API_HASH)
                await temp.connect()

                code = await temp.send_code(phone)

                user_states[uid] = {
                    "step": "otp",
                    "client": temp,
                    "phone": phone,
                    "hash": code.phone_code_hash
                }

                await msg.reply("Send OTP")

            # ---------------- OTP ----------------
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        msg.text
                    )

                    session = await state["client"].export_session_string()

                    cursor.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?, ?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await msg.reply("Saved ✔")
                    del user_states[uid]

                except SessionPasswordNeeded:
                    user_states[uid]["step"] = "pass"
                    await msg.reply("2FA password?")

            # ---------------- PASSWORD ----------------
            elif state["step"] == "pass":
                try:
                    await state["client"].sign_in(password=msg.text)

                    session = await state["client"].export_session_string()

                    cursor.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?, ?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await msg.reply("Saved ✔")
                    del user_states[uid]

                except Exception as e:
                    await msg.reply(str(e))

            # ---------------- CHAT ----------------
            elif state["step"] == "chat":

                chat = await self.bot.get_chat(msg.text)
                state["chat_id"] = chat.id

                user_states[uid]["step"] = "file"
                await msg.reply("Now send audio file")

            # ---------------- FILE + PLAY ----------------
            elif state["step"] == "file":

                file_path = await msg.download()

                chat_id = state.get("chat_id")

                if not chat_id:
                    await msg.reply("Chat not set")
                    return

                await self.voice.join_group_call(
                    chat_id,
                    AudioPiped(file_path)
                )

                await msg.reply("🎵 Playing...")
                del user_states[uid]


# =========================
# RUN
# =========================
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = ProfessionalPanel()
    loop.run_until_complete(app.run())
