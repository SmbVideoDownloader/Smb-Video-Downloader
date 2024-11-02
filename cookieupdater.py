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
            # Set up Chrome driver with logging and interactive mode
            options = webdriver.ChromeOptions()
            # Remove headless mode for interactive debugging
            # Comment out "--headless" for visual debugging
            # options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--start-maximized")
            
            # Initialize ChromeDriver with extra logging
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            wait = WebDriverWait(driver, 20)  # Extend wait time

            # Open YouTube login page
            driver.get("https://accounts.google.com/signin/v2/identifier")

            # Input email and proceed
            email_field = wait.until(EC.presence_of_element_located((By.ID, "identifierId")))
            email_field.send_keys(USERNAME)
            driver.find_element(By.ID, "identifierNext").click()

            # Wait for password field, then input password
            password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_field.send_keys(PASSWORD)
            driver.find_element(By.ID, "passwordNext").click()

            # Wait for successful login check (e.g., user's account icon or other post-login element)
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
