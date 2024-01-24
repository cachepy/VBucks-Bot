import os
from dotenv.main import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
SELLER_KEY = os.getenv("SELLER_KEY")
EMAIL = os.getenv("MAIL_ID")
SECRET_ID = os.getenv("SECRET_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
KEYAUTH = os.getenv("KEYAUTH")