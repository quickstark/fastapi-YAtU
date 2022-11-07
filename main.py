import imp
import os
from datetime import date
from re import S
from typing import List, Optional

import boto3
import psycopg2
import sentry_sdk
# Configure the client
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentry_sdk import capture_exception, configure_scope

# Prep our environment variables / upload .env to Railway.app
# (or create manually in the FastAPI Railway settings)
load_dotenv()
DB = os.getenv('PGDATABASE')
HOST = os.getenv('PGHOST')
PORT = os.getenv('PGPORT')
USER = os.getenv('PGUSER')
PW = os.getenv('PGPASSWORD')
AWS_KEY = os.getenv('AMAZON_KEY_ID')
AWS_SECRET = os.getenv('AMAZON_KEY_SECRET')
AWS_BUCKET = os.getenv('AMAZON_S3_BUCKET')

# Instantiate an AWS Session (orthogonal to Client and Resource)
AWS_SESSION = boto3.Session(
    region_name="us-east-2",
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET
)

# Instantiate the Sentry SDK using DSN
SENTRY_DSN = os.getenv('FASTAPI_SENTRY_DSN')
sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=1.0,
)

origins = [
    "http://localhost",
    "https://quickstark-vite-images.up.railway.app/",
]

app = FastAPI(debug=True)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

# define Python user-defined exceptions


class SentryError(Exception):
    """Base class for custom Sentry exceptions"""
    pass


class Msg(BaseModel):
    msg: str

# Extend an ImageModel from pydantic BaseModel


class ImageModel(BaseModel):
    id: int
    name: str
    width: Optional[int]
    height: Optional[int]
    url: Optional[str]
    url_resize: Optional[str]
    date_added: Optional[date]
    date_identified: Optional[date]
    ai_labels: Optional[list]
    ai_text: Optional[list]


