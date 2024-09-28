from selenium.webdriver.common.by import By
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import json
import time
import requests
import chromedriver_autoinstaller
from urllib.parse import urlparse, parse_qs

# WebDriver headless mode settings
options = webdriver.ChromeOptions()
# options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--window-size=1920,1080")

# Specify the path to Chromium binary
options.binary_location = "/snap/bin/chromium"

# Install the appropriate ChromeDriver
chromedriver_autoinstaller.install()

# BS4 setting for secondary access
session = requests.Session()
headers = {"User-Agent": "user value"}

retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])

session.mount("http://", HTTPAdapter(max_retries=retries))

# Driver setup
driver = webdriver.Chrome(options=options)

url = (
    "https://map.naver.com/p/entry/place/1793953868?c=15.00,0,0,0,dh&placePath=/review"
)
driver.get(url)
driver.implicitly_wait(1.5)
wait = WebDriverWait(driver, 1.5)
time.sleep(1.5)

# 에러가 없는 title들 선택
existing_titles = []
with open("output.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        json_obj = json.loads(line)

        if "title" in json_obj:
            existing_titles.append(json_obj["title"])

# Get 관광지 names
data = []
with open("./names.json", "r") as file:
    places = json.loads(file.read())


# 저장된 데이터를 일정 양 이상일 때 한 번에 저장하는 함수
def save_data(buffer, filename):
    with open(filename, "a", encoding="utf-8") as file:
        for item in buffer:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


# 에러를 일정 양 모아서 한 번에 저장하는 함수
def save_errors(buffer, filename):
    with open(filename, "a", encoding="utf-8") as file:
        for error in buffer:
            file.write(error + "\n")


# 확인 필요한 리스트
def save_checks(buffer, filename):
    with open(filename, "a", encoding="utf-8") as file:
        for error in buffer:
            file.write(error + "\n")


# 크롤링 작업을 처리하며 데이터를 모아 한 번에 저장
data_buffer = []
error_buffer = []
check_buffer = []
BUFFER_LIMIT = 5  # 버퍼에 데이터를 몇 개 모을지 설정

# For each place
for place in places:
    # 해당 지역만 진행
    if place["areacode"] != "경상북도":
        continue

    title = place["title"]
    loc = place["address"]

    # 이미 한 지역 스킵
    if title in existing_titles:
        continue

    place_data = {
        "title": title,
    }

    try:
        # Search bar
        term = "".join(title.split())
        input_field = driver.find_element(
            By.CSS_SELECTOR, 'input[class="input_search"][maxlength="255"]'
        )
        input_field.clear()

        # 2. 검색창에 남은 텍스트가 있을 경우를 대비해 BACKSPACE로 텍스트 삭제
        input_field.send_keys(Keys.CONTROL + "a")  # 전체 선택
        time.sleep(0.05)
        input_field.send_keys(Keys.BACKSPACE)  # 전체 선택 후 삭제
        time.sleep(0.05)

        input_field.send_keys(term)
        time.sleep(0.2)
        input_field.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.2)
        input_field.send_keys(Keys.RETURN)
        time.sleep(1)

        # # 검색해서 결과로 바로 이동 되지 않으면 첫번째 링크 클릭
        # not_sure = False
        # try:
        #     container = wait.until(
        #         EC.presence_of_element_located((By.ID, "_pcmap_list_scroll_container"))
        #     )
        #     first_button = container.find_element(By.CSS_SELECTOR, "a.P7gyV")
        #     first_button.click()
        #     not_sure = True

        # except Exception as e:
        #     print("The specified elements were not found within the given time.")

        # Switch to iframe
        iframe = wait.until(EC.presence_of_element_located((By.ID, "entryIframe")))
        driver.switch_to.frame(iframe)

        # 선택한 첫번째 링크와 제목이 같은지 비교
        title_span = driver.find_element(By.CSS_SELECTOR, "div#_title span.GHAhO")
        parent = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.vV_z_"))
        )
        location = parent.find_element(By.CLASS_NAME, "LDgIH")
        # print(title_span.text)
        # print(location.text)
        if title_span.text != title:
            check_buffer.append(
                f"{title}: {title_span.text}\n# {loc}: {location.text}\n"
            )

        # 리뷰 클릭
        driver.find_element(
            By.XPATH,
            '//*[@id="app-root"]/div/div/div/div[4]/div/div/div/div//a[span[text()="리뷰"]]',
        ).click()
        time.sleep(1.5)

        # 스크롤
        for _ in range(12):
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
            time.sleep(0.15)
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_UP)
        time.sleep(1)

        # 리뷰 창 스크롤 (더보기 클릭)
        for i in range(2):  # 최대 몇번 더보기 누를건지
            try:
                more_button = driver.find_element(
                    By.XPATH,
                    '//*[@id="app-root"]/div/div/div/div[6]/div[3]/div[3]/div[2]/div/a',
                )
                more_button.click()
            except Exception as e:  # 더이상 더보기가 없음
                print(f"Failed to click on attempt {i+1}: {e}")
                break

            # 스크롤
            for _ in range(12):
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
                time.sleep(0.15)
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_UP)
            time.sleep(1)

        # Parse data
        time.sleep(2)
        html = driver.page_source
        bs = BeautifulSoup(html, "lxml")
        reviews = bs.select("li.pui__X35jYm.EjjAW")
        photos = bs.select("div.CEX4u > div.fNygA > a.QX0J7")
        photo_urls = [photo.find("img")["src"] for photo in photos if photo.find("img")]
        no_reviews = bs.select_one("div.dAsGb > span.PXMot")

        photo_data = []
        for url in photo_urls:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            src_value = query_params.get("src", [""])[0]
            photo_data.append(src_value)

        place_data.update({"photos": photo_data})

        review_count = element = driver.find_element(
            By.XPATH, "/html/body/div[3]/div/div/div/div[2]/div[1]/div[2]/span[2]/a"
        ).text
        place_data.update({"review_count": review_count})

        review_data = []
        for r in reviews:
            content = r.select_one("div.pui__vn15t2 > a.pui__xtsQN-")

            date_elements = r.select("div.pui__QKE5Pr > span.pui__gfuUIT > time")
            date = date_elements[0] if date_elements else "N/A"

            content = content.text.strip() if content else ""
            date = date.text.strip() if date else ""

            if content != "":
                review_data.append({"content": content, "data": date})
            time.sleep(0.06)

        place_data.update({"reviews": review_data})

        data_buffer.append(place_data)

        # 버퍼가 가득 찼으면 파일에 기록
        if len(data_buffer) >= BUFFER_LIMIT:
            save_data(data_buffer, "output.jsonl")
            data_buffer = []  # 버퍼 초기화
            save_errors(error_buffer, "error.txt")
            error_buffer = []  # 버퍼 초기화
            save_checks(check_buffer, "check.txt")
            check_buffer = []

    except Exception as e:
        data_buffer.append(place_data)
        error_buffer.append(title)
        # 항상 초기 상태로 회귀
        driver.get(
            "https://map.naver.com/p/entry/place/1793953868?c=15.00,0,0,0,dh&placePath=/review"
        )
        time.sleep(1.5)
    finally:
        driver.switch_to.default_content()
        continue

save_data(data_buffer, "output.jsonl")
save_errors(error_buffer, "error.txt")
save_checks(check_buffer, "check.txt")
