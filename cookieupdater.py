import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Credentials (use a secure method to handle sensitive info in production)
USERNAME = 'vmp65854@gmail.com'
PASSWORD = 'xEL8S#GyvgSt$'

# Directory for cookie storage
COOKIE_DIR = '/var/www/v2mp4.com/cookies/'
os.makedirs(COOKIE_DIR, exist_ok=True)

def generate_cookie_files(n=500):
    for i in range(n):
        try:
            # Set up Chrome driver
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")  # Run in headless mode
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            # Open YouTube login page
            driver.get("https://accounts.google.com/signin/v2/identifier")
            time.sleep(2)

            # Input email
            driver.find_element(By.ID, "identifierId").send_keys(USERNAME)
            driver.find_element(By.ID, "identifierNext").click()
            time.sleep(2)

            # Input password
            driver.find_element(By.NAME, "password").send_keys(PASSWORD)
            driver.find_element(By.ID, "passwordNext").click()
            time.sleep(5)  # Wait for login to complete

            # Save cookies
            cookie_path = os.path.join(COOKIE_DIR, f"cookies_{i}.pkl")
            with open(cookie_path, "wb") as f:
                pickle.dump(driver.get_cookies(), f)
            print(f"Saved cookies to {cookie_path}")

        except Exception as e:
            print(f"Error during login for cookie file {i}: {e}")
        
        finally:
            driver.quit()
            time.sleep(2)  # Small delay to avoid rapid requests

generate_cookie_files()
