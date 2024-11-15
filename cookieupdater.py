import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import pickle
import time

COOKIES_PATH = '/var/www/v2mp4.com/cookies'
COOKIE_TEMPLATE = os.path.join(COOKIES_PATH, 'cookies.txt{index}')

def get_new_cookies(index=0):
    # Setup Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run headless to avoid browser window
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Navigate to YouTube
        driver.get('https://accounts.google.com/')

        # Wait for login page to load
        time.sleep(3)

        # Perform login actions here
        email_field = driver.find_element(By.ID, 'identifierId')
        email_field.send_keys('vmp65854@gmail.com')  # Replace with your email
        email_field.send_keys(Keys.RETURN)

        time.sleep(3)  # Wait for password field
        password_field = driver.find_element(By.NAME, 'password')
        password_field.send_keys('xELS8S#GyvgSt$')  # Replace with your password
        password_field.send_keys(Keys.RETURN)

        # Wait for redirection to YouTube
        time.sleep(10)

        # Save cookies
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
    get_new_cookies(index=0)  # Generate the initial cookie file
