import os
import pickle
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Path to store cookies
COOKIES_PATH = '/var/www/v2mp4.com/cookies'
COOKIE_TEMPLATE = os.path.join(COOKIES_PATH, 'cookies{index}.txt')

def get_new_cookies(index=0):
    # Setup Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # Open browser in maximized mode
    chrome_options.add_argument("--disable-infobars")  # Disabling infobars
    chrome_options.add_argument("--disable-extensions")  # Disabling extensions
    chrome_options.add_argument("--disable-gpu")  # Applicable to Windows OS only
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.binary_location = "/usr/bin/google-chrome"  # Update with correct binary path

    # Initialize WebDriver
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Navigate to Google Accounts
        driver.get("https://accounts.google.com/")

        # Wait for login page to load and interact with email field
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "identifierId"))
        )
        email_field.send_keys("vmp65854@gmail.com")  # Replace with your email
        email_field.send_keys(Keys.RETURN)

        # Wait for password field to load
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        password_field.send_keys("xELS8S#GyvgSt$")  # Replace with your password
        password_field.send_keys(Keys.RETURN)

        # Wait for redirection or a specific element to indicate successful login
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))  # Adjust selector if needed
        )

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
