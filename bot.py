import os
import asyncio
import sqlite3
import nest_asyncio

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded

nest_asyncio.apply()

# ======================
# CONFIG (FIXED)
# ======================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MY_ID = int(os.getenv("MY_ID", "0"))

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise Exception("❌ API_ID / API_HASH / BOT_TOKEN تنظیم نشده")

# ======================
# DATABASE
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

print("✅ Bot loaded")

# ======================
# PANEL
# ======================
class ProfessionalPanel:
    def __init__(self):
        self.bot = Client(
            "manager_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )

    async def show_main_menu(self, message):
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ اکانت", callback_data="add_acc"),
                InlineKeyboardButton("📊 لیست", callback_data="list_acc")
            ],
            [
                InlineKeyboardButton("🎵 ارسال فایل", callback_data="send_file")
            ],
            [
                InlineKeyboardButton("ℹ️ راهنما", callback_data="help")
            ]
        ])

        await message.reply("🌟 پنل مدیریت", reply_markup=kb)

    async def start(self):
        await self.bot.start()
        print("🚀 Bot started")

        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_cmd(client, message):
            if message.from_user.id != MY_ID:
                return
            await self.show_main_menu(message)

        @self.bot.on_callback_query()
        async def cb(client, cq: CallbackQuery):
            if cq.from_user.id != MY_ID:
                return

            data = cq.data

            if data == "add_acc":
                user_states[MY_ID] = {"step": "phone"}
                await cq.message.reply("📱 شماره را ارسال کن:")

            elif data == "list_acc":
                cursor.execute("SELECT phone FROM accounts")
                rows = cursor.fetchall()

                if not rows:
                    await cq.answer("خالیه", show_alert=True)
                else:
                    txt = "\n".join([r[0] for r in rows])
                    await cq.message.reply(f"📑 اکانت‌ها:\n{txt}")

            elif data == "send_file":
                user_states[MY_ID] = {"step": "file"}
                await cq.message.reply("🎵 فایل بفرست")

            elif data == "help":
                await cq.message.reply("شروع: /start")

        @self.bot.on_message(filters.private)
        async def msg(client, message):
            uid = message.from_user.id
            if uid != MY_ID or uid not in user_states:
                return

            state = user_states[uid]
            text = message.text

            # ======================
            # PHONE STEP
            # ======================
            if state["step"] == "phone":
                phone = text

                temp = Client(
                    f"temp_{phone}",
                    api_id=API_ID,
                    api_hash=API_HASH
                )

                await temp.connect()
                code = await temp.send_code(phone)

                user_states[uid] = {
                    "step": "otp",
                    "client": temp,
                    "phone": phone,
                    "hash": code.phone_code_hash
                }

                await message.reply("📩 کد را بفرست")

            # ======================
            # OTP
            # ======================
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        text
                    )

                    session = await state["client"].export_session_string()

                    cursor.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?,?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await message.reply("✅ اکانت ذخیره شد")
                    await state["client"].disconnect()
                    user_states.pop(uid)

                except SessionPasswordNeeded:
                    user_states[uid]["step"] = "password"
                    await message.reply("🔐 پسورد 2FA بده")

            # ======================
            # PASSWORD
            # ======================
            elif state["step"] == "password":
                try:
                    await state["client"].sign_in(password=text)
                    session = await state["client"].export_session_string()

                    cursor.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?,?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await message.reply("✅ ذخیره شد")
                    await state["client"].disconnect()
                    user_states.pop(uid)

                except Exception as e:
                    await message.reply(f"❌ {e}")

            # ======================
            # FILE SAVE ONLY
            # ======================
            elif state["step"] == "file":
                file_path = await message.download()

                await message.reply("✅ فایل ذخیره شد")
                print("Saved:", file_path)

                user_states.pop(uid)


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app = ProfessionalPanel()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.start())
