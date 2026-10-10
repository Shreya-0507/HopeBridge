import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)

db = client["nasha_mukti"]

users_collection = db["users"]

progress_collection = db["progress"]

rehab_centres_collection = db["rehab_centres"]