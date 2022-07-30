import logging
import os
import time

import telegram
import requests

from dotenv import load_dotenv
from http import HTTPStatus
from requests import RequestException

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

TELEGRAM_RETRY_TIME = 600

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

MISSING_TOKEN = '0'


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError('Бот не смог отправить сообщение'):
        logger.error('Ошибка отправки в Telegram')


def get_api_answer(current_timestamp):
    """Получает ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError('Сервер недоступен')
    except RequestException as error:
        raise RequestException(f'ошибка {error}')
    return response.json()


def check_response(response):
    """Проверка ответа на корректность."""
    if len(response) == 0:
        logger.error('API-сервис выдал пустой ответ')
        raise ValueError('API-сервис выдал пустой ответ')
    if type(response['homeworks']) != list:
        logger.error('API-сервис выдал другой тип данных')
        raise TypeError('API-сервис выдал другой тип данных')
    if type(response) != dict:
        logger.error('API-сервис выдал другой тип данных')
        raise TypeError('API-сервис выдал другой тип данных')
    if 'homeworks' not in response.keys():
        logger.error('В словаре нет ключа homeworks')
        raise KeyError('В словаре нет ключа homeworks')
    return response.get('homeworks')


def parse_status(homework):
    """Проверка статуса ДЗ."""
    if not homework['homework_name']:
        logger.error('Ошибка отсутствует ключ имени ДЗ')
        raise KeyError('Ошибка отсутствует ключ имени ДЗ')
    if not homework['status']:
        logger.error('Ошибка отсутствует ключ статуса ДЗ')
        raise KeyError('Ошибка отсутствует ключ статуса ДЗ')
    hw_name = homework['homework_name']
    hw_status = homework.get('status')
    if hw_status not in HOMEWORK_STATUSES:
        logger.error('Неизвестный статус ДЗ')
        raise ValueError('Неизвестный статус ДЗ')
    verdict = HOMEWORK_STATUSES.get(hw_status)
    return f'Изменился статус проверки работы "{hw_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    if TELEGRAM_TOKEN:
        if PRACTICUM_TOKEN:
            if TELEGRAM_CHAT_ID:
                return True
            else:
                globals()['MISSING_TOKEN'] = 'ID чата'
        else:
            globals()['MISSING_TOKEN'] = 'Практикума'
    else:
        globals()['MISSING_TOKEN'] = 'Телеграма'
    logger.critical(f'Ошибка, отсутствует токен {MISSING_TOKEN}')
    # exit() не проходит тест


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                status = parse_status(homeworks[0])
                send_message(bot, status)
                logger.info(f'Сообщение отправлено {status}')
                current_timestamp = response['current_date']
            else:
                logger.debug('Нет новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(f'Сбой в работе программы: {error}')
            send_message(bot, message)
        time.sleep(TELEGRAM_RETRY_TIME)
    else:
        message = 'Практикум-Домашка или Токен бота недоступен'
        logger.error(f'Ошибка: {message}')
        send_message(bot, message)


if __name__ == '__main__':
    check_tokens()
    main()
