import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from aiohttp import web

# === CONFIG ===
BOT_TOKEN = '7760347190:AAFU8sCNijevrjQgWEKQ4IA_4XY1U3-lvRQ'
ADMIN_ID = 6249999953
GMAIL_USER = 'escapeeternity05@gmail.com'
GMAIL_PASS = 'Escapeeternity05$'
WEBHOOK_HOST = 'https://your-render-domain.onrender.com'  # <-- Replace with your Render URL
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH
PORT = 3000

# === Logging ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === Bot and Dispatcher ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# === Dummy DB and utils ===
user_states = {}
pending_payments = {}  # user_id: {duration, file_id}
gmail_accounts = [(GMAIL_USER, GMAIL_PASS)]
price_list = {'1m': 100, '2m': 190, '3m': 270, '6m': 520, '12m': 1000}

def get_price(duration):
    return price_list.get(duration, 0)

def set_price(duration, amount):
    price_list[duration] = amount

def add_pending_user(user_id, duration, file_id):
    pending_payments[user_id] = {'duration': duration, 'file_id': file_id}

def get_pending_users():
    return [(uid, info['duration']) for uid, info in pending_payments.items()]

def approve_user(user_id):
    pending_payments.pop(user_id, None)

def reject_user(user_id):
    pending_payments.pop(user_id, None)

def get_next_gmail():
    if gmail_accounts:
        return gmail_accounts[0]
    return None

def add_gmail(email, password):
    gmail_accounts.append((email, password))

def build_main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Buy Netflix 1 Screen"))
    return keyboard

def build_duration_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for dur in ['1m', '2m', '3m', '6m', '12m']:
        keyboard.add(types.KeyboardButton(dur))
    return keyboard

def is_valid_duration(text):
    return text in price_list

def check_gmail_for_code(user_id, code):
    return code.isdigit() and len(code) >= 4  # Dummy implementation

# === Handlers ===
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    logger.info(f"/start from {message.from_user.id}")
    user_states[message.from_user.id] = {}
    await message.answer("📺 Welcome! Choose your Netflix plan:", reply_markup=build_main_menu())

@dp.message_handler(lambda m: m.text == "Buy Netflix 1 Screen")
async def buy_1screen(message: types.Message):
    logger.info(f"User {message.from_user.id} wants to buy 1 screen Netflix")
    user_states[message.from_user.id] = {"step": "choose_duration"}
    await message.answer("⏱ Choose duration:", reply_markup=build_duration_menu())

@dp.message_handler(lambda m: is_valid_duration(m.text) and user_states.get(m.from_user.id, {}).get("step") == "choose_duration")
async def choose_duration(message: types.Message):
    duration = message.text
    price = get_price(duration)
    user_states[message.from_user.id] = {"step": "awaiting_payment", "duration": duration}
    logger.info(f"User {message.from_user.id} chose duration {duration} costing {price}")
    await message.answer(f"💰 Price for {duration}: ₹{price}\n\nPlease pay via UPI/USDT and send payment screenshot.")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def receive_payment_screenshot(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if not state or state.get("step") != "awaiting_payment":
        logger.warning(f"Unexpected payment screenshot from {user_id}")
        return
    duration = state["duration"]
    file_id = message.photo[-1].file_id
    add_pending_user(user_id, duration, file_id)
    logger.info(f"Received payment proof from {user_id} for {duration}")

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
    )
    await bot.send_message(ADMIN_ID, f"🧾 New payment request from user {user_id} for {duration}", reply_markup=keyboard)
    await message.answer("🕐 Payment sent. Waiting for admin approval.")

@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def on_approve(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Unauthorized", show_alert=True)
        logger.warning(f"Unauthorized approve attempt by {callback.from_user.id}")
        return
    user_id = int(callback.data.split("_")[1])
    gmail = get_next_gmail()
    if not gmail:
        await callback.message.answer("❌ No Gmail accounts available")
        logger.error("No Gmail account available for approval")
        return
    approve_user(user_id)
    logger.info(f"User {user_id} approved by admin")
    await bot.send_message(user_id, f"✅ Approved!\nLogin to this Gmail:\n\n📧 {gmail[0]}\n🔑 {gmail[1]}\n\nSend the Netflix login code here.")
    await callback.answer("User approved")

@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def on_reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Unauthorized", show_alert=True)
        logger.warning(f"Unauthorized reject attempt by {callback.from_user.id}")
        return
    user_id = int(callback.data.split("_")[1])
    reject_user(user_id)
    logger.info(f"User {user_id} rejected by admin")
    await bot.send_message(user_id, "❌ Your payment was rejected.")
    await callback.answer("User rejected")

@dp.message_handler(commands=["approve", "reject"])
async def manual_approve_reject(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Usage: /approve <user_id> or /reject <user_id>")
        return
    cmd, uid = parts
    try:
        user_id = int(uid)
    except:
        await message.answer("❌ Invalid user ID")
        return
    if cmd == "/approve":
        gmail = get_next_gmail()
        if not gmail:
            await message.answer("❌ No Gmail available.")
            return
        approve_user(user_id)
        await bot.send_message(user_id, f"✅ Approved!\nGmail: {gmail[0]}\nPass: {gmail[1]}")
        await message.answer(f"User {user_id} approved.")
    elif cmd == "/reject":
        reject_user(user_id)
        await bot.send_message(user_id, "❌ Your payment was rejected.")
        await message.answer(f"User {user_id} rejected.")
    else:
        await message.answer("❌ Unknown command. Use /approve or /reject.")

@dp.message_handler(commands=["set_price"])
async def cmd_set_price(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Usage: /set_price <duration> <amount>")
        return
    _, duration, amount = parts
    try:
        amount = int(amount)
        set_price(duration, amount)
        await message.answer(f"✅ Price for {duration} set to ₹{amount}")
    except:
        await message.answer("❌ Invalid amount")

@dp.message_handler(commands=["add_gmail"])
async def cmd_add_gmail(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Usage: /add_gmail <email> <pass>")
        return
    _, email, password = parts
    add_gmail(email, password)
    await message.answer("✅ Gmail added.")

@dp.message_handler(commands=["pending"])
async def cmd_pending(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    pending = get_pending_users()
    if not pending:
        await message.answer("No pending users.")
        return
    text = "\n".join([f"{uid} - {dur}" for uid, dur in pending])
    await message.answer(text)

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    help_text = (
        "User Commands:\n"
        "/start - Start bot\n"
        "/help - Show help\n"
        "Buy Netflix 1 Screen from menu.\n"
        "Send payment screenshot after choosing duration.\n"
        "After approval, receive login details.\n"
    )
    await message.answer(help_text)

# === Aiohttp web server and webhook setup ===
async def on_startup(app):
    logger.info("Setting webhook")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    logger.info("Removing webhook")
    await bot.delete_webhook()

app = web.Application()
app.router.add_post(WEBHOOK_PATH, dp.updates_handler)

if __name__ == '__main__':
    logger.info("Starting bot...")
    start_webhook(
        app,                 # pass app **as first positional argument**
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
       on_startup=on_startup,
on_shutdown=on_shutdown,
skip_updates=True,
host='0.0.0.0',
port=PORT,
)
