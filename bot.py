import logging
from aiogram import Bot, Dispatcher, executor, types
from db import init_db, add_pending_user, get_price, set_price, get_next_gmail, add_gmail, get_pending_users, approve_user, reject_user
from gmail_checker import check_gmail_for_code
from utils import build_main_menu, build_duration_menu, is_valid_duration

# === CONFIG (Replace below) ===
BOT_TOKEN = '7760347190:AAFU8sCNijevrjQgWEKQ4IA_4XY1U3-lvRQ'
ADMIN_ID = 6249999953
GMAIL_USER = 'escapeeternity05@gmail.com'
GMAIL_PASS = 'Escapeeternity05$'

# === Init ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
init_db()

user_states = {}

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("📺 Welcome! Choose your Netflix plan:", reply_markup=build_main_menu())

@dp.message_handler(lambda m: m.text == "Buy Netflix 1 Screen")
async def buy_1screen(msg: types.Message):
    user_states[msg.from_user.id] = {"step": "choose_duration"}
    await msg.answer("⏱ Choose duration:", reply_markup=build_duration_menu())

@dp.message_handler(lambda m: is_valid_duration(m.text) and user_states.get(m.from_user.id, {}).get("step") == "choose_duration")
async def choose_duration(msg: types.Message):
    duration = msg.text
    price = get_price(duration)
    user_states[msg.from_user.id] = {"step": "awaiting_payment", "duration": duration}
    await msg.answer(f"💰 Price for {duration}: ₹{price}\n\nPlease pay via UPI/USDT and send payment screenshot.")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def receive_payment_proof(msg: types.Message):
    user_data = user_states.get(msg.from_user.id)
    if not user_data or user_data.get("step") != "awaiting_payment":
        return

    duration = user_data["duration"]
    file_id = msg.photo[-1].file_id
    add_pending_user(msg.from_user.id, duration, file_id)

    await bot.send_message(
        ADMIN_ID,
        f"🧾 New Payment Request\nUser: {msg.from_user.id}\nDuration: {duration}",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{msg.from_user.id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{msg.from_user.id}")
        )
    )
    await msg.answer("🕐 Payment sent. Waiting for admin approval.")

@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def handle_approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    gmail = get_next_gmail()
    if not gmail:
        await callback.message.answer("❌ No Gmail account available.")
        return

    approve_user(user_id)
    await bot.send_message(user_id, f"✅ Approved!\nLogin to this Gmail:\n\n📧 {gmail[0]}\n🔑 {gmail[1]}\n\nSend the Netflix login code here.")
    await callback.answer("User approved")

@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def handle_reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    reject_user(user_id)
    await bot.send_message(user_id, "❌ Your payment was rejected.")
    await callback.answer("User rejected")

@dp.message_handler(commands=["approve", "reject"])
async def manual_approval_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        cmd, uid = msg.text.split()
        user_id = int(uid)
        if cmd == "/approve":
            gmail = get_next_gmail()
            if not gmail:
                await msg.answer("No Gmail available.")
                return
            approve_user(user_id)
            await bot.send_message(user_id, f"✅ Approved!\nGmail: {gmail[0]}\nPass: {gmail[1]}")
        elif cmd == "/reject":
            reject_user(user_id)
            await bot.send_message(user_id, "❌ Your payment was rejected.")
    except:
        await msg.answer("❌ Usage: /approve <user_id>")

@dp.message_handler(commands=["set_price"])
async def set_price_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        _, duration, amount = msg.text.split()
        set_price(duration, int(amount))
        await msg.answer(f"✅ Price for {duration} set to ₹{amount}")
    except:
        await msg.answer("❌ Usage: /set_price 1m 100")

@dp.message_handler(commands=["add_gmail"])
async def add_gmail_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        _, email, password = msg.text.split()
        add_gmail(email, password)
        await msg.answer("✅ Gmail added.")
    except:
        await msg.answer("❌ Usage: /add_gmail email pass")

@dp.message_handler(commands=["pending"])
async def pending_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    pending = get_pending_users()
    text = "\n".join([f"{u[0]} - {u[1]}" for u in pending]) or "No pending users."
    await msg.answer(text)

@dp.message_handler()
async def handle_code(msg: types.Message):
    code = msg.text.strip()
    if len(code) >= 4 and code.isdigit():
        found = check_gmail_for_code(GMAIL_USER, GMAIL_PASS, code)
        if found:
            await msg.answer("✅ Code verified! You're logged in.")
        else:
            await msg.answer("❌ Code not found in Netflix emails. Try again.")