# from selenium import webdriver
from __future__ import annotations

from seleniumwire import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import csv
import os
import random
import string
import time
from typing import Callable, Optional

from fp.fp import FreeProxy
from fake_useragent import UserAgent

from providers.fivesim import FiveSimProvider
from providers.sms_base import BotSettings, SmsConfig

# #region agent log
import json as _agent_json

_AGENT_LOG_PATH = r"c:\dev\telegram-mcp\debug-edd7d7.log"


def _agent_dbg(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    try:
        line = _agent_json.dumps(
            {
                "sessionId": "edd7d7",
                "runId": "run1",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000),
            },
            ensure_ascii=True,
        ) + "\n"
        with open(_AGENT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
# #endregion

# Defaults when running `python app.py` without GUI (CLI uses env via SmsConfig.from_env)
AUTO_GENERATE_UERINFO = True
AUTO_GENERATE_NUMBER = 10
INCLUDE_REFER_URL = False
WAIT = 4
REQUEST_MAX_TRY = 10

SELECTORS = {
    "create_account":[
        "//button[@class='VfPpkd-LgbsSe VfPpkd-LgbsSe-OWXEXe-dgl2Hf ksBjEc lKxP2d LQeN7 FliLIb uRo0Xe TrZEUc Xf9GD']",
        "//*[@class='JnOM6e TrZEUc kTeh9 KXbQ4b']"
        ],
    'for_my_personal_use':[
        "//span[@class='VfPpkd-StrnGf-rymPhb-b9t22c']",
        ], 
    "first_name":"//*[@name='firstName']",
    "last_name":"//*[@name='lastName']",
    "username":"//*[@name='Username']",
    "password":"//*[@name='Passwd']",
    "confirm_password":"//*[@name='PasswdAgain']",
    "next":[
            "//button[@class='VfPpkd-LgbsSe VfPpkd-LgbsSe-OWXEXe-k8QpJ VfPpkd-LgbsSe-OWXEXe-dgl2Hf nCP5yc AjY5Oe DuMIQc LQeN7 qIypjc TrZEUc lw1w4b']",
            "//button[contains(text(),'Next')]",
            "//button[contains(text(),'I agree')]"
    ],
    "phone_number":"//*[@id='phoneNumberId']",
    "code":'//input[@name="code"]',
    "acc_phone_number":'//input[@id="phoneNumberId"]',
    "acc_day":'//input[@name="day"]',
    "acc_month":'//select[@id="month"]',
    "acc_year":'//input[@name="year"]',
    "acc_gender":'//select[@id="gender"]',
    "username_warning":'//*[@class="jibhHc"]',
    "username_select":'//*[@aria-posinset="3"]'
}
# https://webflow.com/made-in-webflow/fast , I tried to find the fast websites and you can add more.
SITE_LIST = [
    'https://google.com',
    'https://wizardrytechnique.webflow.io/',
    'https://www.rachelbavaresco.com/',
    'https://lightning-bolt.webflow.io/'
]
def generatePassword():
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + string.punctuation
    size = random.randint(8, 12)
    return ''.join(random.choice(chars) for x in range(size))

def getRandomeUserAgent():
    UAGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.52',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 YaBrowser/21.8.1.468 Yowser/2.5 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64; rv:105.0) Gecko/20100101 Firefox/105.0',
        'Mozilla/5.0 (X11; CrOS x86_64 14440.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4807.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14467.0.2022) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4838.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14469.7.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.13 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14455.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4827.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14469.11.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.17 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14436.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4803.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14475.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4840.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14469.3.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.9 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14471.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4840.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14388.37.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.9 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14409.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4829.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14395.0.2021) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4765.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14469.8.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.14 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14484.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4840.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14450.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4817.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14473.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4840.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14324.72.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.91 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14454.0.2022) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4824.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14453.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4816.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14447.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4815.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14477.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4840.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14476.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4840.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14469.8.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.9 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14588.67.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14588.67.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.69.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.82 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14695.25.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.22 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.89.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.133 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.57.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.64 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.89.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.133 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.84.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.93 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14469.59.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14588.91.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.55 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14695.23.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.20 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14695.36.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.36 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14588.41.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.26 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14695.11.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.6 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14588.67.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14685.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.4992.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.69.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.82 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14682.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.16 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14695.9.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.5 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14574.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4937.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14388.52.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14716.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5002.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14268.81.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14469.41.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.48 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14388.61.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14695.37.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.37 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14588.51.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.32 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.89.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.133 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14588.92.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.56 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.43.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.54 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14505.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4870.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.16.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.25 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.28.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.44 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14543.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4918.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14588.11.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.6 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.89.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.133 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14588.31.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.19 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14526.6.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.13 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14658.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.4975.0 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS x86_64 14695.25.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5002.0 Safari/537.36'
    ]
    agent = random.choice(UAGENTS)
    return agent

