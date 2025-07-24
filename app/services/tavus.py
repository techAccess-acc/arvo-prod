import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TAVUS_API_KEY = os.getenv("TAVUS_KEY")
BASE_URL = "https://tavusapi.com/v2"

HEADERS = {
    "x-api-key": TAVUS_API_KEY,
    "Content-Type": "application/json"
}

async def post_to_tavus(endpoint: str, payload: dict) -> dict:
    url = f"{BASE_URL}/{endpoint}"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=HEADERS)

    if response.status_code not in [200, 201]:
        raise Exception(f"Request failed: {response.status_code} - {response.text}")

    return response.json()