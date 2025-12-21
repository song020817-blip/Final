import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def close_alert(driver):
    try:
        alert = driver.switch_to.alert
        alert.accept()
        time.sleep(0.5)
    except:
        pass

def wait_visible(driver, xpath, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.XPATH, xpath))
    )

def click(driver, xpath, timeout=10):
    close_alert(driver)
    elem = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", elem)
    time.sleep(0.5)
    close_alert(driver)

def sendkeys(driver, xpath, text):
    box = wait_visible(driver, xpath)
    box.clear()
    box.send_keys(text)
    time.sleep(0.7)
    close_alert(driver)

def click_search(driver):
    close_alert(driver)
    driver.execute_script("window.scrollTo(0,0);")
    time.sleep(0.2)

    buttons = [
        "#search-btn img",
        "#search-btn2 img",
        "div.search-btn > a > img",
        "div#search-btn > a > img",
        "div#search-btn2 > a > img",
        "img[src*='srch']"
    ]

    for selector in buttons:
        try:
            elem = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            driver.execute_script("arguments[0].click();", elem)
            time.sleep(1)
            return
        except:
            continue

    raise Exception("검색 버튼 없음")

# ================================
# 메인 함수 (Flask가 호출함)
# ================================
def run_crawler(tp, addr, sido, sigungu, road, bldg):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")

    driver = webdriver.Chrome(options=options)



    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print("Chrome 실행 실패:", e)
        return None

    driver.get("https://rt.molit.go.kr/")
    time.sleep(1)

    TYPE_BTN = {
        "아파트": '//*[@id="header"]/div[2]/div/div/nav/ul/li[1]/a',
        "연립다세대": '//*[@id="header"]/div[2]/div/div/nav/ul/li[2]/a',
        "단독다가구": '//*[@id="header"]/div[2]/div/div/nav/ul/li[3]/a',
        "오피스텔": '//*[@id="header"]/div[2]/div/div/nav/ul/li[4]/a'
    }

    click(driver, TYPE_BTN[tp])
    click(driver, '//*[@id="ladBtn"]/a')
    click(driver, '//*[@id="jibun"]' if addr == "지번" else '//*[@id="road"]')
    click(driver, '//*[@id="pnuBtn"]/a')

    Select(wait_visible(driver, '//*[@id="srhSidoCodeS"]')).select_by_visible_text(sido)
    time.sleep(0.3)
    Select(wait_visible(driver, '//*[@id="srhSignguCodeS"]')).select_by_visible_text(sigungu)
    time.sleep(1)

    sendkeys(driver, '//*[@id="srhRoadNmI"]', road)
    click_search(driver)

    click(driver, '//*[@id="roadList"]/li[1]')
    time.sleep(0.5)
    click(driver, '//*[@id="roadList"]/li[1]/a/div/h5')

    time.sleep(1)
    click(driver, '//*[@id="bldgBtn"]/a')
    time.sleep(0.5)

    sendkeys(driver, '//*[@id="srhBldgNmI"]', bldg)
    click(driver, '//*[@title="단지명검색"]')
    time.sleep(1)
    click(driver, '//*[@id="danjiLast"]')

    # 전월세 탭 클릭
    click(driver, '//*[@id="dtlLrms"]')
    time.sleep(1)

    try:
        rows = driver.find_elements(By.XPATH, '//*[@id="dtlList"]/table/tbody/tr')
        results = []

        i = 0
        while i < len(rows):
            tds = rows[i].find_elements(By.TAG_NAME, "td")

            if len(tds) >= 6:
                data = {
                    "전용면적(m^2)": tds[0].text,
                    "계약일": tds[1].text,
                    "계약기간": tds[2].text,
                    "보증금(만원)": tds[3].text,
                    "종전보증금(만원)": tds[4].text,
                    "계약구분": tds[5].text
                }

                # 바로 다음 tr이 월세 행
                if i + 1 < len(rows):
                    rent_tds = rows[i + 1].find_elements(By.TAG_NAME, "td")
                    if len(rent_tds) >= 3:
                        data["월세(만원)"] = rent_tds[1].text
                        data["종전월세(만원)"] = rent_tds[2].text
                    else:
                        data["월세(만원)"] = ""
                        data["종전월세(만원)"] = ""

                results.append(data)
                i += 2
            else:
                i += 1

        result = results




    except:
        result = None

    driver.quit()
    return result