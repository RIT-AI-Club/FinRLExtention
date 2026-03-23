# app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os, glob

from mcp_client import MCPClient

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

PDF_OUTPUT_DIR = "reports"
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(req: ChatRequest):
    files_before = set(glob.glob(f"{PDF_OUTPUT_DIR}/*.pdf"))
    try:
        reply = await MCPClient.process_message(req.message)
        
        # Detect if a new PDF was created
        files_after = set(glob.glob(f"{PDF_OUTPUT_DIR}/*.pdf"))
        new_files = files_after - files_before
        pdf_filename = os.path.basename(max(new_files, key=os.path.getmtime)) if new_files else None

        return { "reply": reply, "pdf_filename": pdf_filename }
    except Exception as e:
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