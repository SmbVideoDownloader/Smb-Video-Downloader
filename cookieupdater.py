import os
import time
import pickle
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
            # Set up Chrome driver with necessary options
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            wait = WebDriverWait(driver, 10)

            # Open YouTube login page
            driver.get("https://accounts.google.com/signin/v2/identifier")

            # Input email
            email_field = wait.until(EC.presence_of_element_located((By.ID, "identifierId")))
            email_field.send_keys(USERNAME)
            driver.find_element(By.ID, "identifierNext").click()

            # Input password (wait until password field is present)
            password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_field.send_keys(PASSWORD)
            driver.find_element(By.ID, "passwordNext").click()

            # Wait for login to complete by checking a post-login element
            time.sleep(5)  # Ensure login session is created

            # Save cookies
            cookie_path = os.path.join(COOKIE_DIR, f"cookies_{i}.pkl")
            with open(cookie_path, "wb") as f:
                pickle.dump(driver.get_cookies(), f)
            print(f"Saved cookies to {cookie_path}")

        except Exception as e:
            print(f"Error during login for cookie file {i}: {e}")

        finally:
            if driver:
                driver.quit()
            time.sleep(2)  # Small delay to avoid rapid requests

generate_cookie_files()
