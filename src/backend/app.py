import sys
import os
import re
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from pathlib import Path
import glob, traceback

from mcp_client import MCPClient, create_mcp_client
from generate_report import generate_report as _run_generate_report

_REPORT_KEYWORDS = frozenset(['report', 'generate', 'analyze', 'analysis', 'create'])


def _detect_report_ticker(message: str) -> str | None:
    """Return uppercase ticker if the message is a report generation request, else None."""
    lower = message.lower()
    if not any(kw in lower for kw in _REPORT_KEYWORDS):
        return None
    match = re.search(r'\b([A-Z]{2,5})\b', message)
    return match.group(1) if match else None

PDF_OUTPUT_DIR = "reports"
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

# Resolved absolute path used for all security checks
PDF_OUTPUT_DIR_ABS = Path(PDF_OUTPUT_DIR).resolve()

client: MCPClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = await create_mcp_client()  # loads config, inits Gemini, connects servers, discovers tools
    yield
    await client.close()


app = FastAPI(lifespan=lifespan)

# Use an env var so the frontend URL is not hardcoded for deployments
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    # history contains only PRIOR turns — the current message must NOT be included.
    # Each entry: {"role": "user"|"ai", "content": "..."}
    history: list[dict] = []


def _guard_client() -> MCPClient:
    """Return the MCP client or raise a 503 if startup failed."""
    if client is None:
        raise HTTPException(status_code=503, detail="MCP client not initialized — startup may have failed")
    return client


@app.post("/api/chat")
async def chat(req: ChatRequest):
    mcp = _guard_client()

    ticker = _detect_report_ticker(req.message)
    if ticker:
        try:
            paths = await _run_generate_report(
                ticker=ticker,
                save_pdf=True,
                output_dir=PDF_OUTPUT_DIR_ABS,
                client=mcp,
            )
            pdf_filename = paths["pdf"].name if "pdf" in paths else None
            return {
                "reply": f"Report for {ticker} has been generated.",
                "pdf_filename": pdf_filename,
            }
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    # Non-report chat: use the Gemini agentic loop and detect any incidentally generated PDFs.
    files_before = {p: os.path.getmtime(p) for p in glob.glob(f"{PDF_OUTPUT_DIR_ABS}/*.pdf")}
    try:
        reply = await mcp.process_message(req.message, req.history)

        files_after = set(glob.glob(f"{PDF_OUTPUT_DIR_ABS}/*.pdf"))
        new_files = [p for p in files_after if p not in files_before]
        pdf_filename: str | None = None
        if new_files:
            pdf_filename = os.path.basename(max(new_files, key=os.path.getmtime))

        return {"reply": reply, "pdf_filename": pdf_filename}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/report/download/{filename}")
async def download(filename: str):
    """
    Serve a report PDF.

    The filename is validated against the resolved output directory to prevent
    path traversal attacks (e.g. '../../etc/passwd').
    """
    # Resolve the candidate path and verify it stays inside PDF_OUTPUT_DIR_ABS
    candidate = (PDF_OUTPUT_DIR_ABS / filename).resolve()
    if not str(candidate).startswith(str(PDF_OUTPUT_DIR_ABS) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(str(candidate), media_type="application/pdf", filename=filename)


@app.get("/api/reports")
async def list_reports():
    files = sorted(
        glob.glob(f"{PDF_OUTPUT_DIR_ABS}/*.pdf"),
        key=os.path.getmtime,
        reverse=True,
    )
    return {"reports": [os.path.basename(f) for f in files]}