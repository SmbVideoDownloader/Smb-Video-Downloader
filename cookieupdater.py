import os
import time
import pickle
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Credentials
USERNAME = 'vmp65854@gmail.com'
PASSWORD = 'xEL8S#GyvgSt$'

# Directory for cookie storage
COOKIE_DIR = '/var/www/v2mp4.com/cookies/'
os.makedirs(COOKIE_DIR, exist_ok=True)

def generate_cookie_files(n=500):
    for i in range(n):
        driver = None
        try:
            # Set up Chrome driver with additional options
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--remote-debugging-port=9222")
            options.add_argument("--headless")  # Run in headless mode
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")
            options.add_argument("--enable-logging")
            options.add_argument("--v=1")
            options.add_argument("--log-path=/tmp/chrome_debug.log")

            # Initialize ChromeDriver
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            wait = WebDriverWait(driver, 40)  # Increased wait time

            # Open YouTube login page
            driver.get("https://accounts.google.com/signin/v2/identifier")

            # Input email and proceed
            email_field = wait.until(EC.presence_of_element_located((By.ID, "identifierId")))
            email_field.send_keys(USERNAME)
            driver.find_element(By.ID, "identifierNext").click()

            # Wait for password field to become available
            try:
                password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
                password_field.send_keys(PASSWORD)
                driver.find_element(By.ID, "passwordNext").click()
            except Exception as e:
                driver.save_screenshot(f"/tmp/error_screenshot_{i}.png")  # Take a screenshot for debugging
                print(f"Error finding password field for cookie file {i}: {e}")
                continue  # Skip to the next iteration if password field is not found

            # Wait for successful login, then save cookies
            time.sleep(10)  # Increase wait time
            cookie_path = os.path.join(COOKIE_DIR, f"cookies_{i}.pkl")
            with open(cookie_path, "wb") as f:
                pickle.dump(driver.get_cookies(), f)
            print(f"Saved cookies to {cookie_path}")

        except Exception as e:
            print(f"Error during login for cookie file {i}: {e}")
            traceback.print_exc()  # Print the full error stack

        finally:
            if driver:
                driver.quit()
            time.sleep(2)  # Small delay to avoid rapid requests

generate_cookie_files()
