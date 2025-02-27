import os
import os
import pickle
import sys
import logging
from time import sleep
import requests
import yaml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Получаем абсолютный путь к директории, где находится скрипт
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Абсолютные пути к файлам
CONFIG_FILE = os.path.join(BASE_DIR, 'settings.yaml')
COOKIES_FILE = os.path.join(BASE_DIR, 'hh-cookies')

# Константы
HH_LOGIN_URL = 'https://spb.hh.ru/applicant/resumes'
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}"


# Настройка ChromeOptions
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
            'EMAIL': 'none'
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


def handle_captcha(driver, config):
    if driver.find_elements(By.CSS_SELECTOR, "img[data-qa=account-captcha-picture]"):
        title = 'Обнаружена капча!'
        logging.warning(title)
        send_message_telegram(title, config)
        driver.save_screenshot('captcha.png')
        # Закомментируй для ввода капчи
        sys.exit()
        logging.info("Снимок экрана сохранен - captcha.png")
        captcha_text = input('Enter captcha:\r\n')
        driver.find_element(By.CSS_SELECTOR, 'input[data-qa="account-captcha-input"]').send_keys(captcha_text)
        driver.find_element(By.CSS_SELECTOR, 'button[data-qa="account-login-submit"]').click()
        sleep(5)


def login(driver, config):
    driver.find_element(By.CSS_SELECTOR, 'span[data-qa="expand-login-by-password-text"]').click()
    driver.find_element(By.CSS_SELECTOR, 'input[data-qa="login-input-username"]').send_keys(config['EMAIL'])
    sleep(3)
    driver.find_element(By.CSS_SELECTOR, 'input[data-qa="login-input-password"]').send_keys(config['PSWRD'])
    driver.find_element(By.CSS_SELECTOR, 'button[data-qa="account-login-submit"]').click()
    sleep(5)


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
        sleep(5)

        if driver.find_elements(By.CSS_SELECTOR, 'span[data-qa="expand-login-by-password-text"]'):
            logging.info("Куки устарели, прохожу авторизацию")
            login(driver, config)
            handle_captcha(driver, config)

        if driver.find_elements(By.CSS_SELECTOR, 'button[data-qa*="resume-update"]'):
            update_resumes(driver, config)
        else:
            title = 'Ошибка! Не найдено кнопки для поднятия резюме!'
            driver.save_screenshot('error.png')
            logging.error(title)
            send_message_telegram(title, config)

    except Exception as e:
        title = f'Ошибка!:\r\n{e}'
        logging.error(title)
        send_message_telegram(title, config)
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
