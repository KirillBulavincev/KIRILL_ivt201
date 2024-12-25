from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def start_menu():
    kb = InlineKeyboardBuilder()

    kb.row(InlineKeyboardButton(text='По запросу', callback_data='generate_text_on_query'),
           InlineKeyboardButton(text='Случайно', callback_data='generate_random_text'))
    kb.row(InlineKeyboardButton(text='Помощь', url='https://giga.chat/'))

    kb.row(InlineKeyboardButton(text='Личный кабинет', callback_data='personal_cabinet'))
    return kb.as_markup()


def after_text():
    kb = [[KeyboardButton(text='Главное меню')]]
    return ReplyKeyboardMarkup(keyboard=kb, one_time_keyboard=True, resize_keyboard=True)


def start_menu():
    kb = InlineKeyboardBuilder()

    kb.row(InlineKeyboardButton(text='По запросу', callback_data='generate_text_on_query'),
           InlineKeyboardButton(text='Случайно', callback_data='generate_random_text'))
    kb.row(InlineKeyboardButton(text='Генерация изображения',
                                callback_data='generate_image'))  # Добавляем кнопку для генерации изображения
    kb.row(InlineKeyboardButton(text='Помощь', url='https://giga.chat/'))
    kb.row(InlineKeyboardButton(text='Личный кабинет', callback_data='personal_cabinet'))

    return kb.as_markup()
