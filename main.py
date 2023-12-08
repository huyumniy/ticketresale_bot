import requests
import time
import re
import sys, os
import json
from selenium.webdriver.common.by import By
import undetected_chromedriver as webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import logging
from random import choice
import shutil
import tempfile
from twocaptcha import TwoCaptcha


solver = TwoCaptcha('29ada3bf8a7df98cfa4265ea1145c77b')

CAPTCHA_URL = 'https://peak-euwe.secutix.com'

BLACKLIST = []
logging.basicConfig(filename='bot.log', level=logging.DEBUG)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

BASE_URL = 'https://ticketresale.lancashirecricket.co.uk'


# https://ticketresale.lancashirecricket.co.uk/selection/resale/seat/item?perfId=101757109741&amp;polygonId=P_BU9&amp;blocks=101745466997&amp;areas=#seat-map-sub-container
# https://ticketresale.lancashirecricket.co.uk/selection/resale/seat/item?perfId=101757109741&polygonId=P_BU9&blocks=101745466997&areas=#seat-map-sub-container
class ProxyExtension:
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "76.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: %d
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        { urls: ["<all_urls>"] },
        ['blocking']
    );
    """

    def __init__(self, host, port, user, password):
        self._dir = os.path.normpath(tempfile.mkdtemp())

        manifest_file = os.path.join(self._dir, "manifest.json")
        with open(manifest_file, mode="w") as f:
            f.write(self.manifest_json)

        background_js = self.background_js % (host, port, user, password)
        background_file = os.path.join(self._dir, "background.js")
        with open(background_file, mode="w") as f:
            f.write(background_js)

    @property
    def directory(self):
        return self._dir

    def __del__(self):
        shutil.rmtree(self._dir)


def get_area(driver):
  try:
    if WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'path[title][style="opacity: 0;"]'))):
      areas = driver.find_elements(By.CSS_SELECTOR, 'path[title][style="opacity: 0;"]')
      selected_area = choice(areas)
      print(selected_area)
      return selected_area
  except: return False


def check_grouped_content(driver):
  try:
    if WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#collapsiblePanel_performance_chooser > div"))):
      return True
  except: return False


def check_simple_content(driver):
  try:
    if WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#collapsiblePanel_main_content_resale_item"))):
      return True
  except: return False


def click_grouped_content(driver):
  try:
    if WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'p[class="semantic-no-styling available"]'))):
      select = driver.find_elements(By.CSS_SELECTOR, 'p[class="semantic-no-styling available"]')
      selected_element = choice(select)
      selected_element.click()
      return True
  except: return False


def click_simple_seats(driver):
  try:
    print('trying to find')
    if WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'td[class="resale-item-action"] > span > a[title="Select"]'))):
      time.sleep(2)
      seats = driver.find_elements(By.CSS_SELECTOR, 'td[class="resale-item-action"] > span > a[title="Select"]')
      print(seats)
      for i in range(len(seats)):
        seat = driver.find_element(By.CSS_SELECTOR, 'td[class="resale-item-action"] > span > a[title="Select"]')
        seat.click()
      print('clicked 2')
      book = driver.find_element(By.CSS_SELECTOR, 'a[id="book"]')
      book.click()
      print('booked')
      return True
  except: return False


def click_rect_seat(driver, rect):
    width = int(rect.get_attribute('width'))
    height = int(rect.get_attribute('height'))
    forward_seat = None
    backward_seat = None

    try:
        forward_seat = driver.find_element(By.CSS_SELECTOR, f'rect[height="{height}"][width="{width+1}"][status="visible"]')
    except Exception as e:
        print(e)

    try:
        backward_seat = driver.find_element(By.CSS_SELECTOR, f'rect[height="{height}"][width="{width-1}"][status="visible"]')
    except Exception as e:
        print(e)

    print(forward_seat)
    print(backward_seat)

    if backward_seat:
        backward_seat.click()
        click_select_seat(driver)
        if click_rect_seat(driver, backward_seat):
            return True

    if forward_seat:
        forward_seat.click()
        click_select_seat(driver)
        if click_rect_seat(driver, forward_seat):
            return True

    if backward_seat or forward_seat:
        rect.click()
        return True

    return True



def process_rect_seats(driver):
    try:
        if WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'rect[status="visible"]'))):
            rects = driver.find_elements(By.CSS_SELECTOR, 'rect[status="visible"]')
            for rect in rects:
                if click_rect_seat(driver, rect):
                    return True
    except Exception as e:
        print(e)
        return None

    return False


def check_for_captcha(driver):
    try:
      if driver.find_element(By.CSS_SELECTOR, '#img_captcha'):
        captcha_src = driver.find_element(By.CSS_SELECTOR, '#img_captcha').get_attribute('src')
        print(captcha_src)
        result = solver.normal(CAPTCHA_URL + captcha_src)
        print(result)
        form_input_buttons = driver.find_element(By.CSS_SELECTOR, '#form_input_buttons')
        input_captcha = form_input_buttons.find_element(By.TAG_NAME, 'input')
        input_captcha.send_keys(result)
        submit_captcha = form_input_buttons.find_element(By.TAG_NAME, 'span')
        submit_captcha.click()
    except:
        return False
   

def click_select_seat(driver):
  try:
    if WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#add-selected-seat-to-cart'))):
      select = driver.find_element(By.CSS_SELECTOR, '#add-selected-seat-to-cart')
      select.click()
      
      return True
  except: return None


def click_buy_ticket(driver):
  try:
    if WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#add-to-cart'))):
      select = driver.find_element(By.CSS_SELECTOR, '#add-to-cart')
      select.click()
      return True
  except: return None


def move_and_click(driver, target):
    try:
        actions = ActionChains(driver)
        actions.move_to_element(target)
        actions.perform()
        time.sleep(1)
        actions.click()
        actions.perform()
    except Exception as e:
        print(e)

# #comparison-block-top > div.btn_go_step2_container > span
def get_seat_url(driver):
  try:
    if WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#comparison-block-top > div.btn_go_step2_container > span'))):
      seat_link = driver.find_element(By.CSS_SELECTOR, '#comparison-block-top > div.btn_go_step2_container > span > a').get_attribute('href')
      return seat_link
  except: return False   

# #collapsiblePanel_main_content_reservation > div > section.message.success
def get_success(driver):
  try:
    if WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#collapsiblePanel_main_content_reservation > div > section.message.success'))):
      success = driver.find_element(By.CSS_SELECTOR, '#collapsiblePanel_main_content_reservation > div > section.message.success')
      return success
  except: return False   

# div[class="seat_category_section"]
def get_data(driver):
  try:
    if WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class="seat_category_section"]'))):
      data = []
      sections = driver.find_elements(By.CSS_SELECTOR, 'div[class="seat_category_section"]')
      for section in sections:
        category = section.find_element(By.CSS_SELECTOR, 'p[class="semantic-no-styling-no-display description"]').text
        price = section.find_element(By.CSS_SELECTOR, 'td[class="unit_price"]').find_element(By.CSS_SELECTOR, 'span[class="amount amount_GBP "]').text
        print(price, category)
        data.append({"price": price, "category": category})
      return data
  except: return False   


def genhead():
        headers = {}
        headers["user-agent"]= ua()
        return headers


def ua():
        with open('uas') as ugs:
            uas = [x.strip() for x in ugs.readlines()]
            ugs.close()
        return choice(uas)

def send_cookies():
        cookies = driver.get_cookies()
        cookies_json = json.dumps(cookies)
        return cookies_json


def send_http(data):
    json_data = json.dumps(data)
    # Set the headers to specify the content type as JSON
    headers = {
        "Content-Type": "application/json"
    }

    # Send the POST request
    try:
        response = requests.post("http://localhost:5000/book", data=json_data, headers=headers)
        if response.status_code == 200:
            print("POST request successful!")
        else:
            raise Exception("POST request failed with status code: " + str(response.status_code))
    except Exception as e:
        print(e)
        with open('exception_log.txt', 'a') as file:
            file.write(str(e) + "\n")

def selenium_connect():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    #options.add_argument("--incognito")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-site-isolation-trials")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--lang=EN')
    #pergfan:6ofKZOXwL7qSTGNZ@proxy.packetstream.io:31112
    with open('proxies.txt', "r") as file:
        lines = file.readlines()

    random_line = choice(lines)
    random_line = random_line.strip()  # Remove leading/trailing whitespace and newline characters
    host, port, user, password = random_line.split(":")
    print("Host:", host)
    print("Port:", port)
    print("User:", user)
    print("Password:", password)
    proxy = (host, int(port), user, password)  # your proxy with auth, this one is obviously fake
    proxy_extension = ProxyExtension(*proxy)
    options.add_argument(f"--load-extension={proxy_extension.directory}")

    prefs = {"credentials_enable_service": False,
        "profile.password_manager_enabled": False}
    options.add_experimental_option("prefs", prefs)


    # Create the WebDriver with the configured ChromeOptions
    driver = webdriver.Chrome(
        driver_executable_path='./chromedriver.exe',
        options=options,
        enable_cdp_events=True,
        
    )
    driver.get(BASE_URL)
    return driver


def main(driver):

    while True:
        formatted_url = f"https://ticketresale.lancashirecricket.co.uk/list/resale/resaleProductCatalog.json?"

        try:
            response = requests.get(formatted_url, headers=headers, timeout=10)
            logging.info("Request successful. Status code: %d", response.status_code)
        except requests.exceptions.RequestException as e:
            logging.error("Request error: %s", str(e))
        except Exception as e:
            logging.exception("An unexpected error occurred: %s", str(e))
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Process the data as needed
                for el in data['topicWithProductsList'][0]['products']:
                    if el['availableQuantity'] > 1:
                        try:
                            page_path = el['productPagePath']
                            driver.get(BASE_URL + page_path)
                            check_for_captcha(driver)
                            if check_grouped_content(driver):
                                click_grouped_content(driver)
                                if check_simple_content(driver):
                                   click_simple_seats(driver)
                                   if get_success(driver):
                                    time.sleep(5)
                                    cookiee = send_cookies()
                                    data = get_data(driver)
                                    send_http({"url": "https://ticketresale.lancashirecricket.co.uk/cart/shoppingCart", "cookiee": cookiee, "data": data})
                            try:
                                area = get_area(driver)
                                move_and_click(driver, area)
                                seat_url = get_seat_url(driver)
                                clean_link = re.sub(r'&amp;', '', seat_url)
                                driver.get(clean_link)
                                process_rect_seats(driver)
                                click_select_seat(driver)
                                click_buy_ticket(driver)
                                if get_success(driver):
                                    time.sleep(5)
                                    cookiee = send_cookies()
                                    data = get_data(driver)
                                    send_http({"url": "https://ticketresale.lancashirecricket.co.uk/cart/shoppingCart", "cookiee": cookiee, "data": data})
                            except Exception as e:
                                print(e)
                        except Exception as e:
                            print(e)
                            # Save exception information to a text file
                            with open('exception_log.txt', 'a') as file:
                                file.write(str(e) + "\n")
            except Exception as e:
                with open('exception_log.txt', 'a') as file:
                    file.write(str(e) + "\n")
            time.sleep(1)
if __name__ == "__main__":
    driver = selenium_connect()
    main(driver)