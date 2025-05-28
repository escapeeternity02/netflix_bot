from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def build_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Buy Netflix 1 Screen"))
    return kb

def build_duration_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("1m", "2m", "3m")
    kb.row("6m", "12m")
    return kb

def is_valid_duration(text):
    return text in ["1m", "2m", "3m", "6m", "12m"]