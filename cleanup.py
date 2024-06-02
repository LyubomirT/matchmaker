# cleanup.py
import os
from pymongo import MongoClient

mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['matchmakerdb']

def cleanup_database():
    collections = db.list_collection_names()
    for collection in collections:
        db[collection].delete_many({})

if __name__ == "__main__":
    cleanup_database()
    print("Database cleaned up successfully.")
