import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import pickle
import time

# Path to store cookies
COOKIES_PATH = '/var/www/v2mp4.com/cookies'
COOKIE_TEMPLATE = os.path.join(COOKIES_PATH, 'cookies{index}.txt')

def get_new_cookies(index=0):
    chrome_options = Options()
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("--headless=new")  # Headless mode
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/google-chrome"  # Adjust if necessary

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get('https://accounts.google.com/')
        time.sleep(3)

        # Perform login actions
        email_field = driver.find_element(By.ID, 'identifierId')
        email_field.send_keys('vmp65854@gmail.com')
        email_field.send_keys(Keys.RETURN)

        time.sleep(3)
        password_field = driver.find_element(By.NAME, 'password')
        password_field.send_keys('xELS8S#GyvgSt$')
        password_field.send_keys(Keys.RETURN)

        time.sleep(10)
        cookies = driver.get_cookies()
        cookie_path = COOKIE_TEMPLATE.format(index=index)
        with open(cookie_path, 'wb') as cookie_file:
            pickle.dump(cookies, cookie_file)
        print(f"Cookies saved to {cookie_path}")
    except Exception as e:
        print(f"Error extracting cookies: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    # Generate the initial cookie file
    get_new_cookies(index=0)
