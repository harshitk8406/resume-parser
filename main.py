"""
FastAPI application entry point for the Resume Parser AI Agent.

Endpoints:
  GET  /           → Serves the frontend SPA
  POST /api/analyze → Accepts resume file upload or raw text, returns JSON analysis
  GET  /api/health  → Health check
"""

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent import analyze_resume, convert_resume
from converter import generate_docx
from models import ConvertedResumeData, ErrorResponse, ResumeAnalysisResponse
from parsers import extract_text

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Resume Parser AI Agent",
    description="AI-powered resume analysis using xAI Grok API — extracts skills, highlights, and ATS score.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow all origins in development; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the main frontend HTML page."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(str(index_path))


@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "provider": "Groq",
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "api_key_set": bool(os.getenv("GROQ_API_KEY")),
    }


@app.post(
    "/api/analyze",
    response_model=ResumeAnalysisResponse,
    tags=["Resume Analysis"],
    summary="Analyze a resume and return ATS score + skills + highlights",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input or unsupported file type"},
        422: {"model": ErrorResponse, "description": "AI parsing error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze(
    file: UploadFile = File(None, description="Resume file (PDF, DOCX, or TXT)"),
    text: str = Form(None, description="Raw resume text (alternative to file upload)"),
):
    """
    Analyze a resume using Grok AI.

    Accepts either:
    - A **file upload** (PDF, DOCX, TXT) via the `file` field, OR
    - **Raw text** pasted via the `text` field.

    Returns structured JSON with:
    - Candidate name & title
    - Extracted skills (technical, tools, soft skills, domain expertise)
    - Key highlights & achievements
    - ATS score (0–100) with dimensional breakdown
    - Improvement tips ordered by priority
    """
    start_time = time.perf_counter()

    # --- 1. Extract text from input ---
    resume_text = ""

    if file and file.filename:
        # File upload path
        logger.info("Received file upload: %s (size: %s bytes)", file.filename, file.size)
        try:
            file_bytes = await file.read()
            if not file_bytes:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            resume_text = extract_text(file.filename, file_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ImportError as e:
            raise HTTPException(status_code=500, detail=str(e))

    elif text and text.strip():
        # Plain text path
        logger.info("Received raw text input (%d characters).", len(text))
        resume_text = text.strip()

    else:
        raise HTTPException(
            status_code=400,
            detail="No input provided. Please upload a resume file (PDF/DOCX/TXT) or paste resume text.",
        )

    if len(resume_text) < 50:
        raise HTTPException(
            status_code=400,
            detail="Resume text is too short to analyze. Please provide a complete resume.",
        )

    # --- 2. Run AI analysis ---
    try:
        result = analyze_resume(resume_text)
    except ValueError as e:
        logger.error("Agent error: %s", e)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during resume analysis.")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

    elapsed = time.perf_counter() - start_time
    logger.info("Analysis completed in %.2fs | ATS Score: %d", elapsed, result.ats_score.overall)

    return result


# ---------------------------------------------------------------------------
# Resume Conversion endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/api/convert",
    tags=["Resume Conversion"],
    summary="Convert a resume to the HAIRAT template format and download as DOCX",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        422: {"model": ErrorResponse, "description": "AI conversion error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def convert(
    file: UploadFile = File(None, description="Resume file (PDF, DOCX, or TXT)"),
    text: str = Form(None, description="Raw resume text"),
):
    """
    Convert a resume to the HAIRAT template format and return a DOCX download.

    Accepts the same input as /api/analyze (file upload or raw text).
    Returns a downloadable .docx file in the template format.
    """
    start_time = time.perf_counter()

    # --- 1. Extract text ---
    resume_text = ""
    if file and file.filename:
        logger.info("Convert: received file '%s'", file.filename)
        try:
            file_bytes = await file.read()
            if not file_bytes:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            resume_text = extract_text(file.filename, file_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif text and text.strip():
        logger.info("Convert: received raw text (%d chars)", len(text))
        resume_text = text.strip()
    else:
        raise HTTPException(
            status_code=400,
            detail="No input provided. Please upload a resume file or paste resume text.",
        )

    if len(resume_text) < 50:
        raise HTTPException(status_code=400, detail="Resume text is too short.")

    # --- 2. AI conversion ---
    try:
        converted_data = convert_resume(resume_text)
    except ValueError as e:
        logger.error("Conversion agent error: %s", e)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during resume conversion.")
        raise HTTPException(status_code=500, detail=f"AI conversion failed: {str(e)}")

    # --- 3. Generate DOCX ---
    try:
        docx_bytes = generate_docx(converted_data)
    except Exception as e:
        logger.exception("DOCX generation error.")
        raise HTTPException(status_code=500, detail=f"DOCX generation failed: {str(e)}")

    candidate_name = converted_data.get("name", "Converted_Resume").replace(" ", "_")
    filename = f"{candidate_name}_Template.docx"

    elapsed = time.perf_counter() - start_time
    logger.info("Conversion completed in %.2fs — file: %s", elapsed, filename)

    import io
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )
