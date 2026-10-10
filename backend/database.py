from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["nasha_mukti"]
users_collection = db["users"]
progress_collection = db["progress"]
rehab_centres_collection = db["rehab_centres"]