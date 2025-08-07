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
import time


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
    
@app.post("/chat/completionsk")
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

import os
import json
from fastapi import Request
from starlette.responses import StreamingResponse
from openai import OpenAI, AssistantEventHandler

# create a dedicated client for streaming completions
OPENAI_API_KEY = os.getenv("OPENAI_KEY")
stream_client = OpenAI(api_key=OPENAI_API_KEY)
# stream_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


#working normal chat completion bot
@app.post("/chat/completions")
async def chat_stream(request: Request):
    """
    A Server-Sent Events (SSE) endpoint that proxies to gpt-4o-mini with streaming.
    """
    # 1. parse incoming messages
    body = await request.json()
    messages = body.get("messages", [])

    # 2. generator that yields SSE data frames
    def event_generator():
        stream = stream_client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=messages, 
            stream=True
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                print("🔹 chunk:", delta.content)  

                payload = {"choices":[{"delta":{"content": delta.content}}]}
                # SSE format: "data: <json>\n\n"
                yield f"data: {json.dumps(payload)}\n\n"
        # signal completion
        yield "data: [DONE]\n\n"

    # 3. return an event stream
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/chat/completionsm-stream")
async def chat_stream(request: Request):
    """
    A Server-Sent Events (SSE) endpoint that converts form input to streaming chat completions.
    """
    # 1. Parse incoming form data or JSON
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        # Handle JSON request (like your reference endpoint)
        body = await request.json()
        user_input = body.get("input", "")
        # You can also accept messages array if needed
        messages = body.get("messages", [])
        if not messages and user_input:
            messages = [{"role": "user", "content": user_input}]
    else:
        # Handle form data (like your existing endpoint)
        form_data = await request.form()
        user_input = form_data.get("input", "")
        messages = [{"role": "user", "content": user_input}]
    
    if not messages:
        # Return error in SSE format
        def error_generator():
            error_payload = {"error": "No input provided"}
            yield f"data: {json.dumps(error_payload)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
    
    # 2. Generator that yields SSE data frames
    def event_generator():
        try:
            stream = stream_client.chat.completions.create(
                model="gpt-4o-mini",  # or your preferred model
                messages=messages,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        print("🔹 chunk:", delta.content)
                        payload = {"choices": [{"delta": {"content": delta.content}}]}
                        # SSE format: "data: <json>\n\n"
                        yield f"data: {json.dumps(payload)}\n\n"
            
            # Signal completion
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            # Handle errors in streaming format
            error_payload = {"error": str(e)}
            yield f"data: {json.dumps(error_payload)}\n\n"
            yield "data: [DONE]\n\n"
    
    # 3. Return an event stream with proper headers
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control"
    }
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers=headers
    )

# Optional: Keep your original non-streaming endpoint for backwards compatibility
@app.post("/chat/completions-sync")
def query_sync(input: str = Form(...)):
    """
    Non-streaming version that returns complete response
    """
    try:
        response = stream_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": input}]
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}
    

