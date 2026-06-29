# سلول اول: نصب و تنظیمات
!pip install pyrogram tgcrypto nest_asyncio

import nest_asyncio
nest_asyncio.apply()

import asyncio
import sqlite3

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import SessionPasswordNeeded

# ======================
# تنظیمات واقعی (FIXED)
# ======================
API_ID = 12688186
API_HASH = "0cdd3e314b5a5487d2c99bbdc7afd450"
BOT_TOKEN = "8576876988:AAEW3VXtqkXAyDsMiapTQxYTkGzfcKPQHDw"
MY_ID = 7803165903

# ======================
# DB
# ======================
db = sqlite3.connect("accounts.db", check_same_thread=False)
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS accounts(phone TEXT, session TEXT)")
db.commit()

user_states = {}

print("✅ سیستم آماده است")


# ======================
# BOT CLASS
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
            [InlineKeyboardButton("➕ اضافه کردن اکانت", callback_data="add")],
            [InlineKeyboardButton("📊 لیست اکانت‌ها", callback_data="list")],
            [InlineKeyboardButton("🎵 ارسال فایل", callback_data="send")]
        ])
        await message.reply("🔥 پنل مدیریت", reply_markup=kb)

    async def start(self):
        await self.bot.start()
        print("🚀 Bot Started")

        # START
        @self.bot.on_message(filters.command("start"))
        async def start_cmd(_, m):
            if m.from_user.id != MY_ID:
                return
            await self.show_menu(m)

        # CALLBACK
        @self.bot.on_callback_query()
        async def cb(_, q):
            if q.from_user.id != MY_ID:
                return

            if q.data == "add":
                user_states[MY_ID] = {"step": "phone"}
                await q.message.reply("📱 شماره را ارسال کن")

            if q.data == "list":
                cur.execute("SELECT phone FROM accounts")
                rows = cur.fetchall()

                if not rows:
                    await q.message.reply("هیچ اکانتی نیست")
                else:
                    txt = "\n".join([r[0] for r in rows])
                    await q.message.reply(txt)

            if q.data == "send":
                user_states[MY_ID] = {"step": "file"}
                await q.message.reply("📥 فایل بفرست")

        # MESSAGE HANDLER
        @self.bot.on_message(filters.private)
        async def msg(_, m):
            if m.from_user.id != MY_ID:
                return

            if MY_ID not in user_states:
                return

            state = user_states[MY_ID]

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

                user_states[MY_ID] = {
                    "step": "otp",
                    "client": client,
                    "phone": phone,
                    "hash": code.phone_code_hash
                }

                await m.reply("📩 کد تایید را ارسال کن")

            # OTP
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

                    await m.reply("✅ اکانت ذخیره شد")

                    await state["client"].disconnect()
                    user_states.pop(MY_ID)

                except SessionPasswordNeeded:
                    user_states[MY_ID]["step"] = "password"
                    await m.reply("🔐 پسورد 2FA؟")

            # PASSWORD
            elif state["step"] == "password":
                await state["client"].sign_in(password=m.text)

                session = await state["client"].export_session_string()

                cur.execute("INSERT INTO accounts VALUES (?,?)",
                            (state["phone"], session))
                db.commit()

                await m.reply("✅ ذخیره شد")
                await state["client"].disconnect()
                user_states.pop(MY_ID)

            # FILE SAVE (بدون ویسکال واقعی)
            elif state["step"] == "file":
                file_path = await m.download()

                await m.reply("✅ فایل ذخیره شد روی سرور\n📂 آماده استفاده هست")

                user_states.pop(MY_ID)


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app = ProfessionalPanel()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.start())
