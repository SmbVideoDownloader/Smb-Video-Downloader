import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
from selenium_stealth import stealth

# Path to save the cookies file
COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'

# Account credentials (use a dummy account)
YOUTUBE_EMAIL = "vmp65854@gmail.com"
YOUTUBE_PASSWORD = "xEL8S#GyvgSt$"

def create_browser():
    # Automatically installs the matching chromedriver version
    chromedriver_autoinstaller.install()

    options = Options()
    options.headless = True  # Runs Chrome in headless mode.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    browser = webdriver.Chrome(options=options)
    
    # Set up stealth mode to reduce bot detection
    stealth(browser,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )
    
    return browser

def login_and_get_cookies(browser):
    # Navigate to YouTube's login page
    browser.get("https://accounts.google.com/signin")

    # Enter email and go to next
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "identifierId"))
    ).send_keys(YOUTUBE_EMAIL)
    browser.find_element(By.ID, "identifierNext").click()

    # Enter password and go to next
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.NAME, "password"))
    ).send_keys(YOUTUBE_PASSWORD)
    browser.find_element(By.ID, "passwordNext").click()

    # Wait until logged in and redirected to YouTube
    WebDriverWait(browser, 15).until(
        EC.url_contains("https://www.youtube.com")
    )

    # Collect cookies from YouTube
    cookies = browser.get_cookies()
    return cookies

def save_cookies_for_yt_dlp(cookies):
    # Convert cookies to Netscape format for yt-dlp
    with open(COOKIES_FILE, 'w') as file:
        for cookie in cookies:
            file.write(f"{cookie['domain']}\tTRUE\t{cookie['path']}\t{str(cookie['secure']).upper()}\t{cookie.get('expiry', '0')}\t{cookie['name']}\t{cookie['value']}\n")
    print(f"Cookies saved to {COOKIES_FILE}")

def main():
    while True:
        browser = create_browser()
        
        try:
            # Log in and retrieve cookies
            cookies = login_and_get_cookies(browser)
            
            # Save cookies in yt-dlp format
            save_cookies_for_yt_dlp(cookies)
            
        except Exception as e:
            print(f"An error occurred: {e}")
        
        finally:
            browser.quit()

        # Wait 15 minutes before refreshing cookies
        time.sleep(900)

if __name__ == "__main__":
    main()
