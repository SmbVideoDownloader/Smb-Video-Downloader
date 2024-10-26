import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

COOKIES_PATH = '/var/www/v2mp4.com/cookies/cookies.txt'
USERNAME = 'vmp65854@gmail.com'  # Your YouTube account email
PASSWORD = 'xEL8S#GyvgSt$'  # Your YouTube account password

def extract_cookies():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode for automation
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # Navigate directly to YouTube
        driver.get("https://www.youtube.com")

        # Initiate sign-in process if not logged in
        sign_in_button = driver.find_element("xpath", "//button[contains(text(), 'Sign in')]")
        sign_in_button.click()
        
        # Wait for the Google sign-in page to load
        time.sleep(2)

        # Enter the email and navigate to the password step
        email_field = driver.find_element("name", "identifier")
        email_field.send_keys(USERNAME)
        driver.find_element("id", "identifierNext").click()

        time.sleep(2)  # Wait for the password field to load

        password_field = driver.find_element("name", "password")
        password_field.send_keys(PASSWORD)
        driver.find_element("id", "passwordNext").click()

        # Wait for login to complete and redirect to YouTube
        time.sleep(5)

        # Extract cookies after login
        cookies = driver.get_cookies()
        with open(COOKIES_PATH, 'w') as f:
            json.dump(cookies, f)

        print(f"Cookies extracted and saved to {COOKIES_PATH}")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    extract_cookies()
