"""Streamlit Community Cloud 앱이 잠들지 않도록 주기적으로 접속해서 깨우는 스크립트.
GitHub Actions에서 실행됩니다 (.github/workflows/wake.yml).
"""
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

APP_URL = os.getenv(
    "STREAMLIT_APP_URL",
    "https://jeju-smart-travel-ikvcjnnzr8geqdsxx7wnrx.streamlit.app/",
)

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1280,900")

driver = webdriver.Chrome(options=options)

try:
    driver.get(APP_URL)
    time.sleep(10)

    # 잠든 상태면 "Yes, get this app back up!" 버튼이 보임
    buttons = driver.find_elements(
        By.XPATH, "//button[contains(., 'get this app back up')]"
    )

    if buttons:
        print("앱이 잠들어 있음 → 깨우기 버튼 클릭")
        buttons[0].click()
        time.sleep(60)  # 다시 켜질 때까지 대기
        print("깨우기 완료")
    else:
        print("앱이 이미 깨어 있음")
        time.sleep(20)  # 접속 상태를 잠시 유지
finally:
    driver.quit()
