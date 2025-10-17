#!/usr/bin/env uv run
# main.py
import argparse
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests


def main():
    """
    Determine brand to get the refresh token for
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", help="Brand of vehicle (Hyundai/Kia)", type=str.lower, required=True, choices=['hyundai','kia'])
    args = parser.parse_args()

    """
    Populate global variables
    """
    BASE_URL = f"https://idpconnect-eu.{args.brand}.com/auth/api/v2/user/oauth2/"
    TOKEN_URL = f"{BASE_URL}token"

    if args.brand == 'kia':
        # Kia specific variables here
        CLIENT_ID = "fdc85c00-0a2f-4c64-bcb4-2cfb1500730a"
        CLIENT_SECRET = "secret"
        REDIRECT_URL_FINAL = "https://prd.eu-ccapi.kia.com:8080/api/v1/user/oauth2/redirect"
        SUCCESS_ELEMENT_SELECTOR = "a[class='logout user']" 
        LOGIN_URL = f"{BASE_URL}authorize?ui_locales=de&scope=openid%20profile%20email%20phone&response_type=code&client_id=peukiaidm-online-sales&redirect_uri=https://www.kia.com/api/bin/oneid/login&state=aHR0cHM6Ly93d3cua2lhLmNvbTo0NDMvZGUvP21zb2NraWQ9MjM1NDU0ODBmNmUyNjg5NDIwMmU0MDBjZjc2OTY5NWQmX3RtPTE3NTYzMTg3MjY1OTImX3RtPTE3NTYzMjQyMTcxMjY=_default" 
    elif args.brand == 'hyundai':
        # Hyundai specific variables
        CLIENT_ID = "6d477c38-3ca4-4cf3-9557-2a1929a94654"
        CLIENT_SECRET = "KUy49XxPzLpLuoK0xhBC77W6VXhmtQR9iQhmIFjjoY4IpxsV"
        REDIRECT_URL_FINAL = "https://prd.eu-ccapi.hyundai.com:8080/api/v1/user/oauth2/token"
        SUCCESS_ELEMENT_SELECTOR = "button.mail_check" 
        LOGIN_URL = f"{BASE_URL}authorize?client_id=peuhyundaiidm-ctb&redirect_uri=https%3A%2F%2Fctbapi.hyundai-europe.com%2Fapi%2Fauth&nonce=&state=PL_&scope=openid+profile+email+phone&response_type=code&connector_client_id=peuhyundaiidm-ctb&connector_scope=&connector_session_key=&country=&captcha=1&ui_locales=en-US" 

    REDIRECT_URL = f"{BASE_URL}authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URL_FINAL}&lang=de&state=ccsp"

    """
    Main function to run the Selenium automation.
    """
    # Initialize the Chrome WebDriver
    # Make sure you have chromedriver installed and in your PATH,
    # or specify the path to it.
    options = webdriver.ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Linux; Android 4.1.1; Galaxy Nexus Build/JRO03C) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Mobile Safari/535.19_CCS_APP_AOS")
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    # 1. Open the login page
    print(f"Opening login page: {LOGIN_URL}")
    driver.get(LOGIN_URL)

    print("\n" + "="*50)
    print("Please log in manually in the browser window.")
    print("The script will wait for you to complete the login...")
    print("="*50 + "\n")

    try:
        wait = WebDriverWait(driver, 300) # 300-second timeout
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SUCCESS_ELEMENT_SELECTOR)))
        print("✅ Login successful! Element found.")
        driver.get(REDIRECT_URL)
        wait = WebDriverWait(driver, 15) # 15-second timeout
        current_url = driver.current_url
        print(current_url)
        code = re.search(
                r'code=([0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36})',
                current_url
            ).group(1)
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URL_FINAL,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
        session = requests.Session()
        response = session.post(TOKEN_URL, data=data)
        if response.status_code == 200:
            tokens = response.json()
            if tokens is not None:
                refresh_token = tokens["refresh_token"]
                access_token = tokens["access_token"]
                print(f"\n✅ Your tokens are:\n\n- Refresh Token: {refresh_token}\n- Access Token: {access_token}")
        else:
            print(f"\n❌ Error getting tokens from der API!\n{response.text}")

    except TimeoutException:
        print("❌ Timed out after 5 minutes. Login was not completed or the success element was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Cleaning up and closing the browser.")
        driver.quit()        

if __name__ == "__main__":
    main()
