
import aiohttp
from aiohttp import ClientSession
import aiohttp_socks

from config import IP_INFO_KEY

async def rotate_proxy(session: ClientSession, rotation_link: str):
    async with session.get(rotation_link, ssl=False, timeout=20) as response:
        if response.status == 200:
            return True


async def get_socks_proxy_ip(host: str, port: int, login: str, password: str):
    connector = aiohttp_socks.ProxyConnector.from_url(f'socks5://{login}:{password}@{host}:{port}')
    link = 'https://api.my-ip.io/v2/ip.json'

    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get(link, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['ip'], int(data['type'][-1])
                else:
                    return None, None
        except Exception:
            return None, None


async def get_http_proxy_ip(session: ClientSession, host: str, port: int, login: str, password: str):
    link = 'https://api.my-ip.io/v2/ip.json'
    link = 'https://v4v6.ipv6-test.com/api/myip.php?json'

    try:
        async with session.get(link, ssl=False, timeout=55, proxy=f'http://{login}:{password}@{host}:{port}') as response:
            if response.status == 200:
                data = await response.json()
                return data['address'], int(data['proto'][-1])
            else:
                return None, None
    except Exception:
        return None, None



async def get_ip_info(session: ClientSession, ip: str):
    import dotenv
    dotenv.load_dotenv(r'D:\fun_project\proxyManager\.env')
    async with session.get(f'https://ipinfo.io/{ip}?token={IP_INFO_KEY}', ssl=False) as response:
        if response.status == 200:
            return await response.json()
        else:
            return None


async def get_http_proxy_ip_multitry(session: ClientSession, host: str, port: int, login: str, password: str):
    tasks = [get_http_proxy_ip(session, host, port, login, password) for _ in range(5)]
    try:
        for task in asyncio.as_completed(tasks, timeout=60):
            ip, ip_ver = await task
            if ip:
                return ip, ip_ver

        return None, None
    except asyncio.TimeoutError:
        return None, None



async def main():
    # async with ClientSession() as session:
    #     host = '91.234.3.73'
    #     port = 8561
    #     login = 'modem61'
    #     password = 'aXyuifM1'


    host = '91.234.3.73'
    port = 8555
    login = 'modem55'
    password = 'Xpvj1aWQ'

    ip, ip_ver = await get_http_proxy_ip_multitry(host, port, login, password)
    print(ip, ip_ver)

if __name__ == '__main__':
    # import requests as py_requests
    # import time
    # start_time = time.time()
    # response = py_requests.get('https://v4v6.ipv6-test.com/api/myip.php?json', proxies={'http': 'http://modem55:Xpvj1aWQ@91.234.3.73:8555'})
    # end_time = time.time()
    # print(response.json())
    # print(end_time - start_time)

    import asyncio
    asyncio.run(main())
