# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from .routes import extraction_routes
from .core.config import settings

from backend.services.retrieval_handler import RetrievalHandler

app = FastAPI(
    title="PDF Extraction Service",
    description="Advanced PDF extraction with image and text processing",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
templates = Jinja2Templates(directory="frontend/templates")

# Include routes
app.include_router(extraction_routes.router, prefix="/api/v1")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""

    # Initialize handlers
    retrieval_handler = RetrievalHandler()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

# Root route for serving the frontend


@app.get("/")
async def serve_frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
