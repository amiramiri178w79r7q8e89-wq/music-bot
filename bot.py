# ======================
# سلول اول: نصب و تنظیمات
# ======================
# pip install pyrogram tgcrypto nest_asyncio yt-dlp

import os
import nest_asyncio
import asyncio
import sqlite3

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded

nest_asyncio.apply()

# ======================
# تنظیمات اصلی (FIXED)
# ======================
API_ID = int(os.getenv("API_ID", "12688186"))
API_HASH = os.getenv("API_HASH", "0cdd3e314b5a5487d2c99bbdc7afd450")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8576876988:AAEW3VXtqkXAyDsMiapTQxYTkGzfcKPQHDw")
MY_ID = int(os.getenv("MY_ID", "7803165903"))

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
session TEXT
)
""")
db.commit()

user_states = {}

print("✅ Bot loaded")


# ======================
# سلول دوم: ربات اصلی
# ======================
class ProfessionalPanel:
    def __init__(self):
        self.bot = Client(
            "manager_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )

    async def show_menu(self, message):
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ اضافه کردن اکانت", callback_data="add_acc"),
                InlineKeyboardButton("📊 لیست اکانت‌ها", callback_data="list_acc")
            ],
            [
                InlineKeyboardButton("🎵 ارسال فایل", callback_data="send_file")
            ],
            [
                InlineKeyboardButton("ℹ️ راهنما", callback_data="help")
            ]
        ])
        await message.reply("🌟 پنل مدیریت حرفه‌ای 🌟", reply_markup=kb)

    async def start(self):
        await self.bot.start()
        print("🚀 Bot Started")

        # ======================
        # /start
        # ======================
        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_cmd(_, msg):
            if msg.from_user.id != MY_ID:
                return
            await self.show_menu(msg)

        # ======================
        # Callback
        # ======================
        @self.bot.on_callback_query()
        async def callback(_, q: CallbackQuery):
            if q.from_user.id != MY_ID:
                return

            data = q.data

            if data == "add_acc":
                user_states[MY_ID] = {"step": "phone"}
                await q.message.reply("📱 شماره را بفرست")

            elif data == "list_acc":
                cursor.execute("SELECT phone FROM accounts")
                rows = cursor.fetchall()

                if not rows:
                    await q.answer("هیچ اکانتی نیست", show_alert=True)
                    return

                text = "📊 اکانت‌ها:\n" + "\n".join([r[0] for r in rows])
                await q.message.reply(text)

            elif data == "send_file":
                user_states[MY_ID] = {"step": "file"}
                await q.message.reply("📥 فایل (MP3/MP4) بفرست")

            elif data == "help":
                await q.message.reply("📌 اول اکانت اضافه کن، بعد فایل بفرست.")

        # ======================
        # Messages flow
        # ======================
        @self.bot.on_message(filters.private)
        async def handler(_, msg):
            if msg.from_user.id != MY_ID:
                return

            if MY_ID not in user_states:
                return

            state = user_states[MY_ID]
            step = state["step"]

            # ----------------------
            # PHONE
            # ----------------------
            if step == "phone":
                phone = msg.text.strip()

                client = Client(
                    f"acc_{phone}",
                    api_id=API_ID,
                    api_hash=API_HASH
                )

                await client.connect()
                code = await client.send_code(phone)

                user_states[MY_ID] = {
                    "step": "otp",
                    "client": client,
                    "phone": phone,
                    "hash": code.phone_code_hash
                }

                await msg.reply("📩 کد را بفرست")

            # ----------------------
            # OTP
            # ----------------------
            elif step == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        msg.text.strip()
                    )

                    session = await state["client"].export_session_string()

                    cursor.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?,?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await msg.reply("✅ اکانت ذخیره شد")
                    await state["client"].disconnect()

                    user_states.pop(MY_ID)

                except SessionPasswordNeeded:
                    user_states[MY_ID]["step"] = "password"
                    await msg.reply("🔐 پسورد 2FA؟")

            # ----------------------
            # PASSWORD
            # ----------------------
            elif step == "password":
                await state["client"].sign_in(password=msg.text.strip())

                session = await state["client"].export_session_string()

                cursor.execute(
                    "INSERT OR REPLACE INTO accounts VALUES (?,?)",
                    (state["phone"], session)
                )
                db.commit()

                await msg.reply("✅ ذخیره شد")
                await state["client"].disconnect()

                user_states.pop(MY_ID)

            # ----------------------
            # FILE SAVE
            # ----------------------
            elif step == "file":
                file_path = await msg.download()

                await msg.reply(f"✅ فایل ذخیره شد:\n`{file_path}`")

                user_states.pop(MY_ID)


# ======================
# سلول سوم: اجرا
# ======================
if __name__ == "__main__":
    app = ProfessionalPanel()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.start())
