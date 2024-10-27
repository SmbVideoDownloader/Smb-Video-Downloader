import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Hardcoded credentials (be cautious with this for security reasons)
USERNAME = 'vmp65854@gmail.com'
PASSWORD = 'xEL8S#GyvgSt$'

# Path where cookies will be stored
COOKIES_PATH = '/var/www/v2mp4.com/cookies/cookies.txt'

def get_youtube_cookies():
    """Open a virtual Chrome browser, log into YouTube, and save cookies to file."""
    
    # Setup Chrome options to run in headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Initialize Chrome WebDriver with specified options
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Navigate to YouTube's login page
        driver.get("https://accounts.google.com/ServiceLogin?service=youtube")

        # Input email
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "identifierId"))).send_keys(USERNAME)
        driver.find_element(By.ID, "identifierNext").click()

        # Input password
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(PASSWORD)
        driver.find_element(By.ID, "passwordNext").click()

        # Wait until redirected to YouTube homepage
        WebDriverWait(driver, 20).until(EC.url_contains("youtube.com"))

        # Fetch cookies from the YouTube session
        cookies = driver.get_cookies()

        # Write cookies in Netscape format (compatible with yt-dlp)
        with open(COOKIES_PATH, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for cookie in cookies:
                f.write(f"{cookie['domain']}\t"
                        f"{str(cookie.get('hostOnly', 'FALSE')).upper()}\t"
                        f"{cookie['path']}\t"
                        f"{str(cookie.get('secure', 'FALSE')).upper()}\t"
                        f"{cookie.get('expiry', '0')}\t"
                        f"{cookie['name']}\t"
                        f"{cookie['value']}\n")

        print(f"Cookies updated successfully at {COOKIES_PATH}")

    except Exception as e:
        print(f"Error updating cookies: {e}")

    finally:
        # Close the browser instance to release resources
        driver.quit()

def main():
    """Run the YouTube cookie updater in a continuous loop every 15 minutes."""
    while True:
        print("Updating YouTube cookies...")
        get_youtube_cookies()
        
        # Wait for 15 minutes (900 seconds) before refreshing cookies again
        time.sleep(900)

if __name__ == "__main__":
    main()
