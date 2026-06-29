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
# CONFIG (FIXED)
# =========================
API_ID = int(os.getenv("API_ID", "12688186"))
API_HASH = os.getenv("API_HASH", "0cdd3e314b5a5487d2c99bbdc7afd450")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8576876988:AAEW3VXtqkXAyDsMiapTQxYTkGzfcKPQHDw")
MY_ID = int(os.getenv("MY_ID", "7803165903"))


# =========================
# DB
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
# MAIN BOT
# =========================
class ProfessionalPanel:
    def __init__(self):
        self.bot = Client(
            "manager_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )

        self.voice_client = PyTgCalls(self.bot)

    async def show_main_menu(self, message):
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ اضافه کردن اکانت", callback_data="add_acc"),
                InlineKeyboardButton("📊 لیست اکانت‌ها", callback_data="list_acc")
            ],
            [
                InlineKeyboardButton("🎵 موسیقی (MP3)", callback_data="send_mp3"),
                InlineKeyboardButton("🎬 فیلم (MP4)", callback_data="send_mp4")
            ],
            [
                InlineKeyboardButton("🚀 ورود به ویس", callback_data="join_voice_prompt")
            ]
        ])

        await message.reply("🌟 پنل مدیریت", reply_markup=buttons)

    async def start(self):
        await self.bot.start()
        await self.voice_client.start()

        print("✅ Bot loaded")

        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_cmd(client, message):
            if message.from_user.id != MY_ID:
                return
            await self.show_main_menu(message)

        @self.bot.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):

            user_id = callback_query.from_user.id
            if user_id != MY_ID:
                return

            data = callback_query.data

            if data == "back_to_main":
                await self.show_main_menu(callback_query.message)

            elif data == "add_acc":
                user_states[user_id] = {"step": "phone"}
                await callback_query.message.reply("📱 شماره را ارسال کنید")

            elif data == "list_acc":
                cursor.execute("SELECT phone FROM accounts")
                rows = cursor.fetchall()

                if not rows:
                    await callback_query.answer("هیچ اکانتی نیست", show_alert=True)
                else:
                    text = "\n".join([r[0] for r in rows])
                    await callback_query.message.reply(text)

            elif data == "join_voice_prompt":
                user_states[user_id] = {"step": "link"}
                await callback_query.message.reply("🔗 لینک گروه را بفرست")

            elif data in ["send_mp3", "send_mp4"]:
                user_states[user_id] = {"step": "file"}
                await callback_query.message.reply("📥 فایل را ارسال کن")

        @self.bot.on_message(filters.private)
        async def message_handler(client, message):

            user_id = message.from_user.id

            if user_id != MY_ID:
                return

            if user_id not in user_states:
                return

            state = user_states[user_id]

            # =====================
            # PHONE STEP
            # =====================
            if state["step"] == "phone":
                phone = message.text

                temp = Client(
                    f"temp_{phone}",
                    api_id=API_ID,
                    api_hash=API_HASH
                )

                await temp.connect()

                code = await temp.send_code(phone)

                user_states[user_id] = {
                    "step": "otp",
                    "client": temp,
                    "phone": phone,
                    "hash": code.phone_code_hash
                }

                await message.reply("کد را ارسال کن")

            # =====================
            # OTP STEP
            # =====================
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        message.text
                    )

                    session = await state["client"].export_session_string()

                    cursor.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?, ?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await message.reply("✅ اکانت ذخیره شد")
                    await state["client"].disconnect()

                    del user_states[user_id]

                except SessionPasswordNeeded:
                    user_states[user_id]["step"] = "password"
                    await message.reply("پسورد 2FA را بده")

            # =====================
            # PASSWORD STEP
            # =====================
            elif state["step"] == "password":
                try:
                    await state["client"].sign_in(password=message.text)
                    session = await state["client"].export_session_string()

                    cursor.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?, ?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await message.reply("✅ ذخیره شد")

                    del user_states[user_id]

                except Exception as e:
                    await message.reply(str(e))

            # =====================
            # VOICE LINK STEP
            # =====================
            elif state["step"] == "link":
                state["link"] = message.text
                state["step"] = "file"
                await message.reply("حالا فایل رو بفرست")

            # =====================
            # FILE STEP (FIXED)
            # =====================
            elif state["step"] == "file":

                file_path = await message.download()

                await self.voice_client.join_group_call(
                    chat_id=state.get("link"),
                    audio=AudioPiped(file_path)
                )

                await message.reply("🎵 پخش شروع شد")
                del user_states[user_id]

    async def run(self):
        await self.start()


# =========================
# RUN
# =========================
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = ProfessionalPanel()
    loop.run_until_complete(bot.run())
