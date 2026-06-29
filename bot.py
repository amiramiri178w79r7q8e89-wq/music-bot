# سلول اول: نصب و تنظیمات
!pip install pyrogram tgcrypto nest_asyncio pytgcalls

import nest_asyncio
nest_asyncio.apply()
import asyncio
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded, FloodWait
from pytgcalls import PyTgCalls

# --- تنظیمات اصلی ---
API_ID = 12688186  
API_HASH = "0cdd3e314b5a5487d2c99bbdc7afd450"
BOT_TOKEN = "8576876988:AAGBLHEz9IAQa9NwgG6L8tWZnUQjUifxu10"
MY_ID = 7803165903  

# --- دیتابیس ---
db = sqlite3.connect("accounts.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, session_string TEXT)")
db.commit()

user_states = {}
print("✅ مرحله اول: نصب و تنظیمات با موفقیت انجام شد.")  # سلول دوم: بدنه اصلی ربات
class ProfessionalPanel:
    def __init__(self):
        self.bot = Client("manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
        self.voice_client = PyTgCalls(self.bot)

    async def show_main_menu(self, message):
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ اضافه کردن اکانت", callback_data="add_acc"), 
             InlineKeyboardButton("📊 لیست اکانت‌ها", callback_data="list_acc")],
            [InlineKeyboardButton("🎵 موسیقی (MP3)", callback_data="send_mp3"), 
             InlineKeyboardButton("🎬 فیلم (MP4)", callback_data="send_mp4")],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"), 
             InlineKeyboardButton("ℹ️ راهنما", callback_data="help")],
            [InlineKeyboardButton("🚀 ورود به گروه/ویسکال", callback_data="join_voice_prompt")]
        ])
        await message.reply("🌟 **پنل مدیریت یوزر‌بات‌ها** 🌟", reply_markup=buttons)

    async def start(self):
        await self.bot.start()
        print("🚀 ربات روشن شد! در تلگرام /start بزنید.")

        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_cmd(client, message):
            if message.from_user.id != MY_ID: return
            await self.show_main_menu(message)

        @self.bot.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            user_id = callback_query.from_user.id
            if user_id != MY_ID: return
            data = callback_query.data

            if data == "back_to_main":
                await self.show_main_menu(callback_query.message)
            elif data == "add_acc":
                await callback_query.message.reply("📱 شماره را بفرستید (مثال: `+98912...`):", 
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="back_to_main")]]))
                user_states[user_id] = {"step": "phone"}
            elif data == "list_acc":
                cursor.execute("SELECT phone FROM accounts")
                rows = cursor.fetchall()
                if not rows: await callback_query.answer("هیچ اکانتی پیدا نشد!", show_alert=True)
                else:
                    text = "📑 اکانت‌ها:\n" + "\n".join([f"• `{r[0]}`" for r in rows])
                    await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]))
            elif data == "join_voice_prompt":
                await callback_query.message.reply("🔗 لینک عمومی یا خصوصی گروه را بفرستید:")
                user_states[user_id] = {"step": "waiting_link"}
            elif data == "send_mp3" or data == "send_mp4":
                await callback_query.message.reply("📥 فایل را بفرستید:")
                user_states[user_id] = {"step": "waiting_file"}
            elif data == "help":
                await callback_query.edit_message_text("📖 راهنما: ابتدا اکانت اضافه کنید، سپس لینک گروه را برای ورود بدهید.", 
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]))
            elif data == "settings":
                await callback_query.answer("⚙️ تنظیمات در حال توسعه است...", show_alert=True)

        @self.bot.on_message(filters.private)
        async def message_handler(client, message):
            user_id = message.from_user.id
            if user_id != MY_ID or user_id not in user_states: return
            state = user_states[user_id]
            text = message.text or message.caption

            if state["step"] == "phone":
                phone = text.strip()
                try:
                    temp = Client(f"temp_{phone}", api_id=API_ID, api_hash=API_HASH)
                    await temp.connect()
                    code = await temp.send_code(phone)
                    user_states[user_id] = {"step": "otp", "client": temp, "phone": phone, "hash": code.phone_code_hash}
                    await message.reply("📩 کد تایید (OTP) را بفرستید:")
                except Exception as e: await message.reply(f"❌ خطا: {e}")
            
            elif state["step"] == "otp":
                try:
                    await state["client"].sign_in(state["phone"], state["hash"], text.strip())
                    await self.finalize_acc(message, user_id, state["client"], state["phone"])
                except SessionPasswordNeeded:
                    user_states[user_id]["step"] = "password"
                    await message.reply("🔐 رمز دو مرحله‌ای (اگر دارید) را بفرستید:")
                except Exception as e: await message.reply(f"❌ خطا: {e}")

            elif state["step"] == "password":
                try:
                    await state["client"].sign_in(state["phone"], password=text.strip())
                    await self.finalize_acc(message, user_id, state["client"], state["phone"])
                except Exception as e: await message.reply(f"❌ خطا: {e}")

            elif state["step"] == "waiting_link":
                user_states[user_id]["link"] = text.strip()
                await message.reply("✅ لینک ذخیره شد. حالا فایل (MP3 یا MP4) را بفرستید تا پخش شود.")
                user_states[user_id]["step"] = "waiting_file"

            elif state["step"] == "waiting_file":
                await message.reply("🔄 فایل دریافت شد! در حال تلاش برا ورود به گروه و پخش فایل در ویس‌کال...")
                # منطق ورود به گروه و پخش در اینجا قرار می‌گیرد
                await self.voice_client.join(user_states[user_id]["link"])
                # پخش فایل
                await self.voice_client.play(user_states[user_id]["file_path"])
                del user_states[user_id]

    async def finalize_acc(self, message, user_id, client, phone):
        try:
            session_str = await client.export_session_string()
            cursor.execute("INSERT OR REPLACE INTO accounts (phone, session_string) VALUES (?, ?)", (phone, session_str))
            db.commit()
            await message.reply(f"✅ اکانت `{phone}` با موفقیت ذخیره شد!\n\n`{session_str}`", parse_mode="Markdown")
            await client.disconnect()
            if user_id in user_states: del user_states[user_id]
        except Exception as e:
            await message.reply(f"❌ خطا در ذخیره: {e}")

# سلول سوم: اجرای نهایی
if __name__ == "__main__":
    try:
        manager = ProfessionalPanel()
        # استفاده از loop دستی برای جلوگیری از خطای asyncio در کولب
        loop = asyncio.get_event_loop()
        loop.run_until_complete(manager.start())
    except KeyboardInterrupt:
        print("\n🚫 ربات توسط کاربر متوقف شد.")
    except Exception as e:
        print(f"❌ یک خطای غیرمنتظره رخ داد: {e}")
