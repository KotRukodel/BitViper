import requests
from config import TELEGRAM_CHANEL, TELEGRAM_BOT_TOKEN


def bot_send_message(text):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {
        'chat_id': TELEGRAM_CHANEL,
        'text': text
    }
    return requests.post(url, data=data)


