# Candidate Eval API

A lightweight candidate evaluation backend built with FastAPI and MCP.

## Tech Stack

- Python
- FastAPI
- Pydantic
- AsyncIO
- MCP
- Pytest

## Project Structure

```text
app/
├── main.py
├── models.py
├── service.py
├── middleware.py
└── mcp_server.py

tests/
└──
```

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

API documentation:

http://127.0.0.1:8000/docs

## Status

🚧 Under development
