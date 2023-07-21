"""
OpenAI API functions
"""

import os

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import JSONResponse

import openai

# Load dotenv in the base root refers to application_top
APP_ROOT = os.path.join(os.path.dirname(__file__), '..')
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

OPENAI = os.getenv('OPENAI')
openai.api_key = OPENAI

# Create a new router for OpenAI Routes
router_openai = APIRouter()

@router_openai.get("/openai-hello")
async def openai_hello():
    """OpenAI Fetch Account Info

    Returns:
        Dict: Account Information
    """

    return {"message": "You've reached the OpenAI endpoint"}

@router_openai.get("/openai-gen-image/{search}")
async def openai_gen_image(search: str): 
    print(OPENAI)
    response = openai.Image.create(
        prompt=search,
        n=1,
        size="512x512"
    )
    image_url = response['data'][0]['url']
    return image_url