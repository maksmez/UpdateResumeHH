# UpdateResumeHH

Проект для автоматического поднятия резюме на hh.ru с уведомлениями через Telegram-бота

## Возможности

- Автоматическое обновление резюме на hh.ru
- Обход капчи через Telegram (бот присылает капчу, вы вводите ответ)
- Уведомления о результатах в Telegram
- Поддержка нескольких резюме
- Сохранение сессии через cookies

## Технологии

- Python 3.10+
- Selenium 4.29.0 (для автоматизации браузера)
- PyYAML 6.0.2 (для работы с конфигом)
- Requests 2.32.3 (для Telegram API)
- ChromeDriver (для работы Selenium)

## Установка

1. Клонируйте репозиторий:
    ```
    git clone https://github.com/maksmez/UpdateResumeHH.git
    cd UpdateResumeHH
    ```

2. Установите зависимости:
    ```
    pip install -r req.txt
    ```
## Настройка

Создайте бота через @BotFather и получите токен

Создайте файл settings.yaml:
```
TELEGRAM_TOKEN: "ваш_токен_бота"
CHAT_ID: "ваш_chat_id"  # Узнать можно через @userinfobot
EMAIL: "ваш@email.hh"
PSWRD: "ваш_пароль"
TIMEOUT: 30  # Таймаут ожидания капчи (сек)
CAPTCHA_MAX_ATTEMPTS: Количество попыток ввода капчи 
```
Запуск
```
python main.py
```
