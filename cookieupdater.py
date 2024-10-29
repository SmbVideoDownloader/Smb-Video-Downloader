import schedule
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

USERNAME = 'vmp65854@gmail.com'  # Your YouTube account email
PASSWORD = 'xEL8S#GyvgSt$'  # Your YouTube account password

# Path to save the cookies
COOKIE_FILE_PATH = '/var/www/v2mp4.com/cookies/cookies.txt'

def get_youtube_cookies():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service('/usr/bin/chromedriver')  # Replace with your ChromeDriver path

    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get('https://www.youtube.com/login')

        # Find the username and password fields and input credentials
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'identifierId'))
        )
        username_field.send_keys(USERNAME)
        driver.find_element(By.ID, 'identifierNext').click()

        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'password'))
        )
        password_field.send_keys(PASSWORD)
        driver.find_element(By.ID, 'passwordNext').click()

        # Wait for the YouTube homepage to load
        WebDriverWait(driver, 20).until(
            EC.url_contains('https://www.youtube.com/')
        )

        # Get the cookies and save them to a file
        cookies = driver.get_cookies()
        with open(COOKIE_FILE_PATH, 'w') as f:
            for cookie in cookies:
                f.write(f"{cookie['name']}={cookie['value']}\n")

        print(f"Cookies saved to {COOKIE_FILE_PATH}")

    finally:
        driver.quit()

def job():
    get_youtube_cookies()

# Schedule the job to run every 900 seconds
schedule.every(900).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)