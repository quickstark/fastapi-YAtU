import json
import os
from unittest.mock import AsyncMock

import pytest

from src.mongo import *

print(os.getcwd())


@pytest.mark.asyncio
async def test_get_one_mongo(monkeypatch):

    # Call the async function and await its result
    response = await get_one_mongo("648b7444769c327f2a7cf0fe")

    assert isinstance(response, dict)
    expected_keys = {"name", "url", "ai_labels", "id"}
    assert expected_keys.issubset(response.keys())


@pytest.mark.asyncio
async def test_get_all_images_mongo(monkeypatch):
    # Call the async function and await its result
    response = await get_all_images_mongo()

    # Assert that the response is an instance of Response
    assert isinstance(response, Response)

    # Get the content of the response
    response_content = json.loads(response.body)

    # Assert that the response content is a list
    assert isinstance(response_content, list)

    # Check if the list contains dictionaries
    for item in response_content:
        assert isinstance(item, dict)
        expected_keys = {"name", "url", "ai_labels", "ai_text", "id"}
        assert expected_keys.issubset(item.keys())
