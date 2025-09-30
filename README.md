# UniDocParser

A comprehensive document parsing backend system that extracts, processes, and converts various document formats (PDF, Excel, Images) into structured markdown with intelligent element detection and VLM-powered formatting.

## Features

- **Multi-format Support**: Parse PDFs, Excel files, and images
- **Intelligent Element Extraction**: Automatically detect and extract tables, figures, and text elements using Unstructured
- **OCR Integration**: Built-in OCR support for scanned documents via OCRmyPDF and Tesseract
- **VLM-Powered Processing**:
  - Vision Language Models for figure-to-table conversion
  - Intelligent text formatting and cleanup
  - Support for both local (Hugging Face) and remote (Ollama) models
- **Async Pipeline Architecture**: Modular, extensible pipeline with configurable steps
- **Job Management**: Complete CRUD operations with PostgreSQL backend
- **Celery Integration**: Asynchronous task processing with Redis
- **FastAPI Backend**: RESTful API with automatic documentation
- **Docker Support**: Containerized deployment with docker-compose

## Requirements

- Python 3.11-3.12
- PostgreSQL (for job storage)
- Redis (for Celery tasks)
- Tesseract OCR (for text extraction from images)
- CUDA-compatible GPU (optional, for local VLM inference)

## Installation

### System Dependencies

First, install Tesseract OCR:

**Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install -y tesseract-ocr libtesseract-dev

sudo apt install -y tesseract-ocr-ind tesseract-ocr-eng # for Indonesian and English

```

**macOS:**

```bash
brew install tesseract
```

**Windows:**
Download and install from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)

### Using Poetry (Recommended)

```bash
# Clone the repository
git clone https://github.com/deduu/UniDocParser.git
cd UniDocParser

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies with Poetry
poetry install
```

### Using Docker

```bash
# Build and run with docker-compose
docker-compose up -d
```

## Configuration

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/unidocparser

# Redis
REDIS_URL=redis://localhost:6379/0

# Model Configuration
VLM_MODEL_PATH=your-vlm-model-path
USE_OLLAMA=false
OLLAMA_BASE_URL=http://localhost:11434

# Storage
STORAGE_ROOT=./storage
OUTPUT_ROOT=./outputs
```

## Quick Start

### 1. Run Database Migrations

```bash
alembic upgrade head
```

### 2. Start the Backend Server

```bash
uvicorn backend.main:app --reload
```

API will be available at `http://localhost:8000`

- API Docs: `http://localhost:8000/docs`
- Alternative Docs: `http://localhost:8000/redoc`

### 3. Start Celery Worker

```bash
celery -A backend.celery_app worker --loglevel=info
```

### 4. Process a Document

```python
import requests

# Upload and process a document
files = {'file': open('document.pdf', 'rb')}
response = requests.post(
    'http://localhost:8000/api/extraction/extract',
    files=files
)

job_id = response.json()['job_id']

# Check job status
status = requests.get(f'http://localhost:8000/api/jobs/{job_id}')
print(status.json())
```

## Architecture

### Pipeline Steps

The document processing pipeline consists of modular steps:

1. **SplitStep**: Converts documents to images (page-by-page)
2. **OCRStep**: Applies OCR to scanned documents using Tesseract
3. **ExtractElementsStep**: Extracts structured elements using Unstructured
4. **ExtractImagesStep**: Detects and extracts figures/tables with vision models
5. **FormatExtractedTextStep**: Cleans and formats extracted text
6. **VLMExtractorStep**: Applies VLM for advanced element understanding
7. **MarkdownStep**: Generates final markdown output

### Core Components

- **Extraction Layer** (`backend/extraction/`): File type detection and element extraction
- **Pipeline Layer** (`backend/pipeline/`): Document processing orchestration
- **Generation Layer** (`backend/generation/`): LLM/VLM inference adapters
- **Database Services** (`backend/db/services/`): Job, page, and result management
- **File Ingestion** (`backend/file_ingestion/`): Format-specific handlers

## API Endpoints

### Extraction

- `POST /api/extraction/extract` - Upload and process a document
- `GET /api/extraction/job/{job_id}` - Get job status and results
- `GET /api/extraction/page/{page_id}` - Get specific page data

### Jobs

- `GET /api/jobs/` - List all jobs (with filtering)
- `GET /api/jobs/{job_id}` - Get job details
- `DELETE /api/jobs/{job_id}` - Delete a job
- `GET /api/jobs/stats` - Get job statistics

### Files

- `GET /api/files/{file_key}` - Download processed files

## Development

### Running Tests

```bash
pytest
```

### Code Structure

```
backend/
├── core/           # Configuration and settings
├── db/            # Database models and services
├── extraction/    # Element extraction logic
├── file_ingestion/# File handlers (PDF, Excel, Image)
├── generation/    # LLM/VLM adapters
├── pipeline/      # Document processing pipeline
├── routes/        # FastAPI routes
├── schemas/       # Pydantic models
└── utils/         # Helper functions
```

## Key Dependencies

- **FastAPI** (0.115.12) - Modern web framework
- **Ultralytics** (8.3.96) - Object detection for figure extraction
- **Unstructured** (0.18.13) - Document element extraction
- **OCRmyPDF** (16.10.4) - PDF OCR processing
- **Celery** (5.5.3) - Distributed task queue
- **PostgreSQL** (via asyncpg & psycopg2) - Database
- **Redis** (6.4.0) - Message broker
- **Unsloth** - Efficient LLM/VLM inference
- **Langchain** (0.3.27) - LLM orchestration

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms specified in the repository.

## Author

**deduu** - [dedy.ariansyah1@gmail.com](mailto:dedy.ariansyah1@gmail.com)

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Document processing powered by [Unstructured](https://unstructured.io/)
- OCR via [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) and [Tesseract](https://github.com/tesseract-ocr/tesseract)
- Object detection with [Ultralytics](https://github.com/ultralytics/ultralytics)
- LLM/VLM support via [Transformers](https://huggingface.co/transformers) and [Unsloth](https://github.com/unslothai/unsloth)

---

For detailed documentation and examples, visit the [API documentation](http://localhost:8000/docs) when running the server.
