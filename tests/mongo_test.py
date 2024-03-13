import os 
print(os.getcwd())

from unittest.mock import AsyncMock

import pytest

from src.mongo import *



@pytest.mark.asyncio
async def test_get_one_mongo(monkeypatch):
   
    # Call the async function and await its result
    result = await get_one_mongo("648b7444769c327f2a7cf0fe")

    # Assert that the result matches what we expect
    assert result == None
