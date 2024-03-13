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

    assert isinstance(response, list)
    expected_keys = {"name", "url", "ai_labels", "id"}
    assert expected_keys.issubset(response.keys())