def set_driver(settings: BotSettings, log):
    """Initialize Chrome via Selenium Wire. SOCKS proxy optional (GUI / BotSettings.socks_proxy)."""
    # #region agent log
    _agent_dbg(
        "H5",
        "app.py:set_driver",
        "entry",
        {
            "data_dir": settings.data_dir,
            "headless": settings.headless,
            "socks_present": bool((settings.socks_proxy or "").strip()),
            "proxy_csv_exists": os.path.exists(
                os.path.join(settings.data_dir, "Proxy_DB.csv")
            ),
        },
    )
    _set_driver_t0 = time.time()
    # #endregion
    seleniumwire_options = {"exclude_hosts": ["google-analytics.com"]}

    proxy_path = os.path.join(settings.data_dir, "Proxy_DB.csv")
    proxy_list = []
    try:
        with open(proxy_path, "r", encoding="utf-8", errors="ignore") as proxy_list_file:
            proxy_list = list(csv.reader(proxy_list_file))
    except OSError:
        log("################ No Proxy_DB.csv or unreadable; FreeProxy only ################")

    try:
        random_proxy = FreeProxy(timeout=1).get()
        log("################ Use FreeProxy library to get HTTP proxy ################")
    except Exception:
        log("################ Use Proxy DB to get HTTP proxy ################")
        if not proxy_list:
            raise RuntimeError("No HTTP proxy available (FreeProxy failed and Proxy_DB missing)") from None
        random_proxy = "http://" + random.choice(proxy_list)[0]

    HTTP_PROXY = random_proxy
    log(str(HTTP_PROXY))

    proxy_options: dict[str, str] = {"no_proxy": "localhost,127.0.0.1"}
    socks = (settings.socks_proxy or "").strip()
    if socks:
        proxy_options["http"] = socks
        proxy_options["https"] = socks
    else:
        proxy_options["http"] = HTTP_PROXY
        proxy_options["https"] = HTTP_PROXY

    seleniumwire_options["proxy"] = proxy_options
    # prox = Proxy()
    # prox.proxy_type = ProxyType.MANUAL
    # prox.socks_proxy = SOCKS_PROXY
    # prox.socks_version = 5
    # prox.http_proxy = HTTP_PROXY
    # print(SOCKS_PROXY)
    # prox.http_proxy = SOCKS_PROXY
    # prox.https_proxy = SOCKS_PROXY

    # capabilities = webdriver.DesiredCapabilities.CHROME
    # prox.add_to_capabilities(capabilities)

    # Set User Agent
    # user_agent = getRandomeUserAgent() # Random user agent
    # user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36" # Fixed agent
    # Please refer to this https://github.com/fake-useragent/fake-useragent
    user_agent = UserAgent(fallback="Mozilla/5.0 (Macintosh; Intel Mac OS X10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36").random
    log(str(user_agent))
    # Set Browser Option
    options = ChromeOptions()
    # options = FirefoxOptions()

    prefs = {"profile.password_manager_enabled": False, "credentials_enable_service": False, "useAutomationExtension": False}
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument("disable-popup-blocking")
    options.add_argument("disable-notifications")
    options.add_argument("disable-popup-blocking")
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')

    if settings.headless:
        options.add_argument("--headless=new")
    # options.add_argument("--incognito")
    # options.add_argument(r"--user-data-dir=C:\\Users\\Username\\AppData\\Local\\Google\\Chrome\\User Data")
    # options.add_argument(r'--profile-directory=ProfileName')
    options.add_argument(f"user-agent={user_agent}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options = options, seleniumwire_options=seleniumwire_options)
    #driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options = options, seleniumwire_options=seleniumwire_options)
    # #region agent log
    _agent_dbg(
        "H5",
        "app.py:set_driver",
        "driver_ready",
        {"elapsed_ms": int((time.time() - _set_driver_t0) * 1000)},
    )
    # #endregion
    return driver

def run_bot(
    settings: BotSettings,
    log=print,
    should_stop: Optional[Callable[[], bool]] = None,
):
    # #region agent log
    _agent_dbg(
        "H6",
        "app.py:run_bot",
        "entered",
        {
            "data_dir": settings.data_dir,
            "auto_generate_number": settings.auto_generate_number,
            "headless": settings.headless,
            "wait": settings.wait,
            "request_max_try": settings.request_max_try,
            "first_csv_exists": os.path.exists(
                os.path.join(settings.data_dir, "First_Name_DB.csv")
            ),
            "last_csv_exists": os.path.exists(
                os.path.join(settings.data_dir, "Last_Name_DB.csv")
            ),
            "proxy_csv_exists": os.path.exists(
                os.path.join(settings.data_dir, "Proxy_DB.csv")
            ),
        },
    )
    # #endregion
    sms_provider = FiveSimProvider(settings.sms)
    AUTO_GENERATE_UERINFO = settings.auto_generate_userinfo
    AUTO_GENERATE_NUMBER = settings.auto_generate_number
    WAIT = settings.wait
    REQUEST_MAX_TRY = settings.request_max_try
    INCLUDE_REFER_URL = settings.include_refer_url
    data_dir = settings.data_dir
    user_number = 0
    i = 0
    user_info_file = None
    user_infos: list[list[str]] = []

    if AUTO_GENERATE_UERINFO:
        user_number = AUTO_GENERATE_NUMBER
        log("################ Open First_Name_DB.csv ################")
        try:
            first_name_path = os.path.join(data_dir, "First_Name_DB.csv")
            with open(
                first_name_path, "r", encoding="utf-8", errors="ignore"
            ) as first_name_file:
                first_names = list(csv.reader(first_name_file))
        except OSError:
            log("################ Please check if First_Name_DB.csv exists ################")
            raise

        log("################ Open Last_Name_DB.csv ################")
        try:
            last_name_path = os.path.join(data_dir, "Last_Name_DB.csv")
            with open(
                last_name_path, "r", encoding="utf-8", errors="ignore"
            ) as last_name_file:
                last_names = list(csv.reader(last_name_file))
        except OSError:
            log("################ Please check if Last_Name_DB.csv exists ################")
            raise
    else:
        log("################ Open User.csv ################")
        try:
            user_info_file = open(
                settings.user_csv_path,
                "r",
                encoding="utf-8",
                errors="ignore",
            )
            user_infos = list(csv.reader(user_info_file))
            user_number = len(user_infos)
        except OSError:
            log("################ Please check if User.csv exists ################")
            raise

    while True:
        try:
            if i == user_number:
                break

            i = i + 1
            if should_stop and should_stop():
                log("################ Stopped by user ################")
                break

            log(f"################ User: {i} ################")
            user_name_manual = ""
            if AUTO_GENERATE_UERINFO:
                first_name = random.choice(first_names)[0]
                last_name = random.choice(last_names)[0]
                password = generatePassword()
                birthday = str(random.randint(1, 12)) + "/" + str(
                    random.randint(1, 28)
                ) + "/" + str(random.randint(1980, 1999))
                log(first_name + "\t" + last_name + "\t" + password + "\t" + birthday)
            else:
                row = user_infos[i]
                if "Firstname" == row[0]:
                    continue

                first_name = row[0]
                last_name = row[1]
                password = row[2]
                birthday = row[3]
                log(first_name + "\t" + last_name + "\t" + password + "\t" + birthday)
                try:
                    user_name_manual = row[4]
                except (IndexError, KeyError):
                    user_name_manual = ""

            driver = None
            log("################ Initialize Chrome Driver ################")
            driver = set_driver(settings, log)

            log("################ Random Refer website to bypass Google Bot Detection ################")
            if INCLUDE_REFER_URL:
                random_url = random.choice(SITE_LIST)
                driver.get(random_url)

            # 4 ways to go to account creation page.
            random_int = random.randint(1,4)
            if random_int ==  1:

                log('################ Creat a google account article ################')
                driver.get('https://support.google.com/accounts/answer/27441?hl=en')
                WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH,'//*[@id="hcfe-content"]/section/div/div[1]/article/section/div/div[1]/div/div[2]/a[1]'))).click()
                time.sleep(WAIT)
            elif random_int == 2:
                log('################ Go to account page ################')
                driver.get("https://accounts.google.com")

                time.sleep(WAIT)
                
                log('################ Click "Create account" ################')
                for selector in SELECTORS["create_account"]:
                    try:
                        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                        break
                    except:
                        pass
                log('################ Click "For my personal use" ################')
                for selector in SELECTORS["for_my_personal_use"]:
                    try:
                        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                        break
                    except:
                        pass

            elif random_int == 3:
                driver.get('https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp')
                time.sleep(WAIT)
            
            elif random_int == 4:
                driver.get('https://support.google.com/mail/answer/56256?hl=en')
                WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH,'//*[@id="hcfe-content"]/section/div/div[1]/article/section/div/div[1]/div/p[1]/a'))).click()
                time.sleep(WAIT)

            username_try = 0

            # if the username exists, it retries REQUEST_MAX_TRY times.
            while username_try < REQUEST_MAX_TRY:
                time.sleep(WAIT*2)

                log('################ 1st step of Creation Wizard. ################')


                log("################ Generate User Try: ", username_try+1, " ################")
                # set the first name.
                log('################ First Name ################')
                first_name_tag = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['first_name'])))
                first_name_tag.clear()
                time.sleep(WAIT/2)
                log(first_name)
                first_name_tag.send_keys(first_name)

                # set the surname.
                log('################ Last Name ################')
                last_name_tag = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['last_name'])))
                last_name_tag.clear()
                last_name_tag.send_keys(last_name)

                #click next button
                log('################ "Next" ################')
                for selector in SELECTORS['next']:
                    try:
                        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                        break
                    except:
                        pass
                time.sleep(WAIT*2)

                log('################ 2st step of Creation Wizard. ################')
                log('################ Birthday & Gender ################')
                # Date   
                WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_day']))).send_keys(birthday.split('/')[1])
                
                # Month
                select_acc_month = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_month'])))

                acc_month = Select(select_acc_month)
                acc_month.select_by_value(birthday.split('/')[0])

                # Year
                WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_year']))).send_keys(birthday.split('/')[2])

                select_acc_gender = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_gender'])))

                # Gender
                acc_gender = Select(select_acc_gender)
                acc_gender.select_by_value('1')

               #click next button
                log('################ Click "Next" Buton ################')
                for selector in SELECTORS['next']:
                    try:
                        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                        break
                    except:
                        pass
                time.sleep(WAIT*2)

                # set username
                log('################ Set User Name ################')
                if user_name_manual == "":
                    rand_5_digit_num = random.randint(10000,99999)
                    user_name = first_name +"."+ last_name
                    user_name = user_name.lower() + str(rand_5_digit_num)
                else:
                    user_name = user_name_manual
                try:
                    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['username_select']))).click()
                except:
                    pass
                try:
                    user_name_tag = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['username'])))
                    user_name_tag.clear()
                    log(user_name)
                    time.sleep(WAIT/2)
                    user_name_tag.send_keys(user_name)
                # time.sleep(WAIT*1000)
                except:
                    pass

                #click next button
                log('################ Click "Next" Buton ################')
                for selector in SELECTORS['next']:
                    try:
                        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                        break
                    except:
                        pass
                time.sleep(WAIT*2)
                log('################ Check Username Validation ################')
                try:
                    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['username_warning'])))
                    user_name_manual = ""
                    log("Invalid")
                    username_try = username_try + 1
                    continue
                except:
                    log("Valid")
                    pass

                # set password
                log('################ Set Password ################')
                passwd_tag =WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['password'])))
                passwd_tag.clear()
                passwd_tag.send_keys(password)

                log('################ Set Confirm Password ################')
                confirmwd_tag = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['confirm_password'])))
                confirmwd_tag.clear()
                confirmwd_tag.send_keys(password)

                #click next button
                log('################ Click "Next" Buton ################')
                for selector in SELECTORS['next']:
                    try:
                        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                        break
                    except:
                        pass
                time.sleep(WAIT*2)

                log('################ Check Phone Verification ################')
                without_verification = False
                try:
                    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_day'])))
                    without_verification = True
                    log("No. It doesn't require.")
                    break
                except:
                    log("Yes. It requires")
                    pass
                log('################ Input Phone Number ################')
                try:
                    phone_number_input = WebDriverWait(driver, WAIT*3).until(EC.presence_of_element_located((By.XPATH, SELECTORS['phone_number'])))
                    time.sleep(WAIT)
                    break
                except:
                    username_try = username_try + 1
            number = ""
            order_id = None
            if without_verification is False:
                log("################ Get Phone Number from 5sim ################")
                try:
                    number, order_id = sms_provider.buy_number(REQUEST_MAX_TRY, float(WAIT))
                except Exception as ex:
                    log(str(ex))
                    raise Exception("Go to next account.") from ex

                phone_number_input.send_keys(number)

                log('################ Click "Next" Buton ################')
                for selector in SELECTORS['next']:
                    try:
                        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                        break
                    except:
                        pass

                log("################ Get SMS Code from 5sim ################")
                time.sleep(WAIT)
                try:
                    code = sms_provider.wait_for_code(
                        order_id,
                        timeout_s=float(WAIT * 5 * 60),
                        poll_interval=float(WAIT * 5),
                    )
                except Exception as ex:
                    log(str(ex))
                    if order_id is not None:
                        sms_provider.cancel_order(order_id)
                    raise Exception("Go to next account.") from ex

                log('################ Verify Phone Code ################')
                WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['code']))).send_keys(code)

                log('################ Click "Verify" Buton ################')
                for selector in SELECTORS['next']:
                    try:
                        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                        break
                    except:
                        pass
                if order_id is not None:
                    sms_provider.finish_ok(order_id)

            time.sleep(WAIT*2)
            log('################ Clear Account Phone Number ################')
            # WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_phone_number']))).clear()

            # print('################ Account Birthday ################')
            # # Date   
            # WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_day']))).send_keys(birthday.split('/')[1])
            
            # # Month
            # select_acc_month = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_month'])))

            # acc_month = Select(select_acc_month)
            # acc_month.select_by_value(birthday.split('/')[0])

            # # Year
            # WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_year']))).send_keys(birthday.split('/')[2])

            # select_acc_gender = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, SELECTORS['acc_gender'])))

            # # Gender
            # acc_gender = Select(select_acc_gender)
            # acc_gender.select_by_value('1')

            log('################ Click "Next" Buton ################')
            for selector in SELECTORS['next']:
                try:
                    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                    break
                except:
                    pass
            log('################ Click "I agree" Buton ################')
            time.sleep(WAIT)

            # Scroll to click "I agree"
            driver.execute_script("window.scrollTo(0, 800)") 
            time.sleep(WAIT)
            for selector in SELECTORS['next']:
                try:
                    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, selector))).click()
                    break
                except:
                    pass
            time.sleep(WAIT*3)
            log("################ Save to Created.txt ################")
            os.makedirs(data_dir, exist_ok=True)
            created_path = os.path.join(data_dir, "Created.txt")
            with open(created_path, "a", encoding="utf-8", errors="replace") as f:
                f.write(user_name + "\t" + password + "\t" + birthday + "\t" + number + "\n")

            driver.quit()
        except Exception as e:
            log(str(e))
            if driver is not None:
                driver.quit()

    if user_info_file is not None:
        try:
            user_info_file.close()
        except OSError:
            pass


def main():
    sms = SmsConfig.from_env()
    if not sms.api_token:
        print("Set FIVESIM_TOKEN environment variable or run: python run_gui.py")
        return
    run_bot(
        BotSettings(
            sms=sms,
            auto_generate_userinfo=AUTO_GENERATE_UERINFO,
            auto_generate_number=AUTO_GENERATE_NUMBER,
            user_csv_path="User.csv",
            wait=WAIT,
            request_max_try=REQUEST_MAX_TRY,
            socks_proxy=os.environ.get("SOCKS_PROXY", "").strip() or None,
            headless=os.environ.get("HEADLESS", "").strip().lower()
            in ("1", "true", "yes"),
            include_refer_url=INCLUDE_REFER_URL,
        )
    )


if __name__ == "__main__":
    main()