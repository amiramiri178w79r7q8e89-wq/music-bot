import nest_asyncio
nest_asyncio.apply()

import asyncio
import sqlite3
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded

# --- تنظیمات اصلی ---
API_ID = 12688186  
API_HASH = "0cdd3e3145b5a5487d2c99bbdc7afd450"
BOT_TOKEN = "8576876988:AAGBLHEz9IAQa9NwgG6L8tWZnUQjUifxu10"
MY_ID = 7803165903  

# --- دیتابیس ---
db = sqlite3.connect("accounts.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, session_string TEXT)")
db.commit()

user_states = {}

print("✅ Bot loaded")

class ProfessionalPanel:
    def __init__(self):
        self.bot = Client("manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

    async def show_main_menu(self, message):
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ اکانت", callback_data="add_acc"),
             InlineKeyboardButton("📊 لیست", callback_data="list_acc")],
            [InlineKeyboardButton("🎵 MP3", callback_data="send_mp3"),
             InlineKeyboardButton("🎬 MP4", callback_data="send_mp4")],
            [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
        ])
        await message.reply("پنل ربات 👇", reply_markup=buttons)

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
                await cq.message.reply("شماره را بفرست")

            elif data == "list_acc":
                cursor.execute("SELECT phone FROM accounts")
                rows = cursor.fetchall()
                text = "\n".join([r[0] for r in rows]) if rows else "خالی"
                await cq.message.reply(text)

            elif data == "help":
                await cq.message.reply("اول اکانت اضافه کن بعد استفاده کن")

        @self.bot.on_message(filters.private)
        async def msg(client, message):
            if message.from_user.id != MY_ID:
                return

            if MY_ID not in user_states:
                return

            state = user_states[MY_ID]
            text = message.text

            if state["step"] == "phone":
                user_states[MY_ID] = {"step": "otp", "phone": text}
                await message.reply("OTP رو بفرست")

            elif state["step"] == "otp":
                await message.reply("این نسخه پایدار فقط UI رو ساپورت میکنه ⚠️")

    async def run(self):
        await self.start()
        await idle()   # 🔥 مهم‌ترین فیکس

# --- اجرا ---
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = ProfessionalPanel()
    loop.run_until_complete(bot.run())
