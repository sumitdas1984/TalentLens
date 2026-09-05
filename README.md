# TalentLens

A lightweight backend service for evaluating candidates against job requirements using **FastAPI, asynchronous Python, and MCP (Model Context Protocol)**.

The project demonstrates how to build a production-style AI/backend service where the same evaluation capabilities can be accessed through both **REST APIs** and **MCP tools**.

## 🎯 Project Overview

TalentLens simulates an AI-powered candidate evaluation system.

A client can submit a candidate and job information, trigger an evaluation, and retrieve the evaluation result through REST APIs.

An AI agent can perform similar operations through MCP tools.

```text
                    ┌──────────────────┐
                    │      Client      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     FastAPI      │
                    │   REST APIs      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Evaluation       │
                    │ Service          │
                    │                  │
                    │ Async Processing │
                    └────────┬─────────┘
                             ▲
                             │
                    ┌────────┴─────────┐
                    │   MCP Server     │
                    │                  │
                    │ MCP Tools        │
                    └──────────────────┘
```

## ✨ Key Features

* REST APIs built with **FastAPI**
* Asynchronous request processing using **asyncio**
* Concurrent execution using `asyncio.gather()`
* Custom FastAPI middleware
* Request ID and processing-time tracking
* Pydantic request/response validation
* In-memory evaluation storage
* MCP server with evaluation tools
* Shared business logic between REST APIs and MCP
* Basic automated testing with pytest

## 🛠️ Tech Stack

| Technology | Purpose                            |
| ---------- | ---------------------------------- |
| Python     | Application development            |
| FastAPI    | REST API framework                 |
| Pydantic   | Data validation                    |
| asyncio    | Asynchronous/concurrent processing |
| MCP        | AI-agent tool interface            |
| pytest     | Testing                            |
| HTTPX      | API testing                        |

## 📁 Repository Structure

```text
TalentLens/
│
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application and REST endpoints
│   ├── models.py        # Pydantic models
│   ├── service.py       # Evaluation business logic
│   ├── middleware.py    # Request middleware
│   └── mcp_server.py    # MCP server and tools
│
├── tests/
│   └── __init__.py      # Test package
│
├── requirements.txt
├── README.md
└── .gitignore
```

The application follows a simple separation of concerns:

```text
API Layer
    ↓
Service Layer
    ↓
Data / Storage
```

Both FastAPI and MCP are intended to use the same service layer rather than duplicating business logic.

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/sumitdas1984/TalentLens.git
cd TalentLens
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the FastAPI application

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## 🔌 REST API

The application exposes endpoints for managing candidate evaluations.

### Create Evaluation

```http
POST /evaluations
```

Example request:

```json
{
  "candidate_id": "C001",
  "job_id": "J100",
  "skills": [
    "python",
    "fastapi",
    "aws"
  ]
}
```

### Get Evaluation

```http
GET /evaluations/{evaluation_id}
```

### Run Evaluation

```http
POST /evaluations/{evaluation_id}/run
```

### Run Batch Evaluation

```http
POST /evaluations/{evaluation_id}/run-batch
```

> API behavior and implementation are intentionally evolving as the project is developed.

## 🤖 MCP Interface

The project also exposes candidate evaluation functionality through MCP.

Planned tools include:

### `evaluate_candidate`

Evaluates a candidate against a job and returns an evaluation result.

### `get_evaluation`

Retrieves an existing candidate evaluation.

The MCP interface allows an AI agent to interact with the evaluation service using structured tools rather than directly calling REST endpoints.

## ⚡ Async Processing

The evaluation workflow demonstrates asynchronous processing.

Independent evaluation operations such as:

```text
Skill Analysis
Resume Analysis
Experience Analysis
```

can execute concurrently using:

```python
asyncio.gather()
```

This allows independent I/O-bound operations to execute concurrently instead of sequentially.

## 🧩 Middleware

Custom middleware is used to provide request-level observability.

Each response can include:

```text
X-Request-ID
X-Process-Time
```

Example log:

```text
GET /evaluations/E001 - 200 - 0.023s
```

This provides a foundation for request tracing and performance monitoring.

## 🧪 Testing

Tests are implemented using **pytest**.

Run the test suite with:

```bash
pytest
```

## 🗺️ Future Improvements

Potential extensions include:

* Persistent database storage
* Authentication and authorization
* Redis-based caching
* Background task processing
* Evaluation queues
* Retry and timeout handling
* Structured logging
* Docker containerization
* CI/CD pipeline
* More comprehensive test coverage
* Real LLM-based candidate evaluation
* Additional MCP resources and tools

## 📌 Project Status

🚧 **Work in Progress**

This project is being developed incrementally to demonstrate practical backend engineering, asynchronous Python, FastAPI, and MCP integration patterns.
