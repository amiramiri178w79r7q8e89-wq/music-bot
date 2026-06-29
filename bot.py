import nest_asyncio
nest_asyncio.apply()

import asyncio
import sqlite3

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded

from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped


# ================= CONFIG =================
API_ID = 12688186
API_HASH = "0cdd3e314b5a5487d2c99bbdc7afd450"
BOT_TOKEN = "YOUR_BOT_TOKEN"
MY_ID = 7803165903


# ================= DATABASE =================
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

print("✅ Init done")


# ================= MAIN BOT =================
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
                InlineKeyboardButton("➕ اکانت", callback_data="add_acc"),
                InlineKeyboardButton("📊 لیست", callback_data="list_acc")
            ],
            [
                InlineKeyboardButton("🎵 MP3/MP4", callback_data="send_file"),
                InlineKeyboardButton("🚀 ویس", callback_data="join_voice_prompt")
            ],
            [
                InlineKeyboardButton("ℹ️ راهنما", callback_data="help")
            ]
        ])

        await message.reply("🌟 پنل ربات", reply_markup=buttons)

    async def start(self):
        await self.bot.start()
        await self.voice_client.start()

        print("🚀 Bot Started")

        # ============ START ============
        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_cmd(client, message):
            if message.from_user.id != MY_ID:
                return
            await self.show_main_menu(message)

        # ============ CALLBACKS ============
        @self.bot.on_callback_query()
        async def callback(client, cq: CallbackQuery):
            if cq.from_user.id != MY_ID:
                return

            data = cq.data

            if data == "add_acc":
                await cq.message.reply("📱 شماره را ارسال کن")
                user_states[MY_ID] = {"step": "phone"}

            elif data == "list_acc":
                cursor.execute("SELECT phone FROM accounts")
                rows = cursor.fetchall()

                if not rows:
                    await cq.answer("خالیه", show_alert=True)
                else:
                    txt = "\n".join([r[0] for r in rows])
                    await cq.message.reply(txt)

            elif data == "join_voice_prompt":
                await cq.message.reply("🔗 لینک گروه را بفرست")
                user_states[MY_ID] = {"step": "link"}

            elif data == "send_file":
                await cq.message.reply("🎵 فایل یا لینک موزیک را بفرست")
                user_states[MY_ID] = {"step": "file"}

        # ============ MESSAGE HANDLER ============
        @self.bot.on_message(filters.private)
        async def handler(client, message):
            if message.from_user.id != MY_ID:
                return

            state = user_states.get(MY_ID)
            if not state:
                return

            # -------- PHONE --------
            if state["step"] == "phone":
                phone = message.text.strip()

                temp = Client(
                    f"temp_{phone}",
                    api_id=API_ID,
                    api_hash=API_HASH
                )

                await temp.connect()
                sent = await temp.send_code(phone)

                user_states[MY_ID] = {
                    "step": "otp",
                    "client": temp,
                    "phone": phone,
                    "hash": sent.phone_code_hash
                }

                await message.reply("📩 کد را بفرست")

            # -------- OTP --------
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(
                        state["phone"],
                        state["hash"],
                        message.text.strip()
                    )

                    session = await state["client"].export_session_string()

                    cursor.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?, ?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await message.reply("✅ اکانت ذخیره شد")
                    await state["client"].disconnect()

                    user_states.pop(MY_ID, None)

                except SessionPasswordNeeded:
                    user_states[MY_ID]["step"] = "password"
                    await message.reply("🔐 پسورد 2FA را بده")

            # -------- PASSWORD --------
            elif state["step"] == "password":
                try:
                    await state["client"].sign_in(password=message.text.strip())

                    session = await state["client"].export_session_string()

                    cursor.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?, ?)",
                        (state["phone"], session)
                    )
                    db.commit()

                    await message.reply("✅ ذخیره شد")
                    await state["client"].disconnect()

                    user_states.pop(MY_ID, None)

                except Exception as e:
                    await message.reply(f"❌ {e}")

            # -------- LINK --------
            elif state["step"] == "link":
                user_states[MY_ID]["link"] = message.text.strip()
                user_states[MY_ID]["step"] = "file"
                await message.reply("🎵 حالا فایل موزیک را بفرست")

            # -------- FILE + VOICE CHAT FIX --------
            elif state["step"] == "file":
                file_path = await message.download()

                chat = user_states[MY_ID]["link"]

                try:
                    await self.voice_client.join_group_call(
                        chat,
                        AudioPiped(file_path)
                    )

                    await message.reply("🎶 در ویس چت پخش شد")

                except Exception as e:
                    await message.reply(f"❌ خطا: {e}")

                user_states.pop(MY_ID, None)


# ================= RUN =================
if __name__ == "__main__":
    bot = ProfessionalPanel()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.start())
