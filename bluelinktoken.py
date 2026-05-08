#!/usr/bin/env python3

# bluelinktoken.py
#
# Retrieve the refresh token for a Hyundai/Kia car.
#
# Supports two modes:
#   --mode headless  (default) — pure HTTP, no browser needed (EU only)
#   --mode browser              — Selenium-based, manual login in browser
#
# The headless mode was developed by reverse engineering the Kia Connect
# App (v2.1.27). It uses curl_cffi to impersonate an Android Chrome TLS
# fingerprint and performs the OAuth flow via direct HTTP requests.
#
# Original browser-based authors:
# Kia: fuatakgun (https://gist.github.com/fuatakgun/fa4ef1e1d48b8dca2d22133d4d028dc9)
# Hyundai: Maaxion (https://gist.github.com/Maaxion/22a38ba8fb06937da18482ddf35171ac)
#

import argparse
import base64
import re
import sys
import time
from urllib.parse import urlparse, parse_qs

BRANDS = {
    "kia": {
        "host": "https://idpconnect-eu.kia.com",
        "client_id": "fdc85c00-0a2f-4c64-bcb4-2cfb1500730a",
        "client_secret": "secret",
        "redirect_uri": "https://prd.eu-ccapi.kia.com:8080/api/v1/user/oauth2/redirect",
        "login_url": (
            "https://idpconnect-eu.kia.com/auth/api/v2/user/oauth2/authorize"
            "?ui_locales=de&scope=openid%20profile%20email%20phone&response_type=code"
            "&client_id=peukiaidm-online-sales"
            "&redirect_uri=https://www.kia.com/api/bin/oneid/login"
            "&state=aHR0cHM6Ly93d3cua2lhLmNvbTo0NDMvZGUv_default"
        ),
        "success_selector": "a[class='logout user']",
    },
    "hyundai": {
        "host": "https://idpconnect-eu.hyundai.com",
        "client_id": "6d477c38-3ca4-4cf3-9557-2a1929a94654",
        "client_secret": "KUy49XxPzLpLuoK0xhBC77W6VXhmtQR9iQhmIFjjoY4IpxsV",
        "redirect_uri": "https://prd.eu-ccapi.hyundai.com:8080/api/v1/user/oauth2/token",
        "login_url": (
            "https://idpconnect-eu.hyundai.com/auth/api/v2/user/oauth2/authorize"
            "?client_id=peuhyundaiidm-ctb"
            "&redirect_uri=https%3A%2F%2Fctbapi.hyundai-europe.com%2Fapi%2Fauth"
            "&nonce=&state=DE_&scope=openid+profile+email+phone&response_type=code"
            "&connector_client_id=peuhyundaiidm-ctb&connector_scope="
            "&connector_session_key=&country=&captcha=1&ui_locales=en-US"
        ),
        "success_selector": "button.mail_check",
    },
}

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 4.1.1; Galaxy Nexus Build/JRO03C) "
    "AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 "
    "Mobile Safari/535.19_CCS_APP_AOS"
)


# ── Headless Login ────────────────────────────────────────

def headless_login(brand_key, username, password):
    """
    Headless login using curl_cffi (Android TLS fingerprint).
    No browser needed. Works for EU Kia and EU Hyundai.

    Flow:
      1. GET authorize page (get session cookies)
      2. GET /auth/api/v1/accounts/certs (RSA public key)
      3. POST /auth/account/signin with app client_id + encrypted password
         → 302 redirect with code directly
      4. POST token exchange → refresh + access token
    """
    try:
        from curl_cffi import requests as curl_requests
        from Crypto.PublicKey import RSA
        from Crypto.Cipher import PKCS1_v1_5
    except ImportError:
        print("❌ Headless mode requires: pip install curl_cffi pycryptodome")
        sys.exit(1)

    cfg = BRANDS[brand_key]
    host = cfg["host"]
    client_id = cfg["client_id"]
    redirect_uri = cfg["redirect_uri"]

    s = curl_requests.Session(impersonate="chrome131_android")
    s.headers.update({"User-Agent": USER_AGENT})

    # Step 1: Load authorize page to get session cookies
    print(f"[1/4] Loading authorize page...")
    auth_url = (f"{host}/auth/api/v2/user/oauth2/authorize"
                f"?response_type=code&client_id={client_id}"
                f"&redirect_uri={redirect_uri}&lang=de&state=ccsp&country=de")
    s.get(auth_url, allow_redirects=True)
    print(f"  ✅ Session established")

    # Step 2: Get RSA public key
    print(f"[2/4] Fetching RSA public key...")
    resp = s.get(f"{host}/auth/api/v1/accounts/certs")
    if resp.status_code != 200:
        print(f"  ❌ Certs endpoint returned {resp.status_code}")
        sys.exit(1)
    jwk = resp.json().get("retValue", {})
    kid = jwk.get("kid", "")

    # Convert JWK to RSA key and encrypt password
    n = int.from_bytes(base64.urlsafe_b64decode(jwk["n"] + "=="), "big")
    e = int.from_bytes(base64.urlsafe_b64decode(jwk["e"] + "=="), "big")
    key = RSA.construct((n, e))
    encrypted_pw = PKCS1_v1_5.new(key).encrypt(password.encode("utf-8")).hex()
    print(f"  ✅ Password encrypted")

    # Step 3: POST signin with app client_id
    print(f"[3/4] Signing in...")
    resp = s.post(f"{host}/auth/account/signin", data={
        "client_id": client_id,
        "encryptedPassword": "true",
        "password": encrypted_pw,
        "redirect_uri": redirect_uri,
        "scope": "",
        "nonce": "",
        "state": "ccsp",
        "username": username,
        "connector_session_key": "",
        "kid": kid,
        "_csrf": "",
    }, allow_redirects=False)

    if resp.status_code != 302:
        print(f"  ❌ Signin returned HTTP {resp.status_code}")
        print(f"     {resp.text[:300]}")
        sys.exit(1)

    location = resp.headers.get("location", "")
    code_list = parse_qs(urlparse(location).query).get("code")
    if not code_list:
        print(f"  ❌ No code in redirect: {location[:200]}")
        sys.exit(1)

    code = code_list[0]
    print(f"  ✅ Authorization code received")

    # Step 4: Token exchange
    print(f"[4/4] Exchanging code for tokens...")
    token_url = f"{host}/auth/api/v2/user/oauth2/token"
    resp = curl_requests.post(token_url, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": cfg["client_secret"],
    })

    if resp.status_code != 200:
        print(f"  ❌ Token exchange failed: HTTP {resp.status_code}")
        print(f"     {resp.text[:300]}")
        sys.exit(1)

    tokens = resp.json()
    print(f"\n✅ Your tokens are:\n")
    print(f"- Refresh Token: {tokens.get('refresh_token', 'N/A')}")
    print(f"- Access Token: {tokens.get('access_token', 'N/A')}")


