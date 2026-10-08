import os

from pymongo import MongoClient


# Set MONGO_URL in the environment to use a hosted database. The local default
# lets the API start even when MongoDB is not configured yet.
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
conn = MongoClient(MONGO_URL)
