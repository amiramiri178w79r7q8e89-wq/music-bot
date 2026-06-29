import nest_asyncio
nest_asyncio.apply()

import asyncio
import sqlite3
import os

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import SessionPasswordNeeded


# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_ID = int(os.getenv("MY_ID"))


# ================= DB =================
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

print("✅ Bot Loaded")


# ================= BOT CLASS =================
class BotManager:

    def __init__(self):
        self.bot = Client(
            "bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )

    # ---------- UI ----------
    async def menu(self, msg):
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ اکانت", callback_data="add"),
                InlineKeyboardButton("📊 لیست", callback_data="list")
            ],
            [
                InlineKeyboardButton("🎧 ارسال فایل", callback_data="file")
            ]
        ])
        await msg.reply("پنل مدیریت", reply_markup=kb)

    # ---------- START ----------
    async def start(self):
        await self.bot.start()
        print("🚀 Bot Started")

        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_cmd(_, msg):
            if msg.from_user.id != MY_ID:
                return
            await self.menu(msg)

        # ---------- CALLBACK ----------
        @self.bot.on_callback_query()
        async def cb(_, cq):

            if cq.from_user.id != MY_ID:
                return

            data = cq.data

            if data == "add":
                user_states[MY_ID] = {"step": "phone"}
                await cq.message.reply("📱 شماره را بفرست")

            elif data == "list":
                cursor.execute("SELECT phone FROM accounts")
                rows = cursor.fetchall()
                await cq.message.reply("\n".join([r[0] for r in rows]) or "خالی")

            elif data == "file":
                user_states[MY_ID] = {"step": "file"}
                await cq.message.reply("📥 فایل بفرست")

        # ---------- MESSAGE HANDLER ----------
        @self.bot.on_message(filters.private)
        async def handler(_, msg):

            uid = msg.from_user.id
            if uid != MY_ID:
                return

            if uid not in user_states:
                return

            state = user_states[uid]
            text = msg.text

            # ================= PHONE =================
            if state["step"] == "phone":

                client = Client(
                    name=f"temp_{uid}",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    in_memory=True
                )

                await client.start()

                sent = await client.send_code(text)

                user_states[uid] = {
                    "step": "otp",
                    "client": client,
                    "phone": text,
                    "hash": sent.phone_code_hash
                }

                await msg.reply("📩 کد OTP را بفرست")
                return

            # ================= OTP =================
            if state["step"] == "otp":

                client = state["client"]

                try:
                    await client.sign_in(
                        phone_number=state["phone"],
                        phone_code_hash=state["hash"],
                        phone_code=text
                    )

                    await self.save_session(msg, client, state["phone"])

                except SessionPasswordNeeded:
                    user_states[uid]["step"] = "pass"
                    await msg.reply("🔐 رمز 2FA را بفرست")

                return

            # ================= PASSWORD =================
            if state["step"] == "pass":

                client = state["client"]

                await client.check_password(text)

                await self.save_session(msg, client, state["phone"])
                return

            # ================= FILE =================
            if state["step"] == "file":

                path = await msg.download()

                await msg.reply(f"✅ ذخیره شد:\n{path}")

                del user_states[uid]

    # ================= SAVE SESSION =================
    async def save_session(self, msg, client, phone):

        session = await client.export_session_string()

        cursor.execute(
            "INSERT OR REPLACE INTO accounts VALUES (?, ?)",
            (phone, session)
        )
        db.commit()

        await msg.reply("✅ اکانت ذخیره شد")

        await client.stop()

        del user_states[msg.from_user.id]


    # ================= RUN =================
    async def run(self):
        await self.start()


# ================= MAIN =================
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = BotManager()
    loop.run_until_complete(bot.run())
