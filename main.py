from datetime import date
from typing import List, Optional
import os
from dotenv import load_dotenv
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(debug=True)

load_dotenv()
DB = os.getenv('PGDATABASE')
HOST= os.getenv('PGHOST')
PORT = os.getenv('PGPORT')
USER = os.getenv('PGUSER')
PW = os.getenv('PGPASSWORD')

class Msg(BaseModel):
    msg: str

class ImageModel(BaseModel):
    id: int
    name: str
    width: Optional[int]
    height: Optional[int]
    url: Optional[str]
    url_resize: Optional[str]
    date_added: Optional[date]
    date_identified: Optional[date]

@app.get("/images", response_model=List[ImageModel])
async def get_all_images():
    #Connect to Postgres
    conn = psycopg2.connect(
        database=DB, user=USER, password=PW, host=HOST, port=PORT
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM images ORDER BY id DESC")
    rows = cur.fetchall()

    formatted_photos = []
    for row in rows:
        formatted_photos.append(
            ImageModel(
                id=row[0], name=row[1], width=row[2], height=row[3], url=row[4], url_resize=row[5], date_added=row[6], date_identified=row[7]
            )
        )

    cur.close()
    conn.close()
    return formatted_photos

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
