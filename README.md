# bluelink_refresh_token

This scripts helps owners of cars made by Hyundai or Kia to retrieve the
`refresh_token` that is now necessary to access the Bluelink API in the
integrations for [HomeAssistant](https://github.com/home-assistant) and [evcc](https://github.com/evcc-io/evcc/).

It is a combination of the separate efforts of [@fuatakgun](https://gist.github.com/fuatakgun)
(original Kia implementation) and [@Maaxion](https://gist.github.com/Maaxion) (Hyundai aption)

## Prerequisites
You need to have the following installed on your computer

1) Python3 >= 3.12
1) [git](https://git-scm.com/downloads)
1) Chrome or a Chromium based Brower

## Preparations

1) Copy the script to your local hard drive
   1) Using `git clone`
      ``` bash 
      git clone https://github.com/RustyDust/bluelink_refresh_token.git
      cd bluelink_refresh_token
      ````
   1) Using the command line
      1) **Linux/MacOS**
         ``` bash 
         wget -O bluelinktoken.py https://raw.githubusercontent.com/RustyDust/bluelink_refresh_token/refs/heads/main/bluelinktoken.py
         ```
      1) **Windows**  
         Run in `powershell`:
         ``` powershell
         iwr -UseBasicParsing -OutFile bluelinktoken.py https://raw.githubusercontent.com/RustyDust/bluelink_refresh_token/refs/heads/main/bluelinktoken.py
         ```
1) Prepare the python runtime environment (you _do_ have Python3 installed, right?)
   1) **Linux/MacOS**
      ``` bash
      python3 -m venv .venv
      source .venv/bin/activate
      pip3 install selenium requests
      ```
   1) **Windows**
      ``` powershell
      python -m venv .venv
      .\.venv\Scripts\Activate.ps1
      python -m pip install --upgrade pip
      pip install selenium requests webdriver-manager
      ````

## Running the Script
> [!NOTE]
> You should still be in the Python environment from step 2.1 or 2.2 from above!

### **Kia**
1) **Linux:**
   ``` bash
   python3 -/bluelinktoken.py --brand kia
   ```
1) **Windows:**
   ``` powershell
   python .\bluelinktoken.py --brand kia
   ```

### **Hyundai**
1) **Linux:**
   ``` bash
   python3 -/bluelinktoken.py --brand hyundai
   ```
1) **Windows:**
   ``` powershell
   python .\bluelinktoken.py --brand hyundai
   ```

The script will automatically open your browser (you did install Chrome, yes?)
with the correct URL for your vehicle's brand. Log in using the credentials 
(username / password) you use in the app on your mobile phone.

If everything worked as expected you'll get an output in your terminal similar
to this:

``` bash
Opening login page: https://idpconnect-eu.(kia/hyundai).com/auth/api/v2/user/oauth2/authorize?(...shortened...)

==================================================
Please log in manually in the browser window.
The script will wait for you to complete the login...
==================================================

✅ Login successful! Element found.

✅ Your tokens are:

- Refresh Token: M2M2OG................................YOTG5
- Access Token: eyJhbGc.........................0_AijpHXp0yg
Cleaning up and closing the browser.
```
## Using in Home Assistant or evcc

Use the `Refresh Token` from above as the _password_ together with your normal
username when setting up either the HomeAssistant or evcc integration for your 
vehicle.

> [!NOTE]
> The `refresh token` you generated is valid for 180 days. After that period 
> you'll have to generate a new one and reconfigure your integrations
