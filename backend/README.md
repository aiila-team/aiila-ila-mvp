# Backend Setup

Run these commands after pulling the repository on Windows PowerShell.

## 1. Go to the backend folder

```powershell
cd backend
```

## 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3. Create the backend `.env` file

The app reads environment variables from a `.env` file in this folder.
Copy the example file from the repository root:

```powershell
Copy-Item ..\.env.example .env
```

## 4. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Run database migrations

```powershell
alembic upgrade head
```

## Notes

- Make sure PostgreSQL, Redis, and Neo4j are running before starting the app.
- Required secrets such as `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, and `SECRET_KEY` must be set in `.env`.
