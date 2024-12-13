import asyncio
import time

from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from database.operations.bot_operations import get_ports, get_sellers_ports
from database.operations.website_sync_operations import upsert_update_ports, deactivate_ports


async def glweb_synchronize(seller_id: int, geo_id: int, site_login: str, site_password: str):
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor() as executor:
        list_of_ports = await loop.run_in_executor(executor, extract_ports, site_login, site_password)

    for port in list_of_ports:
        port['geo_id'] = geo_id

    db_ports_before = await get_sellers_ports(seller_id=seller_id)
    db_port_ids_before = set([port.port_id for port in db_ports_before])

    affected_port_ids = await upsert_update_ports(seller_id=seller_id, ports=list_of_ports)
    # print("UPDATED/INSTRTEDDDD")
    affected_port_ids = set(affected_port_ids)

    to_deavtivate_ids = db_port_ids_before - affected_port_ids

    await deactivate_ports(seller_id=1, port_ids=list(to_deavtivate_ids))
    # print("DEACTIVATEEDD")


def extract_ports(site_login: str, site_password: str):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://glweb.studio/login/")

    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/form/div[2]/div[1]/input")))

    login_input = driver.find_element(By.XPATH, "/html/body/div[2]/form/div[2]/div[1]/input")
    password_input = driver.find_element(By.XPATH, "/html/body/div[2]/form/div[2]/div[2]/input")

    login_input.send_keys(site_login)
    password_input.send_keys(site_password)

    submit_button = driver.find_element(By.XPATH, "/html/body/div[2]/form/div[4]/button")
    submit_button.click()

    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="select-proxy"]')))
    time.sleep(1)

    elements = driver.find_elements(By.CLASS_NAME, 'myproxy__block')
    list_of_ports = []

    for element in elements:
        soup = BeautifulSoup(element.get_attribute('innerHTML'), 'html.parser')
        div1 = soup.find('div', class_='myproxy__descr-port')
        div2 = soup.find('div', class_='myproxy__descr-login')
        div3 = soup.find('div', class_='myproxy__descr-link')
        div4 = soup.find('div', class_='myproxy__descr-end-date')

        spans1 = div1.find_all('span')
        if not spans1:
            continue
        host = spans1[0].text
        socks_port = int(spans1[1].text.split()[-1])
        http_port = int(spans1[2].text.split()[-1])

        spans2 = div2.find_all('span')
        login = spans2[0].text
        password = spans2[1].text
        rotation_link = div3.find('a').get('href')
        rent_end = div4.find('span').text

        rent_end = datetime.strptime(rent_end, "%d %b %y в %H:%M")

        list_of_ports.append({
            'host': host,
            'http_port': http_port,
            'socks_port': socks_port,
            'login': login,
            'password': password,
            'rotation_link': rotation_link,
            'rent_end': rent_end
        })

    driver.quit()
    return list_of_ports


def parse_custom_datetime(date_str):
    format_str = "%d %b %y в %H:%M"
    try:
        parsed_date = datetime.strptime(date_str, format_str)
        return parsed_date
    except ValueError as e:
        raise ValueError(f"Error parsing date '{date_str}': {e}")


if __name__ == '__main__':
    import asyncio
    asyncio.run(glweb_synchronize(1, 1, 'smaxim02', 'Artanden123'))
#
