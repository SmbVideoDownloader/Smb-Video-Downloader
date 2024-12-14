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
    # Configure Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument("start-maximized")  # Open browser in maximized mode
    chrome_options.add_argument("disable-infobars")  # Disable infobars
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-gpu")  # Applicable to Windows OS only
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model

    # Initialize the WebDriver
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Navigate to Google sign-in page
        driver.get('https://accounts.google.com/')

        # Wait for the login page to load
        time.sleep(3)

        # Perform login actions
        email_field = driver.find_element(By.ID, 'identifierId')
        email_field.send_keys('vmp65854@gmail.com')  # Replace with your email
        email_field.send_keys(Keys.RETURN)

        time.sleep(3)  # Wait for password field to load

        password_field = driver.find_element(By.NAME, 'password')
        password_field.send_keys('xELS8S#GyvgSt$')  # Replace with your password
        password_field.send_keys(Keys.RETURN)

        # Wait for redirection after login
        time.sleep(10)

        # Save cookies to a file
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
