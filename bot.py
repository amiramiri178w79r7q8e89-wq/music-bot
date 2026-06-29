import os
import asyncio
import sqlite3

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import SessionPasswordNeeded

# =========================
# CONFIG
# =========================

API_ID = int(os.getenv("API_ID", "12688186"))
API_HASH = os.getenv("API_HASH", "0cdd3e314b5a5487d2c99bbdc7afd450")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8576876988:AAEW3VXtqkXAyDsMiapTQxYTkGzfcKPQHDw")
MY_ID = int(os.getenv("MY_ID", "7803165903"))

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise Exception("❌ ENV not set")

# =========================
# DB
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

state = {}

# =========================
# BOT
# =========================
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# =========================
# START
# =========================
@bot.on_message(filters.command("start"))
async def start(_, m):
    if m.from_user.id != MY_ID:
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Account", callback_data="add")],
        [InlineKeyboardButton("📂 List", callback_data="list")]
    ])

    await m.reply("🔥 PANEL", reply_markup=kb)


# =========================
# CALLBACK
# =========================
@bot.on_callback_query()
async def cb(_, q):
    if q.from_user.id != MY_ID:
        return

    if q.data == "add":
        state[MY_ID] = {"step": "phone"}
        await q.message.reply("📱 Send phone:")

    if q.data == "list":
        cur.execute("SELECT phone FROM accounts")
        rows = cur.fetchall()

        text = "\n".join([r[0] for r in rows]) or "empty"
        await q.message.reply(text)


# =========================
# MESSAGE FLOW
# =========================
@bot.on_message(filters.private)
async def msg(_, m):
    if m.from_user.id != MY_ID:
        return

    if MY_ID not in state:
        return

    st = state[MY_ID]

    # PHONE
    if st["step"] == "phone":
        phone = m.text.strip()

        client = Client(
            f"acc_{phone}",
            api_id=API_ID,
            api_hash=API_HASH
        )

        await client.connect()
        code = await client.send_code(phone)

        state[MY_ID] = {
            "step": "otp",
            "client": client,
            "phone": phone,
            "hash": code.phone_code_hash
        }

        await m.reply("📩 OTP?")

    # OTP
    elif st["step"] == "otp":
        try:
            await st["client"].sign_in(
                st["phone"],
                st["hash"],
                m.text.strip()
            )

            session = await st["client"].export_session_string()

            cur.execute(
                "INSERT OR REPLACE INTO accounts VALUES (?,?)",
                (st["phone"], session)
            )
            db.commit()

            await m.reply("✅ Saved")
            await st["client"].disconnect()

            state.pop(MY_ID)

        except SessionPasswordNeeded:
            state[MY_ID]["step"] = "password"
            await m.reply("🔐 2FA password")

    # PASSWORD
    elif st["step"] == "password":
        await st["client"].sign_in(password=m.text.strip())

        session = await st["client"].export_session_string()

        cur.execute(
            "INSERT OR REPLACE INTO accounts VALUES (?,?)",
            (st["phone"], session)
        )
        db.commit()

        await m.reply("✅ Saved 2FA")
        await st["client"].disconnect()

        state.pop(MY_ID)


# =========================
# RUN
# =========================
async def main():
    await bot.start()
    print("BOT RUNNING")
    await idle()

if __name__ == "__main__":
    import pyrogram
    from pyrogram import idle

    asyncio.get_event_loop().run_until_complete(main())
