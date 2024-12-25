import os
import random
import re
import shutil
import uuid

import urllib3
import requests
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InputFile
from aiogram.filters import CommandStart
from gigachat.models import Chat, Messages, MessagesRole

from keyboards import keyboards
from database import database
from GigaQueryEngine import create_random_text, prompts_text, create_image_from_query, default_message, gigachat

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

    if response:
        # Скачивание изображения с уникальным именем
        unique_filename = f"{uuid.uuid4()}.jpg"
        download_image(response, unique_filename)

        # Отправка изображения пользователю
        await send_image(message, unique_filename, caption="Вот ваше сгенерированное изображение!")

        # Опционально: удаление временного файла после отправки
        if os.path.exists(unique_filename):
            os.remove(unique_filename)
    else:
        await message.answer("Не удалось сгенерировать изображение, попробуйте снова.", reply_markup=keyboards.after_text())

    await state.clear()
# Функция для скачивания изображения
def download_image(image_id, file_name: str):
    url = f"https://gigachat.devices.sberbank.ru/api/v1/files/{image_id}/content"

    headers = {
        'Accept': 'application/jpg',
        'Authorization': 'Bearer eyJjdHkiOiJqd3QiLCJlbmMiOiJBMjU2Q0JDLUhTNTEyIiwiYWxnIjoiUlNBLU9BRVAtMjU2In0.U4fpkxcj2i8EmEm0d8i4RAwdT58cn995YXqXoqdyW1JbPdajE3jVysv_LdCWdLtI8sic-m-3ZmsZZaUN7vT_KfrGNU_hmsEe9x3WFh1TO_g1hLrIP3ZsnV64zVOLCNt8v0XJPxTpIHAwPbjIKxfDadLS0kjUnFmazoajiEt1Ro_s1yRwWHosTzjsT6a8MUL9BtOUwzbngFDGUuF2zGWPC2XDeD799DGZQUaabSdMOc3GbMyNd7KA7KaUJky-3HzOHo6QeTtzRUem2cabTKBsaDBvQOzdTgr4fGYTwHr0_V5doABhxOFzKD_Th_Lkhkwch85ZMZlb3L4kJEJKguGMJw.L3UOm27i1OjDXydm7cNMzA.BLUAvupbJfIap-IiaHVM5r20kLYuU3Xf2t7kxEScnJr5iefa2noF-DRgvkl2oo0JzXmEoTJhK_lUKaueehDB_mcvjfZOk5GF80dOZSce4Kdg-kk0TCZaU9_Xm7sqbyELdjAThzVAOXEJNjgiyIB1h7PCqsI1Cza80wj5p5nVJMbO_YEHsI04Yc-UAtzgahFizJ0GEBqhRsAbV_qYegXPJqVKirZqxEzbQ6LNvR9I3I9cquEANQqYs_6GztCwUd6k-Rkcyi-6cFCu2qnXWnyjzHVV6-25Nw-lpBjcc--d07CKu67pIl0O41-O0Y9JmCGTsEN1c42Sff9EmTv4jrDwbXMP6-cmmpJ-2nvv2Az8wUgSfbN-AEfE7jq-THac9ZQ8v9IwOWuP41jfySyrQe7gGkj0NEllqRtlYzyRV3ZnMmScMK5yEqfWEThRn7qS-eEWOEz86mmPMQ6bNk-JsCMKt2OaLH0gGHfMA8oPWjHer0ELLNk9FHTOdyqyuOwrPRfKtddzwD-XVPW0sZAppl8Tj2tPqPTNf1jmajr5_srIaTVRHbLALfPoQgHqAv86RhpmLU4tgnnCHEMB9VVqZdTcamGJWJ8GL-2rZkXTHKCcLvh0otE6dUWay8sSVSxXf4WOJhnMJ7Zt0F207-DF1B0BJK2wRtIAucgZsN9N_pXw9wgBG-uF1hHULbUOMGnF57CNizAJKrElq9LWYJ1MaektDQHZC_NFpe7sl9qH-A0wKs4.nhzb3Lai7pTD8FhrcvpxVwAkD2g7fhXy-CPTjjr884s'
    }

    response = requests.request("GET", url, headers=headers, stream=True, verify=False)

    print("Статус ответа:", response.status_code)

    if response.status_code == 200:
        with open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
            return file_name
    else:
        print("Ошибка загрузки файла. Ответ от сервера:", response.text)
        return None


async def send_image(callback_or_message, image_path: str, caption: str = ""):
    try:
        image_file = InputFile(image_path)
        if isinstance(callback_or_message, CallbackQuery):
            await callback_or_message.message.answer_photo(
                photo=image_file,
                caption=caption,
                reply_markup=keyboards.after_text()
            )
        elif isinstance(callback_or_message, Message):
            await callback_or_message.answer_photo(
                photo=image_file,
                caption=caption,
                reply_markup=keyboards.after_text()
            )
        else:
            raise ValueError("Unsupported type for callback_or_message")
    except Exception as e:
        print(f"Ошибка при отправке изображения: {e}")
        if isinstance(callback_or_message, CallbackQuery):
            await callback_or_message.message.answer("Не удалось отправить изображение. Попробуйте снова.")
        elif isinstance(callback_or_message, Message):
            await callback_or_message.answer("Не удалось отправить изображение. Попробуйте снова.")