@app.get("/images", response_model=List[ImageModel])
async def get_all_images():

    # Connect to Postgres
    conn = psycopg2.connect(
        database=DB, user=USER, password=PW, host=HOST, port=PORT
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM images ORDER BY id DESC")
    images = cur.fetchall()

    formatted_photos = []
    for image in images:
        formatted_photos.append(
            ImageModel(
                id=image[0], name=image[1], width=image[2], height=image[3], url=image[4], url_resize=image[
                    5], date_added=image[6], date_identified=image[7], ai_labels=image[8], ai_text=image[9]
            )
        )

    cur.close()
    conn.close()
    return formatted_photos


@app.post("/add_image", status_code=201)
async def add_photo(file: UploadFile):
    print(f"Upload File Endpoint ${file.filename} - ${file.content_type}")

    # Create an S3 Client from our authenticated AWS Session
    awsclient = AWS_SESSION.resource("s3",)
    bucket = awsclient.Bucket(AWS_BUCKET)
    bucket.upload_fileobj(file.file, file.filename)

    uploaded_file_url = f"https://{AWS_BUCKET}.s3.amazonaws.com/{file.filename}"

    amzlabels, amztext, amzmods = amazon_detection(file)

    if any('Suggestive'.casefold() or 'Underwear'.casefold() or 'Revealing'.casefold() in text.casefold() for text in amzmods):
        return {"message": f"file.name may contain questionable content. Let's keep it family friendly. ;-)"}

    # Case insensitive check to see if the image contained the word "error"
    if any('Error'.casefold() or 'Errors'.casefold() in text.casefold() for text in amztext):
        print("Yes, we have Error Text!")
        try:
            error_message = f"Image Text Error - {' '.join(amztext)}"
            raise Exception(error_message)
        except Exception as err:
            capture_exception(err)
            print(err)

    # Case insensitive check to see if the image is a Bug or Insect
    if any('Bug'.casefold() or 'Insect'.casefold() in text.casefold() for text in amzlabels):
        print("Yes, we have Bug!")
        try:
            error_message = f"Image Bug - {' '.join(amzlabels)}"
            raise Exception(error_message)
        except Exception as err:
            capture_exception(err)
            print(err)

    # Store the returned S3 URL in Postgres
    conn = psycopg2.connect(
        database=DB, user=USER, password=PW, host=HOST, port=PORT
    )
    cur = conn.cursor()
    # Note: don't be tempted to use string interpolation on the SQL string ...
    # have never gotten that to accept a List into a text[] or varchar[] Postgres column
    SQL = "INSERT INTO images (name, url, ai_labels, ai_text) VALUES (%s, %s, %s, %s)"
    DATA = (file.filename, uploaded_file_url, amzlabels, amztext)
    cur.execute(SQL, DATA)
    conn.commit()
    cur.close()
    conn.close()


@app.delete("/delete_image/{id}", status_code=201)
async def delete_photo(id):
    print(f"Delete File {id}")

    # Delete the associated file information from Postgres
    conn = psycopg2.connect(
        database=DB, user=USER, password=PW, host=HOST, port=PORT
    )

    # Note: don't be tempted to use string interpolation on the SQL string ...
    # have never gotten that to accept a List into a text[] or varchar[] Postgres column

    # Fetch the Image ID (remember, "DATA" needs to be a tuple)
    SQL = "SELECT * FROM images WHERE id = %s"
    DATA = (id,)
    cur = conn.cursor()
    cur.execute(SQL, DATA)
    image = cur.fetchone()  # Just fetch the specific ID we need
    print(f"Fetched Image Postgres: {image}")

    # Now delete the File
    SQL = "DELETE FROM images WHERE id = %s"
    cur.execute(SQL, DATA)
    print(f"Deleted Image from Postgres")
    conn.commit()
    cur.close()
    conn.close()

    # Create an S3 Client from our authenticated AWS Session
    # Use to delete our S3 file using the filename
    awsclient = AWS_SESSION.client("s3",)
    response = awsclient.delete_object(Bucket=AWS_BUCKET, Key=image[1])
    print(f"Amazon Deletion {response}")


@app.get("/")
async def root():
    return {"message": "API Root. Welcome to FastAPI!"}


@app.get("/path")
async def demo_get():
    return {"message": "This is /path endpoint, use a post request to transform the text to uppercase"}


@app.post("/path")
async def demo_post(inp: Msg):
    return {"message": inp.msg.upper()}


@app.get("/path/{path_id}")
async def demo_get_path_id(path_id: int):
    return {"message": f"This is /path/{path_id} endpoint, use post request to retrieve result"}


def amazon_detection(file):
    awsclient = AWS_SESSION.client("rekognition")
    detect_labels_res = awsclient.detect_labels(
        Image={'S3Object': {'Bucket': AWS_BUCKET, 'Name': file.filename}})
    detect_text_res = awsclient.detect_text(
        Image={'S3Object': {'Bucket': AWS_BUCKET, 'Name': file.filename}})
    detect_moderation_res = awsclient.detect_moderation_labels(
        Image={'S3Object': {'Bucket': AWS_BUCKET, 'Name': file.filename}})

    detect_moderation_list = []
    for label in detect_moderation_res["ModerationLabels"]:
        if label["Confidence"] > 50:
            detect_moderation_list.append(label["Name"])

    detect_labels_list = []
    for label in detect_labels_res["Labels"]:
        if label["Confidence"] > 80:
            detect_labels_list.append(label["Name"])

    detect_text_list = []
    for text in detect_text_res['TextDetections']:
        if text["Type"] == "LINE" and text["Confidence"] > 80:
            detect_text_list.append(text["DetectedText"])

    detect_modified_labels = list(
        map(lambda x: x.replace('Insect', 'Bug'), detect_labels_list))

    print(detect_modified_labels)
    print(detect_text_list)
    print(detect_moderation_list)

    return detect_labels_list, detect_text_list, detect_moderation_list
