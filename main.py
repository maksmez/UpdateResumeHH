import os
import pickle
import sys
import logging
import time

import requests
import yaml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, 'settings.yaml')
COOKIES_FILE = os.path.join(BASE_DIR, 'hh-cookies')

HH_LOGIN_URL = 'https://spb.hh.ru/applicant/resumes'
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}"


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=2000,2000")
    return webdriver.Chrome(options=options)


def load_config():
    if not os.path.exists(CONFIG_FILE):
        config = {
            'TELEGRAM_TOKEN': 'none',
            'CHAT_ID': 'none',
            'PSWRD': 'none',
            'EMAIL': 'none',
            'TIMEOUT': 30,
            'CAPTCHA_MAX_ATTEMPTS': 3
        }
        with open(CONFIG_FILE, 'w') as file:
            yaml.dump(config, file)
        logging.error(f"Файл {CONFIG_FILE} создан. Заполни поля и перезапусти скрипт.")
        sys.exit(0)

    with open(CONFIG_FILE) as file:
        config = yaml.safe_load(file)
        if config['PSWRD'] == 'none':
            logging.error("Error in config file! Please check and restart the program.")
            sys.exit(0)
        return config


def send_message_telegram(text, config):
    url = TELEGRAM_API_URL.format(token=config['TELEGRAM_TOKEN'], chat_id=config['CHAT_ID'],
                                  text=text.replace('#', '%23'))
    requests.get(url).json()


def send_photo_telegram(photo_path, config):
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendPhoto"
    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {"chat_id": config['CHAT_ID'], "caption": "Введите текст с капчи с пробелом"}
        response = requests.post(url, files=files, data=data)
    return response.json()


def wait_for_telegram_response(config):
    timeout = config['TIMEOUT']
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
    start_time = time.time()

    while True:
        try:
            response = requests.get(url, params={"timeout": 30}).json()

            if "result" in response and response["result"]:
                last_message = response["result"][-1]

                if last_message["message"]["date"] >= start_time:
                    return last_message["message"]["text"]

            if time.time() - start_time > timeout:
                raise TimeoutError("Время ожидания ввода капчи истекло")

            time.sleep(1)

        except Exception as e:
            raise


def handle_captcha(driver, config):
    count = 0
    max_attempts = config.get('CAPTCHA_MAX_ATTEMPTS', 3)
    while count < max_attempts:
        captcha_element = driver.find_element(By.CSS_SELECTOR, "img[data-qa=account-captcha-picture]")
        captcha_path = os.path.join(BASE_DIR, 'captcha.png')
        captcha_element.screenshot(captcha_path)

        send_photo_telegram(captcha_path, config)
        logging.info("Капча отправлена в Telegram. Ожидаю ответа")
        try:
            captcha_text = wait_for_telegram_response(config)
            logging.info(f"Получен текст капчи: {captcha_text}")

            driver.find_element(By.CSS_SELECTOR, 'input[data-qa="account-captcha-input"]').send_keys(captcha_text)
            driver.find_element(By.CSS_SELECTOR, 'button[data-qa="account-login-submit"]').click()
            time.sleep(5)

            if driver.find_elements(By.CSS_SELECTOR, "img[data-qa=account-captcha-picture]"):
                title = "Капча введена неверно!"
                send_message_telegram(title, config)
                logging.error(title)
                count += 1
                continue
            else:
                title = "Капча введена верно!"
                send_message_telegram(title, config)
                logging.info(title)
                break
        except Exception as e:
            raise
    if count > 3:
        raise Exception("Слишком много попыток ввода")


def login(driver, config):
    driver.find_element(By.CSS_SELECTOR, 'span[data-qa="expand-login-by-password-text"]').click()
    driver.find_element(By.CSS_SELECTOR, 'input[data-qa="login-input-username"]').send_keys(config['EMAIL'])
    time.sleep(3)
    driver.find_element(By.CSS_SELECTOR, 'input[data-qa="login-input-password"]').send_keys(config['PSWRD'])
    driver.find_element(By.CSS_SELECTOR, 'button[data-qa="account-login-submit"]').click()
    time.sleep(5)


def update_resumes(driver, config):
    resumes = driver.find_elements(By.CSS_SELECTOR, 'div[data-qa="resume"]')
    title = ''
    for resume in resumes:
        if not resume.text.__contains__('Поднимать автоматически'):
            driver.execute_script("arguments[0].scrollIntoView();", resume)
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(resume))
            button = resume.find_element(By.CSS_SELECTOR,
                                         'button[data-qa*="resume-update"]')
            driver.execute_script("arguments[0].click();", button)
            title += resume.text.split('\n')[0] + '\r\n' + 'Успешно обновлено \r\n'
        else:
            title += resume.text.split('\n')[0] + '\r\n' + resume.text.split('\n')[1] + '\r\n'
    logging.info(f'{title}')
    send_message_telegram(title, config)


def main():
    config = load_config()
    driver = setup_driver()

    try:
        driver.get(HH_LOGIN_URL)
        if os.path.exists(COOKIES_FILE):
            logging.info('Используем куки')
            for cookie in pickle.load(open(COOKIES_FILE, 'rb')):
                driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(5)

        if driver.find_elements(By.CSS_SELECTOR, 'span[data-qa="expand-login-by-password-text"]'):
            logging.info("Куки устарели, прохожу авторизацию")
            login(driver, config)
            if driver.find_elements(By.CSS_SELECTOR, "img[data-qa=account-captcha-picture]"):
                handle_captcha(driver, config)

        if driver.find_elements(By.CSS_SELECTOR, 'button[data-qa*="resume-update"]'):
            update_resumes(driver, config)
        else:
            title = 'Ошибка! Не найдено кнопки для поднятия резюме!'
            driver.save_screenshot('error.png')
            logging.error(title)
            send_message_telegram(title, config)

    except Exception as e:
        title = f'Ошибка!\r\n{e}'
        logging.error(title)
        send_message_telegram(title, config)
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
