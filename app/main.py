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
from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Optional
import openai
import asyncio

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
    
from fastapi import FastAPI, Form
import openai

# app = FastAPI()
openai_key = os.getenv("OPENAI_KEY")

openai.api_key = openai_key

# assistant_id = "asst_fN899QQ5rTc3EG4KJka6lBpB"
assistant_id = "asst_MrxRdog7fMsiDSyONw0ECTBA"
@app.post("/chat/completionsm")
def query(input: str = Form(...)):
    # input="Points to remember regarding replicating features in Mobile and TV platforms"
    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(thread.id, role="user", content=input)
    run = openai.beta.threads.runs.create(thread.id, assistant_id=assistant_id)
    while True:
        status = openai.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if status.status == "completed":
            break
    messages = openai.beta.threads.messages.list(thread.id)
    return {"response": messages.data[0].content[0].text.value}




@app.post("/chat/completionsn")
async def universal_chat_handler(request: Request):
    print(request)
    print("📥 Method:", request.method)
    print("📥 URL:", request.url)
    print("📥 Headers:", dict(request.headers))

    # Try reading body as JSON
    try:
        body = await request.json()
        print("📥 JSON Body:", body)
    except Exception:
        # Try reading as form
        try:
            form = await request.form()
            print("📥 Form Data:", dict(form))
        except Exception:
            # Fallback to raw body
            body_bytes = await request.body()
            print("📥 Raw Body:", body_bytes.decode("utf-8"))
    try:
        content_type = request.headers.get("content-type", "")
        prompt = None

        if "application/json" in content_type:
            body = await request.json()
            if isinstance(body, dict):
                # Tavus-style: OpenAI format
                messages = body.get("messages")
                if messages and isinstance(messages, list):
                    prompt = next((m["content"] for m in messages if m.get("role") == "user"), None)
                else:
                    # Fallback for flat prompt
                    prompt = body.get("prompt") or body.get("input")

        elif "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            prompt = form.get("input") or form.get("prompt")

        elif "text/plain" in content_type:
            prompt = await request.body()
            prompt = prompt.decode("utf-8")

        else:
            # Try as JSON anyway
            try:
                body = await request.json()
                prompt = body.get("input") or body.get("prompt")
            except:
                pass

        if not prompt:
            return JSONResponse(status_code=400, content={"error": "No prompt found in request"})

        # Call OpenAI Assistant (or replace with RAG)
        thread = openai.beta.threads.create()
        openai.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt)
        run = openai.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)

        while True:
            status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if status.status == "completed":
                break
            await asyncio.sleep(0.5)

        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        response_text = messages.data[0].content[0].text.value

        return {
            "id": "chatcmpl-custom-001",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "custom-fastapi",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ]
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
import time

@app.post("/chat/completions")
async def rag_proxy(request: Request):
    body = await request.json()
    # 1. Create a thread
    thread = openai.beta.threads.create()

    # 2. Forward only user messages
    for m in body.get("messages", []):
        if m["role"] == "user":
            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=m["content"]
            )

    # 3. Kick off the run
    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    # 4. Wait for completion
    while True:
        status = openai.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if status.status == "completed":
            break
        await asyncio.sleep(0.5)

    # 5. Fetch the assistant’s reply
    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    reply = messages.data[-1].content[0].text.value

    # 6. Return in Tavus format
    return {
      "id": "chatcmpl-001",
      "object": "chat.completion",
      "created": int(time.time()),
      "model": "my_model",
      "choices": [{
        "index": 0,
        "message": {"role": "assistant", "content": reply},
        "finish_reason": "stop"
      }]
    }