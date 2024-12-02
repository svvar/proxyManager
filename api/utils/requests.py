import os

import aiohttp
from aiohttp import ClientSession
import aiohttp_socks


IP_INFO_KEY = os.getenv('IP_INFO_KEY')


async def rotate_proxy(session: ClientSession, rotation_link: str):
    async with session.get(rotation_link, ssl=False, timeout=15) as response:
        if response.status == 200:
            return True


async def get_socks_proxy_ip(host: str, port: int, login: str, password: str, ip_version: int):
    connector = aiohttp_socks.ProxyConnector.from_url(f'socks5://{login}:{password}@{host}:{port}')
    link = 'http://v6.ipv6-test.com/api/myip.php?json' if ip_version == 6 else 'http://v4.ipv6-test.com/api/myip.php?json'

    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(link, ssl=False) as response:
            if response.status == 200:
                data = await response.json()
                return data['address']
            else:
                return None


async def get_http_proxy_ip(session: ClientSession, host: str, port: int, login: str, password: str, ip_version: int):
    link = 'http://v6.ipv6-test.com/api/myip.php?json' if ip_version == 6 else 'http://v4.ipv6-test.com/api/myip.php?json'

    async with session.get(link, ssl=False,
                           proxy=f'http://{login}:{password}@{host}:{port}') as response:
        if response.status == 200:
            data = await response.json()
            return data['address']
        else:
            return None


async def get_ip_info(session: ClientSession, ip: str):
    async with session.get(f'https://ipinfo.io/{ip}?token={IP_INFO_KEY}', ssl=False) as response:
        if response.status == 200:
            return await response.json()
        else:
            return None

