# PDF Extraction Service

## Overview
A modular, scalable PDF extraction service built with FastAPI that supports:
- PDF splitting
- Image extraction
- Element extraction
- Web-based file upload
- Download of extracted content

## Features
- Modern, responsive UI
- Background processing
- Drag and drop file upload
- JSON and Markdown output formats
- Configurable extraction pipeline

## Setup and Installation

### Prerequisites
- Python 3.8+
- pip

### Installation Steps
1. Clone the repository
2. Create a virtual environment
3. Install dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### Running the Application
```bash
uvicorn backend.main:app --reload
```

## Project Structure
- `backend/`: Core application logic
- `frontend/`: Static files and templates
- `uploads/`: Temporary PDF uploads
- `outputs/`: Extracted PDF content

## Configuration
Modify `backend/core/config.py` to customize:
- Upload directory
- Output directory
- Other application settings

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request
```# UniDocParser
