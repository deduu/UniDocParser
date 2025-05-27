# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

# Import the settings object to ensure directories are created
from .core.config import settings  # Add this line
from .routes import extraction_routes

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
# The 'outputs' directory will now exist due to the settings import above
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")
templates = Jinja2Templates(directory="frontend/templates")

# Include routes
app.include_router(extraction_routes.router, prefix="/api/v1")

# Root route for serving the frontend
@app.get("/")
async def serve_frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})