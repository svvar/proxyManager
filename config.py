import os
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

SECRET_KEY = os.getenv("SECRET_KEY")
IP_INFO_KEY = os.getenv("IP_INFO_KEY")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
BOT_ADMINS = [int(x) for x in os.getenv("BOT_ADMINS").strip().strip(',').split(',')]