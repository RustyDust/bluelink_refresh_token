# bluelink_refresh_token

Retrieve the refresh token needed for Hyundai/Kia Bluelink API access in Home Assistant / evcc.

## Headless Mode (recommended, no browser needed)

Since Kia/Hyundai have blocked browser-based OAuth flows ("abusing request" error), this script now supports a **headless mode** that works without any browser.

The headless mode was developed by reverse engineering the official Kia Connect App. It uses `curl_cffi` to impersonate an Android Chrome TLS fingerprint and performs the complete OAuth flow via HTTP requests.

### Quick Start

```bash
git clone https://github.com/RustyDust/bluelink_refresh_token.git
cd bluelink_refresh_token
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Kia
python3 bluelinktoken.py --brand kia --username your@email.com --password yourpassword

# Hyundai
python3 bluelinktoken.py --brand hyundai --username your@email.com --password yourpassword
```

Output:
```
[1/4] Loading authorize page...
  ✅ Session established
[2/4] Fetching RSA public key...
  ✅ Password encrypted
[3/4] Signing in...
  ✅ Authorization code received
[4/4] Exchanging code for tokens...

✅ Your tokens are:

- Refresh Token: M2M2OG................................YOTG5
- Access Token: eyJhbGc.........................0_AijpHXp0yg
```

### How it works

1. Fetches the RSA public key from `/auth/api/v1/accounts/certs`
2. Encrypts the password with RSA (same as the login page)
3. POSTs to `/auth/account/signin` with the app's `client_id` directly (not the website `client_id`)
4. Gets the authorization code in the 302 redirect — no `connector_session_key` needed
5. Exchanges the code for tokens

The key insight: using the app's `client_id` (`fdc85c00-...`) directly in the signin POST bypasses the `connector_session_key` flow that Kia blocks as "abusing".

## Browser Mode (fallback)

If headless mode doesn't work for your setup, you can still use the original browser-based flow:

```bash
pip install -r requirements.txt
python3 bluelinktoken.py --brand kia --mode browser
```

This opens a Chrome window where you log in manually.

## Using the token

Use the **Refresh Token** as the password (not your Bluelink password) when configuring:

- [evcc](https://docs.evcc.io/en/docs/devices/vehicles#hyundai-bluelink)
- [Home Assistant Kia/Hyundai integration](https://github.com/Hyundai-Kia-Connect/kia_uvo)

> **Note:** The refresh token is valid for 180 days. After that, run the script again.

## Docker / Home Assistant Add-on

For a web-based UI with evcc integration and automatic token transfer, see [Bluelink Token Generator](https://github.com/TMA84/bluelink-refresh-token).

## Credits

- Original Kia implementation: [fuatakgun](https://gist.github.com/fuatakgun/fa4ef1e1d48b8dca2d22133d4d028dc9)
- Original Hyundai implementation: [Maaxion](https://gist.github.com/Maaxion/22a38ba8fb06937da18482ddf35171ac)
- Headless login via APK reverse engineering: [TMA84](https://github.com/TMA84)
