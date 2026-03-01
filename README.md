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
| GET | `/items` | List all items |
| GET | `/items/{id}` | Get item by ID |
| POST | `/items` | Create new item |
