"""
Functions for interacting with MongoDB.
"""

import os
import random
import urllib.parse

import pymongo
from bson import json_util
from bson.objectid import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Response
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from sentry_sdk import configure_scope

# Load dotenv in the base root refers to application_top
APP_ROOT = os.path.join(os.path.dirname(__file__), '..')
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

MONGO_CONN = os.getenv('MONGO_CONN')
MONGO_USER = os.getenv('MONGO_USER')
MONGO_PW = os.getenv('MONGO_PW')

# escape special characters in connection string
mongo_user = urllib.parse.quote_plus(MONGO_USER)
mongo_pw = urllib.parse.quote_plus(MONGO_PW)

# Create the connection string
uri = f"mongodb+srv://{mongo_user}:{mongo_pw}@{MONGO_CONN}"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Access a database and a collection
db = client.Images
collection = db.vite_demo_images

# Create a new router for MongoDB Routes
router_mongo = APIRouter()


@router_mongo.post("/add-sample-mongo")
async def add_sample_mongo():
    # Add a sample to the collection
    name = ["Dirk", "Sandy", "John", "Jane", "Joe", "Sally"]
    age = [20, 30, 40, 50, 60, 70]
    document = {"name": random.choice(name), "age": random.choice(age)}
    result = collectio2n.insert_one(document)
    print(result.inserted_id)
    return {"message": f"Mongo added id: {result.inserted_id}"}


@router_mongo.get(path="/get-image-mongo/{id}")
async def get_one_mongo(id: str):
    # Fetch one document from the collection
    result = collection.find_one({"_id": ObjectId(id)})
    return result


@router_mongo.get("/get-all-images-mongo")
async def get_all_images_mongo():
    # Get all documents from the collection
    with configure_scope() as scope:
        scope.set_transaction_name("Mongo Get All Images")
    documents = collection.find({})
    dict_cursor = [doc for doc in documents]
    for d in dict_cursor:
        d["id"] = str(d["_id"]) # swapping _id for id
        print(d)
    resp = json_util.dumps(dict_cursor, ensure_ascii=False)
    return Response(content=resp, media_type="application/json")

# @router_mongo.post("/mongo-add-image")


async def add_image_mongo(name: str, url: str, ai_labels: list, ai_text: list):
    # Add a image data to the collection
    with configure_scope() as scope:
        scope.set_transaction_name("Mongo Add Image")
    document = {"name": name, "url": url,
                "ai_labels": ai_labels, "ai_text": ai_text}
    result = collection.insert_one(document)
    print(result.inserted_id)
    return {"message": f"Mongo added id: {result.inserted_id}"}


@router_mongo.delete(path="/delete-all-mongo/{key}")
async def delete_all_mongo(key: str):
    # Delete all documents from the collection
    result = collection.delete_many({key: {"$exists": True}})
    return {"message": f"Mongo deleted {result.deleted_count} documents"}


@router_mongo.delete(path="/delete-one-mongo/{id}")
async def delete_one_mongo(id: str):
    # Delete one document from the collection
    with configure_scope() as scope:
        scope.set_transaction_name("Mongo Delete Image")

    result = collection.delete_one({"_id": ObjectId(id)})
    return {"message": f"Mongo deleted {result.deleted_count} documents"}
