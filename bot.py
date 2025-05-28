import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiohttp import web

# === CONFIG ===
BOT_TOKEN = '7760347190:AAFU8sCNijevrjQgWEKQ4IA_4XY1U3-lvRQ'
ADMIN_ID = 6249999953  # Replace with real admin ID
GMAIL_USER = 'escapeeternity05@gmail.com'
WEBHOOK_HOST = 'https://netflix-bot-a9ii.onrender.com''
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH
PORT = 3000

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# State management
user_states = {}
pending_payments = {}
price_list_screen = {'1m': 89, '2m': 159, '3m': 235, '6m': 435, '12m': 599}
price_list_full = {'1m': 325, '3m': 775}
payment_methods = ['UPI/QR', 'USDT (Bep20)', 'Binance ID']
payment_info = {'upi': 'your-upi@upi', 'usdt': 'your-usdt-address', 'binance': 'binance-id'}

def build_main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Netflix 1 Screen", "Netflix Full Account")
    return keyboard

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Welcome! Choose a Netflix service:", reply_markup=build_main_menu())

@dp.message_handler(lambda m: m.text == "Netflix 1 Screen")
async def handle_1screen(message: types.Message):
    user_states[message.from_user.id] = {'type': 'screen'}
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for k, v in price_list_screen.items():
        keyboard.add(f"{k} - ₹{v}")
    await message.answer("Choose Duration:", reply_markup=keyboard)

@dp.message_handler(lambda m: m.text == "Netflix Full Account")
async def handle_full_account(message: types.Message):
    user_states[message.from_user.id] = {'type': 'full'}
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for k, v in price_list_full.items():
        keyboard.add(f"{k} - ₹{v}")
    await message.answer("Choose Duration:", reply_markup=keyboard)

@dp.message_handler(lambda m: any(x in m.text for x in ['1m', '3m', '2m', '6m', '12m']))
async def handle_duration(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_states: return
    duration = message.text.split()[0]
    user_states[user_id]['duration'] = duration

    if user_states[user_id]['type'] == 'full':
        user_states[user_id]['step'] = 'email'
        await message.answer("✉️ Please drop your email where you want the Netflix account:")
    else:
        user_states[user_id]['step'] = 'payment_method'
        await ask_payment_method(message)

@dp.message_handler(lambda m: '@' in m.text or '.' in m.text)
async def handle_email(message: types.Message):
    user_id = message.from_user.id
    if user_states.get(user_id, {}).get('step') != 'email':
        return
    user_states[user_id]['email'] = message.text
    user_states[user_id]['step'] = 'payment_method'
    await ask_payment_method(message)

async def ask_payment_method(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for method in payment_methods:
        keyboard.add(method)
    await message.answer("Please select a payment method to pay!", reply_markup=keyboard)

@dp.message_handler(lambda m: m.text in payment_methods)
async def handle_payment_method(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]['payment_method'] = message.text
    await message.answer(f"Pay to this address:
{payment_info[message.text.split()[0].lower()]}

After payment, send the screenshot.")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_screenshot(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return
    pending_payments[user_id] = user_states[user_id]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"))
    keyboard.add(types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}"))
    await bot.send_message(ADMIN_ID, f"New payment received from {user_id}:
{pending_payments[user_id]}", reply_markup=keyboard)
    await message.answer("Thanks for the payment! Admin will verify in 0-12 hours.")

@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    if user_states[user_id]['type'] == 'screen':
        await bot.send_message(user_id, f"✅ Payment Verified!
Login Gmail:
📧 {GMAIL_USER}
Please Use Sign-In Code to Login.
Tap 'OTP SENDED' when ready.")
    else:
        await bot.send_message(user_id, "✅ Payment Verified! Your account will be transferred to your mail soon.")
    await callback.answer("Approved")

@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def reject_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(user_id, "❌ Your payment was rejected.")
    await callback.answer("Rejected")

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

async def handle_webhook(request):
    data = await request.json()
    update = Update(**data)
    await dp.process_update(update)
    return web.Response()

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=PORT)
