import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    MONGODB_URI = os.getenv("MONGODB_URI")
    DB_NAME = os.getenv("DB_NAME")

app_config = Config()

# MongoDB connection
client = MongoClient(app_config.MONGODB_URI)
db = client[app_config.DB_NAME]
users = db.users
rooms = db.rooms
fees = db.fees
mess_fee_reductions = db.mess_fee_reductions