#working assitant with RAG
@app.post("/RAG/chat/completions")
async def chat_stream(request: Request):
    """
    A Server-Sent Events (SSE) endpoint that uses OpenAI Assistant with knowledge base
    and converts the response to streaming format.
    """
    # 1. Parse incoming form data or JSON
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        body = await request.json()
        user_input = body.get("input", "")
        messages = body.get("messages", [])
        if not messages and user_input:
            user_input = messages[-1].get("content", "") if messages else user_input
        elif messages:
            user_input = messages[-1].get("content", "") if messages else ""
    else:
        form_data = await request.form()
        user_input = form_data.get("input", "")
    
    if not user_input:
        def error_generator():
            error_payload = {"error": "No input provided"}
            yield f"data: {json.dumps(error_payload)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
    
    # 2. Generator that simulates streaming from Assistant API
    def event_generator():
        try:
            # Create thread and message (similar to your original code)
            thread = stream_client.beta.threads.create()
            stream_client.beta.threads.messages.create(
                thread.id, 
                role="user", 
                content=user_input
            )
            
            # Create run with streaming enabled
            run = stream_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant_id,
                stream=True  # Enable streaming for Assistant API
            )
            
            # Stream the response
            for event in run:
                if event.event == 'thread.message.delta':
                    if hasattr(event.data, 'delta') and hasattr(event.data.delta, 'content'):
                        for content_delta in event.data.delta.content:
                            if hasattr(content_delta, 'text') and hasattr(content_delta.text, 'value'):
                                chunk_text = content_delta.text.value
                                if chunk_text:
                                    print("🔹 chunk:", chunk_text)
                                    payload = {"choices": [{"delta": {"content": chunk_text}}]}
                                    yield f"data: {json.dumps(payload)}\n\n"
                
                elif event.event == 'thread.run.completed':
                    break
                elif event.event == 'thread.run.failed':
                    error_payload = {"error": "Assistant run failed"}
                    yield f"data: {json.dumps(error_payload)}\n\n"
                    break
            
            # Signal completion
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"Error: {e}")
            # Fallback: if streaming fails, get the complete response and simulate streaming
            try:
                thread = stream_client.beta.threads.create()
                stream_client.beta.threads.messages.create(thread.id, role="user", content=user_input)
                run = stream_client.beta.threads.runs.create(thread.id, assistant_id=assistant_id)
                
                # Poll for completion
                while True:
                    status = stream_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                    if status.status == "completed":
                        break
                    elif status.status == "failed":
                        error_payload = {"error": "Assistant run failed"}
                        yield f"data: {json.dumps(error_payload)}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    # Small delay to avoid overwhelming the API
                    import time
                    time.sleep(0.5)
                
                # Get the response and simulate streaming by chunking it
                messages = stream_client.beta.threads.messages.list(thread.id)
                response_text = messages.data[0].content[0].text.value
                
                # Simulate streaming by sending chunks
                chunk_size = 10  # Adjust chunk size as needed
                words = response_text.split()
                
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i + chunk_size])
                    if i + chunk_size < len(words):
                        chunk += " "  # Add space except for last chunk
                    
                    payload = {"choices": [{"delta": {"content": chunk}}]}
                    yield f"data: {json.dumps(payload)}\n\n"
                    
                    # Small delay to simulate natural streaming
                    import time
                    time.sleep(0.1)
                
                yield "data: [DONE]\n\n"
                
            except Exception as fallback_error:
                error_payload = {"error": f"Failed to get response: {str(fallback_error)}"}
                yield f"data: {json.dumps(error_payload)}\n\n"
                yield "data: [DONE]\n\n"
    
    # 3. Return an event stream with proper headers
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control"
    }
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers=headers
    )

# Alternative approach: Extract knowledge and use Chat Completions
@app.post("/chat/completions-with-context")
async def chat_with_context(request: Request):
    """
    Alternative: Get context from assistant's knowledge base and use Chat Completions API
    This requires you to have access to the knowledge base content
    """
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        body = await request.json()
        user_input = body.get("input", "")
    else:
        form_data = await request.form()
        user_input = form_data.get("input", "")
    
    def event_generator():
        try:
            # You would need to implement this based on your knowledge base
            # This is just an example structure
            context = get_relevant_context(user_input)  # You'd implement this
            
            messages = [
                {"role": "system", "content": f"You are an assistant with access to this knowledge base: {context}"},
                {"role": "user", "content": user_input}
            ]
            
            stream = stream_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        payload = {"choices": [{"delta": {"content": delta.content}}]}
                        yield f"data: {json.dumps(payload)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            error_payload = {"error": str(e)}
            yield f"data: {json.dumps(error_payload)}\n\n"
            yield "data: [DONE]\n\n"
    
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control"
    }
    
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

def get_relevant_context(query: str) -> str:
    """
    Implement this function to retrieve relevant context from your knowledge base
    This could involve:
    1. Vector search through your documents
    2. Keyword matching
    3. Using OpenAI embeddings to find relevant chunks
    """
    # Placeholder - implement based on your knowledge base structure
    return "Your relevant context here..."