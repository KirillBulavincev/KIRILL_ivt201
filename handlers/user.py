import os
import random
import re
import shutil
import uuid
import urllib3
import requests

from aiogram import Router, F
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram import types
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.filters import CommandStart

from config_data.config import Config, load_config
from keyboards import keyboards
from database import database
from GigaQueryEngine import create_random_text, prompts_text, create_image_from_query, default_message, gigachat

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
config: Config = load_config()
bot = Bot(token=config.tg_bot.token)
class UserStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_image_query = State()  # Добавлено новое состояние для запроса изображения


user_router = Router()


async def send_text(callback_or_message, state: FSMContext, theme_text=None, is_query=False):
    send_method = callback_or_message.message.answer if isinstance(callback_or_message, CallbackQuery) else callback_or_message.answer
    tg_id = callback_or_message.from_user.id if isinstance(callback_or_message, CallbackQuery) else callback_or_message.from_user.id

    try:
        await database.process_user_query(tg_id)
    except Exception:
        await send_method(text='У вас закончились бесплатные генерации!')
        await state.clear()
        return

    text = create_random_text(theme_text, is_query)
    await state.update_data(text_type=theme_text)

    await send_method(text=f"{text}", reply_markup=keyboards.after_text())

    await state.clear()


@user_router.message(CommandStart())
@user_router.message(F.text == 'Главное меню')
async def start_menu(message: Message, state: FSMContext):
    await database.add_user(message.from_user.id)

    await message.answer(
        text=f'Привет, {message.from_user.first_name}! Я бот ГигаЧат, я могу генерировать текста.\nВыбери действие:',
        reply_markup=keyboards.start_menu())
    await state.clear()


@user_router.callback_query(F.data == 'generate_random_text')
async def text_random(callback: CallbackQuery, state: FSMContext):
    prompt_text = random.choice(list(prompts_text.keys()))
    await send_text(callback, state, theme_text=prompt_text)


@user_router.callback_query(F.data == 'generate_text_on_query')
async def ask_for_query(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите желаемый запрос:")
    await state.set_state(UserStates.waiting_for_query)


@user_router.message(UserStates.waiting_for_query)
async def generate_text_from_query(message: Message, state: FSMContext):
    user_query = message.text

    try:
        await database.process_user_query(message.from_user.id)
    except Exception:
        await message.answer(
            text='У вас закончились бесплатные генерации!')
        await state.clear()
        return

    story = create_random_text(user_query, is_query=True)
    await message.answer(f"Вот ваш текст:\n{story}", reply_markup=keyboards.after_text())

    await state.clear()


@user_router.callback_query(F.data == 'personal_cabinet')
async def user_info(callback: CallbackQuery):
    user_info = await database.get_user_data(callback.from_user.id)
    text = f'Информация о пользователе:\nusername: @{callback.from_user.username}\nОсталось запросов: {user_info[1]} из 20'
    await callback.message.answer(text=text)



# Основная логика для генерации и отправки изображения
@user_router.callback_query(F.data == 'generate_image')
async def generate_image(callback: CallbackQuery, state: FSMContext):
    # Просим пользователя ввести запрос для изображения
    await callback.message.answer("Введите описание изображения (например, 'Нарисуй космонавта на лошади'):")
    # Переходим в состояние ожидания запроса для изображения
    await state.set_state(UserStates.waiting_for_image_query)  # Переход к состоянию ожидания изображения


@user_router.message(UserStates.waiting_for_image_query)
async def generate_image_from_query(message: Message, state: FSMContext):
    user_query = message.text

    try:
        await database.process_user_query(message.from_user.id)
    except Exception:
        await message.answer(text='У вас закончились бесплатные генерации!')
        await state.clear()
        return

    # Генерация изображения
    response = create_image_from_query(user_query)
    image_id = None
    # Извлекаем ID изображения из ответа
    if response and isinstance(response, dict) and 'choices' in response:
        print(response)
        content = response['choices'][0].get('message', {}).get('content', '')
        print(content)  # для отладки
        match = re.search(r'img src="([^"]+)"', content)  # добавлен тег <img>
        if match:
            image_id = match.group(1)
    print(response)  # Для отладки, чтобы увидеть весь ответ
    print(image_id)  # Для отладки, чтобы увидеть весь ответ
    if response:
        # Скачивание изображения с уникальным именем
        unique_filename = f"{uuid.uuid4()}.jpg"
        download_image(response)

        # Отправка изображения пользователю
        await send_image(message)

        # Опционально: удаление временного файла после отправки
        if os.path.exists(unique_filename):
            os.remove(unique_filename)
    else:
        await message.answer("Не удалось сгенерировать изображение, попробуйте снова.", reply_markup=keyboards.after_text())

    await state.clear()
def get_access_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    payload = 'scope=GIGACHAT_API_PERS'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': '98e63af2-f984-4064-a6db-867fd77a839b',
        'Authorization': 'Basic NTQwY2M1ODMtNTM5OC00ZDk3LTg2MDAtMmJjODhjYjdhYWIxOjMxNGVhMjI1LTczMzYtNDc3NC05Zjk2LWRjMTFlZjRkNmQyZA=='
    }

    # Выполнение запроса
    response = requests.post(url, headers=headers, data=payload, verify=False)

    # Проверка статуса ответа
    if response.status_code == 200:
        # Извлечение токена из JSON-ответа
        response_data = response.json()
        return response_data.get("access_token", "")
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

# Функция для скачивания изображения
access_token = get_access_token()
def download_image(image_id):
    url = f"https://gigachat.devices.sberbank.ru/api/v1/files/{image_id}/content"
    headers = {
        'Accept': 'application/jpg',
        'Authorization': f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers, stream=True, verify=False)
    print("Статус ответа:", response.status_code)
    if response.status_code == 200:
        with open('image.jpg', 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
    else:
        print("Ошибка загрузки файла. Ответ от сервера:", response.text)
        return None



async def send_image(message: Message):
    try:
        # Путь к изображению на вашем компьютере
        image_path = "path/to/your/image.jpg"
        # Используем InputFile для отправки изображения
        photo = FSInputFile("image.jpg")
        await bot.send_photo(chat_id=message.chat.id, photo=photo, caption="Вот ваша картинка!")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

