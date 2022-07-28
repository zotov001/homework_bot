import logging
import os
import time

import telegram
import requests


from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

CHECK_TG_TOKEN = os.getenv('CTG_TOKEN')
# при вставке токена непосредственно в ссылку остаюся ''


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception('Бот не смог отправить сообщение'):
        logger.error('Ошибка отправки в Telegram')


def get_api_answer(current_timestamp):
    """Получает ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise Exception('Ошибка при запросе к основному API')
        logger.error('Ошибка при запросе к основному API')
    return response.json()


def check_response(response):
    """Проверка ответа на корректность."""
    if type(response['homeworks']) != list:
        raise Exception('API-сервис выдал другой тип данных')
        logger.error('Ошибка типа при запросе к основному API')
    if type(response) != dict:
        raise Exception('API-сервис выдал другой тип данных')
        logger.error('Ошибка типа при запросе к основному API')
    return response.get('homeworks')


def parse_status(homework):
    """Проверка статуса ДЗ."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        raise ValueError('Ошибка в получении статуса ДЗ')
        logger.error('Ошибка в получении статуса ДЗ')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия/валидности токенов."""
    tg_status = requests.get(CHECK_TG_TOKEN)
    if tg_status.json().get('ok'):
        if PRACTICUM_TOKEN is not None:
            if TELEGRAM_CHAT_ID is not None:
                return True
    else:
        logger.critical('Ошибка, отсутствует токен')
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while check_tokens():
        response_0 = get_api_answer(current_timestamp)
        homeworks_0 = check_response(response_0)
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks != homeworks_0:
                status = parse_status(homeworks[0])
                send_message(bot, status)
                logger.info(f'Сообщение отправлено {status}')
                homeworks_0 = homeworks
            else:
                logger.debug('Нет новых статусов')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(f'Сбой в работе программы: {error}')
            send_message(bot, message)
            time.sleep(RETRY_TIME)
    else:
        message = 'Практикум-Домашка или Токен бота недоступен'
        logger.error(f'Ошибка: {message}')
        send_message(bot, message)


if __name__ == '__main__':
    main()
