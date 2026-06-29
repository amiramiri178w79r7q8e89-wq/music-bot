# ======================
# سلول اول: نصب و تنظیمات
# ======================

!pip install pyrogram tgcrypto nest_asyncio pytgcalls==3.0.0.dev6 tgcalls==3.0.0.dev6 yt-dlp

import nest_asyncio
nest_asyncio.apply()

import asyncio
import sqlite3

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded

from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped


# ======================
# تنظیمات اصلی (FIXED)
# ======================
API_ID = 12688186
API_HASH = "0cdd3e314b5a5487d2c99bbdc7afd450"
BOT_TOKEN = "8576876988:AAEW3VXtqkXAyDsMiapTQxYTkGzfcKPQHDw"
MY_ID = 7803165903


if not API_ID or not API_HASH or not BOT_TOKEN:
    raise Exception("❌ API_ID / API_HASH / BOT_TOKEN تنظیم نشده")


# ======================
# دیتابیس
# ======================
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

print("✅ مرحله اول: نصب و تنظیمات با موفقیت انجام شد.")


# ======================
# سلول دوم: ربات
# ======================
class ProfessionalPanel:
    def __init__(self):
        self.bot = Client(
            "manager_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )

        self.voice = PyTgCalls(self.bot)

    async def show_main_menu(self, message):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ اضافه کردن اکانت", callback_data="add_acc"),
             InlineKeyboardButton("📊 لیست اکانت‌ها", callback_data="list_acc")],

            [InlineKeyboardButton("🎵 موسیقی", callback_data="send_mp3"),
             InlineKeyboardButton("🎬 ویدیو", callback_data="send_mp4")],

            [InlineKeyboardButton("🚀 ورود به ویسکال", callback_data="join_voice")]
        ])

        await message.reply("🌟 پنل مدیریت ربات", reply_markup=kb)

    async def start(self):
        await self.bot.start()
        await self.voice.start()

        print("🚀 BOT STARTED")

        # ======================
        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_cmd(_, m):
            if m.from_user.id != MY_ID:
                return
            await self.show_main_menu(m)

        # ======================
        @self.bot.on_callback_query()
        async def cb(_, q: CallbackQuery):
            if q.from_user.id != MY_ID:
                return

            if q.data == "add_acc":
                user_states[MY_ID] = {"step": "phone"}
                await q.message.reply("📱 شماره را ارسال کن")

            elif q.data == "list_acc":
                cursor.execute("SELECT phone FROM accounts")
                rows = cursor.fetchall()

                text = "📊 لیست اکانت‌ها:\n" + "\n".join([r[0] for r in rows]) if rows else "خالیه"
                await q.message.reply(text)

            elif q.data == "join_voice":
                user_states[MY_ID] = {"step": "link"}
                await q.message.reply("🔗 لینک گروه را ارسال کن")

            elif q.data in ["send_mp3", "send_mp4"]:
                user_states[MY_ID] = {"step": "file"}
                await q.message.reply("📥 فایل را ارسال کن")

        # ======================
        @self.bot.on_message(filters.private)
        async def msg(_, m):
            if m.from_user.id != MY_ID:
                return

            if MY_ID not in user_states:
                return

            state = user_states[MY_ID]

            # ----------------------
            # PHONE
            # ----------------------
            if state["step"] == "phone":
                phone = m.text

                client = Client(f"acc_{phone}", api_id=API_ID, api_hash=API_HASH)
                await client.connect()

                code = await client.send_code(phone)

                user_states[MY_ID] = {
                    "step": "otp",
                    "client": client,
                    "phone": phone,
                    "hash": code.phone_code_hash
                }

                await m.reply("📩 کد OTP را ارسال کن")

            # ----------------------
            # OTP
            # ----------------------
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        m.text
                    )

                    session = await state["client"].export_session_string()

                    cursor.execute("INSERT OR REPLACE INTO accounts VALUES (?,?)",
                                   (state["phone"], session))
                    db.commit()

                    await m.reply("✅ اکانت ذخیره شد")
                    await state["client"].disconnect()
                    user_states.pop(MY_ID)

                except SessionPasswordNeeded:
                    user_states[MY_ID]["step"] = "password"
                    await m.reply("🔐 پسورد 2FA؟")

            # ----------------------
            # PASSWORD
            # ----------------------
            elif state["step"] == "password":
                await state["client"].sign_in(password=m.text)

                session = await state["client"].export_session_string()

                cursor.execute("INSERT OR REPLACE INTO accounts VALUES (?,?)",
                               (state["phone"], session))
                db.commit()

                await m.reply("✅ ذخیره شد")
                await state["client"].disconnect()
                user_states.pop(MY_ID)

            # ----------------------
            # LINK VC
            # ----------------------
            elif state["step"] == "link":
                user_states[MY_ID]["link"] = m.text
                user_states[MY_ID]["step"] = "file"
                await m.reply("📥 حالا فایل را ارسال کن")

            # ----------------------
            # FILE + PLAY VC (FIXED REAL)
            # ----------------------
            elif state["step"] == "file":
                file_path = await m.download()

                chat = user_states[MY_ID]["link"]

                await m.reply("🔊 ورود به ویسکال...")

                await self.voice.join_group_call(
                    chat,
                    AudioPiped(file_path)
                )

                await m.reply("🎶 در حال پخش")
                user_states.pop(MY_ID)


# ======================
# RUN
# ======================
if __name__ == "__main__":
    bot = ProfessionalPanel()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.start())
