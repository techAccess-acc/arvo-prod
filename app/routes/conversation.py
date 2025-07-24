from fastapi import FastAPI, HTTPException
from app.services.tavus import post_to_tavus
from fastapi import APIRouter

router = APIRouter()

@router.get("/start-conversation")
async def start_conversation():
    payload = {
        "replica_id": "rfe12d8b9597",
        "persona_id": "pdced222244b"
    }

    try:
        data = await post_to_tavus("conversations", payload)
        conversation_url = data.get("conversation_url")

        if not conversation_url:
            raise HTTPException(status_code=500, detail="conversation_url not found")

        return {"conversation_url": conversation_url}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
