from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from config_data.config import Config, load_config

config: Config = load_config()

default_message = ('Ты — бот-генератор текстов. Отвечай сразу без вводных фраз и системных сообщений. При генерации ты '
                   'должен отправить только текст без лишних комментариев".')

prompts_text = {
    '1': 'Объясни, как работает квантовая запутанность простыми словами.',
    '2': 'Расскажи о самых значимых событиях Второй мировой войны.',
    '3': 'Какие основные отличия между Python и Java?',
    '4': 'Какое место вы мечтаете посетить и почему?',
    '5': 'Что такое счастье с философской точки зрения?',
    '6': 'Придумай креативный сценарий для рекламы мобильного приложения.',
    '7': ' Есть ли какие-то научные открытия, которые вас вдохновляют?',
    '8': 'Посоветуй несколько книг по психологии для начинающих.',
    '9': 'Составь план учебы по программированию для начинающих.',
    '10': 'Напиши 5 необычных идей для празднования Нового года.'
}


gigachat = GigaChat(
    credentials=config.gigachat_token,
    scope="GIGACHAT_API_PERS",
    model="GigaChat",
    verify_ssl_certs=False
)
print("gigachat is started")


def create_random_text(user_query: str = '1', is_query=False):
    def check_user_query(user_query):
        if is_query:
            return user_query
        else:
            return prompts_text[user_query]

    prompt = default_message + check_user_query(user_query)
    response = gigachat.chat(prompt)
    return response.choices[0].message.content


def create_image_from_query(user_query: str):
    # Добавляем точный запрос для генерации изображения, чтобы система знала, что нужно создать изображение
    prompt = default_message + user_query

    # Формируем запрос для создания изображения
    payload = Chat(
        messages=[Messages(role=MessagesRole.USER, content=user_query)],
        temperature=0.7,
        max_tokens=100,
        function_call="auto",  # Указываем, что нужно автоматически определить необходимость вызова text2image
    )

    try:
        # Отправляем запрос на генерацию изображения
        response = gigachat.chat(payload)

        # Логирование ответа для отладки
        print("Response from Gigachat:", response)

        # Проверяем, если ответ содержит ссылку на изображение
        if "img src" in response.choices[0].message.content:
            image_id = response.choices[0].message.content.split('"')[1]
            return image_id
        else:
            return "Извините, я не смог создать изображение. Возможно, запрос был некорректным."

    except IndexError:
        # Ловим ошибку в случае, если response.choices пусто или не имеет ожидаемой структуры
        print("Error: Unexpected response structure", response)
        return "Произошла ошибка при обработке запроса изображения. Пожалуйста, попробуйте снова."
    except Exception as e:
        # Общая обработка других ошибок
        print("Unexpected error:", e)
        return "Произошла непредвиденная ошибка при генерации изображения. Попробуйте позже."
