# main.py
import logging
import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Assuming your backend structure
from backend.routes import extraction_routes
from backend.core.config import settings
from backend.utils.logger import configure_logging

# Configure logging early
configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the startup and shutdown events for the FastAPI application.
    This is where you'd typically initialize and clean up resources like
    database connections or external services.
    """
    logger.info("Application startup begins...")
    try:
        # --- Add any startup logic here ---
        # For your current 'PDF Extraction Service', you might not have
        # complex services to initialize yet, unlike the example pattern.
        # However, if you add database connections, AI model loading, etc.,
        # this is where they would go.

        # Example: if you had a database connection pool
        # app.state.db_pool = await initialize_database_pool(settings.DATABASE_URL)
        # logger.info("Database connection pool initialized.")

        logger.info("Application startup complete.")
        yield  # The application will now run
    except Exception as e:
        logger.critical(
            f"Fatal error during application startup: {e}", exc_info=True)
        # Re-raise to prevent the application from starting if initialization fails
        raise
    finally:
        logger.info("Application shutdown begins...")
        # --- Add any shutdown logic here ---
        # Example: if you initialized a database pool
        # if hasattr(app.state, 'db_pool') and app.state.db_pool:
        #     await app.state.db_pool.close()
        #     logger.info("Database connection pool closed.")

        logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application instance.
    This function handles all application-level setup, including
    middleware, static files, templates, and routes.
    """
    app = FastAPI(
        title="PDF Extraction Service",
        description="Advanced PDF extraction with image and text processing",
        version="1.0.0",
        lifespan=lifespan  # Attach the lifespan context manager
    )

    # --- CORS Middleware ---
    # Moved inside create_app as it's part of the app's configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Be more specific in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Mount static files and templates ---
    # Ensure these paths are correct relative to where main.py is run
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
    app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

    # Store templates in app.state for easier access in routes
    templates = Jinja2Templates(directory="frontend/templates")
    app.state.templates = templates  # Important: attach to app.state

    # --- Include routes ---
    app.include_router(extraction_routes.router, prefix="/api/v1")

    # --- Define basic endpoints within create_app or as separate handlers ---
    # For now, we'll keep them here for simplicity, but for more complex apps,
    # you might move them into their own route files (e.g., health_routes.py)

    @app.get("/health")
    async def health_check_endpoint():  # Renamed to avoid conflict if `create_app` is called
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    # Renamed to avoid conflict
    async def serve_frontend_root(request: Request):
        """Root route for serving the frontend."""
        # Access templates from app.state
        return request.app.state.templates.TemplateResponse("index.html", {"request": request})

    logger.info("FastAPI application created and configured.")
    return app


# --- Instantiate the app by calling create_app() ---
app = create_app()

# You can optionally add a function to get all routes for debugging,
# similar to your pattern, but it's not strictly necessary for the core
# functionality of the refactor.
# from fastapi.routing import APIRoute
# def get_all_routes(app: FastAPI):
#     paths = []
#     for route in app.routes:
#         if isinstance(route, APIRoute):
#             paths.append(route.path)
#     return paths

# all_endpoint_paths = get_all_routes(app)
# print("All endpoint paths:")
# for path in all_endpoint_paths:
#     print(f"- {path}")


if __name__ == "__main__":
    # Import uvicorn only if running directly
    import uvicorn
    logger.info("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
    logger.info("Uvicorn server stopped.")
