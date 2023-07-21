"""
Functions for interacting with Postgres.
"""

import os
from datetime import date
from typing import List, Optional

import psycopg2
from dotenv import load_dotenv
from fastapi import APIRouter, Response, encoders
from pydantic import BaseModel
from sentry_sdk import capture_exception, configure_scope

# Load dotenv in the base root refers to application_top
APP_ROOT = os.path.join(os.path.dirname(__file__), '..')
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

# Prep our environment variables / upload .env to Railway.app
DB = os.getenv('PGDATABASE')
HOST = os.getenv('PGHOST')
PORT = os.getenv('PGPORT')
USER = os.getenv('PGUSER')
PW = os.getenv('PGPASSWORD')

# Instantiate a Postgres connection
conn = psycopg2.connect(
    database=DB, user=USER, password=PW, host=HOST, port=PORT
)
# Create a new router for Postgres Routes
router_postgres = APIRouter()

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


@router_postgres.get("/get-image-postgres/{id}", response_model=ImageModel, response_model_exclude_unset=True)
async def get_image_postgres(id: int):
    """Fetches a single image from Postgres

    Args:
        image_id (int): The Image ID
        response_model (_type_, optional): Defaults to ImageModel.
    """
    SQL = "SELECT * FROM images WHERE id = %s"
    DATA = (id,)
    try:
        cur = conn.cursor()
        cur.execute(SQL, DATA)
        image = cur.fetchone()  # Just fetch the specific ID we need
        print(f"Fetched Image Postgres: {image[1]}")
        item = ImageModel(id=image[0], name=image[1], width=image[2], height=image[3], url=image[4],
                          url_resize=image[5], date_added=image[6], date_identified=image[7], ai_labels=image[8], ai_text=image[9])
        return item.dict()
    except Exception as err:
        capture_exception(err)


async def get_all_images_postgres(response_model=List[ImageModel]):
    """Fetches all images from Postgres.

    Args:
        response_model (_type_, optional): _description_. Defaults to List[ImageModel].

    Returns:
        list: The list of images from Postgres
    """
    with configure_scope() as scope:
        scope.set_transaction_name("Postgres Get All Images")

    try:
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
    except Exception as err:
        capture_exception(err)
    finally:
        cur.close()
    return formatted_photos


async def add_image_postgres(name: str, url: str, ai_labels: list, ai_text: list):
    """Adds an image & metadata to Postgres.

    Args:
        name (str): Name of the image
        url (str): S3 URL of the image
        ai_labels (list): Any labels identified by Amazon Rekognition
        ai_text (list): Any text identified by Amazon Rekognition
    """
    with configure_scope() as scope:
        scope.set_transaction_name("Postgres Add Image")

    cur = conn.cursor()
    # Note: don't be tempted to use string interpolation on the SQL string ...
    # have never gotten that to accept a List into a text[] or varchar[] Postgres column
    SQL = "INSERT INTO images (name, url, ai_labels, ai_text) VALUES (%s, %s, %s, %s)"
    DATA = (name, url, ai_labels, ai_text)

    # Attempt to write the image metadata to Postgres
    try:
        cur.execute(SQL, DATA)
        conn.commit()
    except Exception as err:
        conn.rollback()
        capture_exception(err)

    # Close the connection
    cur.close()


async def delete_image_postgres(id: int):
    """Deletes an image from Postgres.

    Args:
        id (int): ID of the image to delete
    """
    cur = conn.cursor()
    SQL = "DELETE FROM images WHERE id = %s"
    DATA = (id,)

    with configure_scope() as scope:
        scope.set_transaction_name("Postgres Delete Image")

    # Attempt to delete the image from Postgres
    try:
        cur.execute(SQL, DATA)
        conn.commit()
    except Exception as err:
        conn.rollback()
        capture_exception(err)

    # Close the connection
    cur.close()
