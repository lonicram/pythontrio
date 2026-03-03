# PythonTrio

A demo project showcasing the integration of Alembic, SQLAlchemy, and FastAPI.

## Tech Stack

- **FastAPI** - Modern web framework for building APIs
- **SQLAlchemy** - SQL toolkit and ORM
- **Alembic** - Database migration tool for SQLAlchemy

## Installation

### Prerequisites

- Python 3.10 or higher

### Setup

1. Clone the repository and navigate to the project directory:

```bash
cd python_trio
```

2. Create a virtual environment:

```bash
python -m venv venv
```

3. Activate the virtual environment:

**Linux/macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

4. Install requirements:

```bash
pip install -r requirements.txt
```

## Database Setup

### Start PostgreSQL with Docker

```bash
docker compose up -d
```

This starts a PostgreSQL container with:
- **Host:** localhost
- **Port:** 5432
- **Database:** pythontrio
- **User:** pythontrio
- **Password:** pythontrio

### Run Migrations

Apply Alembic migrations to set up the database schema:

```bash
alembic upgrade head
```

## Running the FastAPI Server

Start the development server with uvicorn:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### API Documentation

Once the server is running, you can access:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Welcome message |
| GET | `/health` | Health check |
| GET | `/assets` | List all assets |
| GET | `/assets/{id}` | Get asset by ID |
| POST | `/assets` | Create new asset |
| DELETE | `/assets/{id}` | Delete asset |
| GET | `/portfolios` | List all portfolios |
| GET | `/portfolios/{id}` | Get portfolio by ID |
| POST | `/portfolios` | Create new portfolio |
| DELETE | `/portfolios/{id}` | Delete portfolio |

## Project Structure

```
app/
├── main.py              # FastAPI app entry point
├── config.py            # App configuration
├── database.py          # Database engine and session
├── schemas.py           # Pydantic request/response schemas
├── models/              # SQLAlchemy ORM models
│   ├── __init__.py
│   ├── asset.py
│   └── portfolio.py
└── routers/             # API route handlers
    ├── __init__.py
    ├── assets.py
    └── portfolios.py
alembic/
├── env.py               # Alembic environment config
├── script.py.mako       # Migration template
└── versions/            # Migration files
```
