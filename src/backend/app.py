import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import glob, traceback

from mcp_client import MCPClient, create_mcp_client  # your file

PDF_OUTPUT_DIR = "reports"
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

# ── Initialize client once when server starts ──────────────────────────────
client: MCPClient = None

@asynccontextmanager
async def lifespan(app):
    global client
    client = await create_mcp_client()  # loads config, connects servers, discovers tools
    yield
    await client.close()  # clean shutdown

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # [{ "role": "user"|"ai", "content": "..." }]

@app.post("/api/chat")
async def chat(req: ChatRequest):
    files_before = set(glob.glob(f"{PDF_OUTPUT_DIR}/*.pdf"))
    try:
        reply = await client.process_message(req.message, req.history)

        files_after = set(glob.glob(f"{PDF_OUTPUT_DIR}/*.pdf"))
        new_files = files_after - files_before
        pdf_filename = os.path.basename(max(new_files, key=os.path.getmtime)) if new_files else None

        return { "reply": reply, "pdf_filename": pdf_filename }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report/download/{filename}")
async def download(filename: str):
    path = os.path.join(PDF_OUTPUT_DIR, os.path.basename(filename))
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)

@app.get("/api/reports")
async def list_reports():
    files = sorted(glob.glob(f"{PDF_OUTPUT_DIR}/*.pdf"), key=os.path.getmtime, reverse=True)
    return { "reports": [os.path.basename(f) for f in files] }