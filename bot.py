import os
import asyncio
import sqlite3

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import SessionPasswordNeeded

# =========================
# CONFIG (حتماً اینارو در ENV بزار)
# =========================

API_ID = int(os.getenv("API_ID", "12688186"))
API_HASH = os.getenv("API_HASH", "0cdd3e314b5a5487d2c99bbdc7afd450")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8576876988:AAEW3VXtqkXAyDsMiapTQxYTkGzfcKPQHDw")
MY_ID = int(os.getenv("MY_ID", "7803165903"))

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise Exception("❌ API_ID / API_HASH / BOT_TOKEN تنظیم نشده")

# =========================
# DATABASE
# =========================
db = sqlite3.connect("accounts.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS accounts (
    phone TEXT PRIMARY KEY,
    session TEXT
)
""")
db.commit()

# =========================
# STATE
# =========================
user_state = {}

# =========================
# BOT
# =========================
class MusicBot:
    def __init__(self):
        self.bot = Client(
            "music-bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )

    async def start(self):
        await self.bot.start()
        print("✅ BOT STARTED")

        # -------------------------
        # START MENU
        # -------------------------
        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_cmd(_, msg):
            if msg.from_user.id != MY_ID:
                return

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ افزودن اکانت", callback_data="add_acc")],
                [InlineKeyboardButton("📂 لیست اکانت‌ها", callback_data="list_acc")],
                [InlineKeyboardButton("🎵 ارسال فایل", callback_data="send_file")]
            ])

            await msg.reply("🔥 پنل مدیریت ربات", reply_markup=kb)

        # -------------------------
        # CALLBACKS
        # -------------------------
        @self.bot.on_callback_query()
        async def cb(_, q):
            if q.from_user.id != MY_ID:
                return

            if q.data == "add_acc":
                user_state[MY_ID] = {"step": "phone"}
                await q.message.reply("📱 شماره را ارسال کن:")

            elif q.data == "list_acc":
                cur.execute("SELECT phone FROM accounts")
                rows = cur.fetchall()

                if not rows:
                    await q.message.reply("❌ هیچ اکانتی نیست")
                    return

                text = "📌 Accounts:\n" + "\n".join([r[0] for r in rows])
                await q.message.reply(text)

            elif q.data == "send_file":
                user_state[MY_ID] = {"step": "file"}
                await q.message.reply("📁 فایل (mp3/mp4) بفرست")

        # -------------------------
        # MESSAGE HANDLER
        # -------------------------
        @self.bot.on_message(filters.private)
        async def handler(_, msg):
            if msg.from_user.id != MY_ID:
                return

            if MY_ID not in user_state:
                return

            state = user_state[MY_ID]

            # =====================
            # PHONE STEP
            # =====================
            if state["step"] == "phone":
                phone = msg.text.strip()

                client = Client(
                    f"acc_{phone}",
                    api_id=API_ID,
                    api_hash=API_HASH
                )

                await client.connect()
                sent = await client.send_code(phone)

                user_state[MY_ID] = {
                    "step": "otp",
                    "client": client,
                    "phone": phone,
                    "hash": sent.phone_code_hash
                }

                await msg.reply("📩 کد OTP را بفرست")

            # =====================
            # OTP STEP
            # =====================
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        msg.text.strip()
                    )

                    session = await state["client"].export_session_string()

                    cur.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?,?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await msg.reply("✅ اکانت ذخیره شد")
                    await state["client"].disconnect()

                    user_state.pop(MY_ID)

                except SessionPasswordNeeded:
                    user_state[MY_ID]["step"] = "password"
                    await msg.reply("🔐 رمز 2FA را بفرست")

                except Exception as e:
                    await msg.reply(f"❌ خطا: {e}")

            # =====================
            # PASSWORD STEP
            # =====================
            elif state["step"] == "password":
                try:
                    await state["client"].sign_in(password=msg.text.strip())

                    session = await state["client"].export_session_string()

                    cur.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?,?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await msg.reply("✅ اکانت (2FA) ذخیره شد")
                    await state["client"].disconnect()

                    user_state.pop(MY_ID)

                except Exception as e:
                    await msg.reply(f"❌ خطا: {e}")

            # =====================
            # FILE STEP (فقط ذخیره)
            # =====================
            elif state["step"] == "file":
                file_path = await msg.download()

                await msg.reply(
                    f"✅ فایل ذخیره شد:\n`{file_path}`\n\n"
                    "⚠️ (برای ویس‌کال نسخه پایدار باید pytgcalls جدا نصب شود)"
                )

                user_state.pop(MY_ID)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    bot = MusicBot()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.start())
