from fastapi import FastAPI,HTTPException
from app.routes import user,conversation # Import your user routes
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv
from app.services.tavus import post_to_tavus
from fastapi.responses import Response

load_dotenv() 

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
tavus_key = os.getenv("TAVUS_KEY")

# Register routes
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(conversation.router, prefix="/api", tags=["API"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/assets/js",
    StaticFiles(directory=os.path.join("app/assets/js")),
    name="js"
)

app.mount(
    "/assets/css",
    StaticFiles(directory=os.path.join("app/assets/css")),
    name="css"
)

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def root():
    return {"message": "API is alive and kicking 💥"}

@app.get("/web", response_class=HTMLResponse)
def serve_html(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/file/widget.js")
async def dynamic_widget(request: Request):
    payload = {
        "replica_id": "rfe12d8b9597",
        "persona_id": "pdced222244b",
        "properties": {
            "max_call_duration": 600,
            "participant_left_timeout": 60,
            "participant_absent_timeout": 300
        }
    }

    try:
        data = await post_to_tavus("conversations", payload)
        conversation_url = data.get("conversation_url")

        if not conversation_url:
            raise HTTPException(status_code=500, detail="conversation_url not found")

        content = templates.get_template("widget.js.jinja").render({
            "conversation_url": conversation_url
        })

        return Response(content, media_type="application/javascript", headers={
            "Cache-Control": "no-store"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