# ── Browser Login (Selenium) ─────────────────────────────

def browser_login(brand_key):
    """Original Selenium-based login. Opens a browser for manual login."""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    import requests

    cfg = BRANDS[brand_key]
    client_id = cfg["client_id"]
    redirect_uri = cfg["redirect_uri"]
    host = cfg["host"]
    token_url = f"{host}/auth/api/v2/user/oauth2/token"
    redirect_url = (f"{host}/auth/api/v2/user/oauth2/authorize"
                    f"?response_type=code&client_id={client_id}"
                    f"&redirect_uri={redirect_uri}&lang=de&state=ccsp")

    options = webdriver.ChromeOptions()
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_argument("--auto-open-devtools-for-tabs")
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    print(f"Opening login page: {cfg['login_url']}")
    driver.get(cfg["login_url"])

    print("\n" + "=" * 50)
    print("Please log in manually in the browser window.")
    print("The script will wait for you to complete the login...")
    print("=" * 50 + "\n")

    try:
        wait = WebDriverWait(driver, 300)
        if brand_key == "kia":
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, cfg["success_selector"])))
        else:
            wait.until(EC.any_of(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, cfg["success_selector"])),
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "button.ctb_button"))))

        print("✅ Login successful! Element found.")
        print(f"Redirecting to: {redirect_url}")
        driver.get(redirect_url)

        code = None
        for i in range(15):
            current_url = driver.current_url
            print(f" - [{i+1}] Checking URL for code...")
            m = re.search(
                r'code=([0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36})',
                current_url)
            if m:
                code = m.group(1)
                break
            time.sleep(1)

        if not code:
            print(f"\n❌ Failed to extract code from URL: {current_url}")
            return

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": cfg["client_secret"],
        }
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            tokens = response.json()
            print(f"\n✅ Your tokens are:\n")
            print(f"- Refresh Token: {tokens.get('refresh_token', 'N/A')}")
            print(f"- Access Token: {tokens.get('access_token', 'N/A')}")
        else:
            print(f"\n❌ Error getting tokens!\n{response.text}")

    except TimeoutException:
        print("❌ Timed out after 5 minutes.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Cleaning up and closing the browser.")
        driver.quit()


# ── Main ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Retrieve Hyundai/Kia Bluelink refresh token")
    parser.add_argument("--brand", required=True, type=str.lower,
                        choices=["hyundai", "kia"],
                        help="Brand of vehicle")
    parser.add_argument("--mode", type=str.lower, default="headless",
                        choices=["headless", "browser"],
                        help="headless (default, no browser) or browser (Selenium)")
    parser.add_argument("--username", help="Email/username (headless mode)")
    parser.add_argument("--password", help="Password (headless mode)")
    args = parser.parse_args()

    if args.mode == "headless":
        if not args.username or not args.password:
            print("❌ Headless mode requires --username and --password")
            print("   Example: python3 bluelinktoken.py --brand kia --username you@email.com --password yourpass")
            print("   Or use --mode browser for manual login.")
            sys.exit(1)
        headless_login(args.brand, args.username, args.password)
    else:
        browser_login(args.brand)


if __name__ == "__main__":
    main()
