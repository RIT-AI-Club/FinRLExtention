import sys
import os
import asyncio
import json
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from pathlib import Path
import glob, traceback

from mcp_client import MCPClient, create_mcp_client
from generate_report import generate_report as _run_generate_report

PDF_OUTPUT_DIR = "reports"
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

# Resolved absolute path used for all security checks
PDF_OUTPUT_DIR_ABS = Path(PDF_OUTPUT_DIR).resolve()

# Maps job_id -> asyncio.Queue for SSE progress streaming.
_progress_queues: dict[str, asyncio.Queue] = {}

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


class GenerateReportRequest(BaseModel):
    ticker: str
    job_id: str | None = None


def _guard_client() -> MCPClient:
    """Return the MCP client or raise a 503 if startup failed."""
    if client is None:
        raise HTTPException(status_code=503, detail="MCP client not initialized — startup may have failed")
    return client


@app.get("/api/report/progress/{job_id}")
async def report_progress(job_id: str):
    """SSE stream that emits progress log messages while a report is being generated."""
    async def event_generator():
        deadline, waited = 10.0, 0.0
        while job_id not in _progress_queues:
            if waited >= deadline:
                yield 'data: {"done": true}\n\n'
                return
            await asyncio.sleep(0.1)
            waited += 0.1

        q = _progress_queues[job_id]
        try:
            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if item is None:
                    yield 'data: {"done": true}\n\n'
                    return
                yield f"data: {json.dumps(item)}\n\n"
        finally:
            _progress_queues.pop(job_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/report/generate")
async def generate_report_endpoint(req: GenerateReportRequest):
    """Run the generate_report pipeline directly for a given ticker."""
    mcp = _guard_client()
    ticker = req.ticker.strip().upper()

    q: asyncio.Queue | None = None
    if req.job_id:
        q = asyncio.Queue()
        _progress_queues[req.job_id] = q

    async def progress_callback(msg: str, level: str = "info"):
        if q is not None:
            await q.put({"msg": msg, "level": level})

    try:
        paths = await _run_generate_report(
            ticker=ticker,
            save_pdf=True,
            output_dir=PDF_OUTPUT_DIR_ABS,
            client=mcp,
            progress_callback=progress_callback,
        )
        return {
            "html_filename": paths["html"].name if "html" in paths else None,
            "pdf_filename": paths["pdf"].name if "pdf" in paths else None,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if q is not None:
            await q.put(None)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    mcp = _guard_client()
    try:
        reply = await mcp.process_message(req.message, req.history)
        return {"reply": reply}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/report/view/{filename}")
async def view_pdf(filename: str):
    """Serve a report PDF inline for embedded display in an iframe."""
    candidate = (PDF_OUTPUT_DIR_ABS / filename).resolve()
    if not str(candidate).startswith(str(PDF_OUTPUT_DIR_ABS) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(str(candidate), media_type="application/pdf")


@app.get("/api/report/html/{filename}")
async def serve_html(filename: str):
    """Serve a generated report HTML file directly in the browser."""
    candidate = (PDF_OUTPUT_DIR_ABS / filename).resolve()
    if not str(candidate).startswith(str(PDF_OUTPUT_DIR_ABS) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(str(candidate), media_type="text/html")


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
        glob.glob(f"{PDF_OUTPUT_DIR_ABS}/*.html"),
        key=os.path.getmtime,
        reverse=True,
    )
    return {"reports": [os.path.basename(f) for f in files]}