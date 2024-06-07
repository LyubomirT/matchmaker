import os
from pymongo import MongoClient
import dotenv

# Load environment variables
dotenv.load_dotenv()

# MongoDB setup
mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['matchmakerdb']